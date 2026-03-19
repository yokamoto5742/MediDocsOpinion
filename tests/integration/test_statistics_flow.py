"""統合テスト: 統計・使用量フロー"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch

from fastapi import status

from app.models.usage import SummaryUsage

JST = ZoneInfo("Asia/Tokyo")

_VALID_MEDICAL_TEXT = (
    "患者は67歳男性。2型糖尿病、高血圧症の既往あり。"
    "今回は血糖コントロール不良にて入院加療後、状態改善し退院となった。"
)


def _add_usage(db_session, model: str, department: str, days_ago: int = 0, count: int = 1):
    """テスト用使用量レコードを挿入"""
    date = datetime.now(JST) - timedelta(days=days_ago)
    for _ in range(count):
        db_session.add(SummaryUsage(
            date=date,
            department=department,
            doctor="default",
            document_type="退院時サマリ",
            model=model,
            input_tokens=100,
            output_tokens=50,
            processing_time=1.0,
            app_type="dischargesummary",
        ))
    db_session.commit()


class TestStatisticsAfterGeneration:
    def test_summary_stats_reflect_generation(
        self, integration_client, db_session, csrf_headers
    ):
        """文書生成後に統計サマリが正しく更新される"""
        with patch(
            "app.services.summary_service.generate_summary_with_provider",
            return_value=("生成テキスト", 1200, 600),
        ):
            integration_client.post(
                "/api/summary/generate",
                json={
                    "medical_text": _VALID_MEDICAL_TEXT,
                    "model": "Claude",
                    "model_explicitly_selected": True,
                },
                headers=csrf_headers,
            )

        res = integration_client.get("/api/statistics/summary")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["total_count"] == 1
        assert data["total_input_tokens"] == 1200
        assert data["total_output_tokens"] == 600

    def test_multiple_generations_accumulate_in_stats(
        self, integration_client, db_session, csrf_headers
    ):
        """複数回の生成結果が統計に累積される"""
        for _ in range(3):
            with patch(
                "app.services.summary_service.generate_summary_with_provider",
                return_value=("テキスト", 500, 200),
            ):
                integration_client.post(
                    "/api/summary/generate",
                    json={
                        "medical_text": _VALID_MEDICAL_TEXT,
                        "model": "Claude",
                        "model_explicitly_selected": True,
                    },
                    headers=csrf_headers,
                )

        res = integration_client.get("/api/statistics/summary")
        data = res.json()
        assert data["total_count"] == 3
        assert data["total_input_tokens"] == 1500
        assert data["total_output_tokens"] == 600


class TestStatisticsFiltering:
    def test_model_filter(self, integration_client, db_session, csrf_headers):
        """モデルフィルターが正しく機能する"""
        _add_usage(db_session, "Claude", "内科", count=3)
        _add_usage(db_session, "Gemini_Pro", "外科", count=2)

        res = integration_client.get("/api/statistics/summary", params={"model": "Claude"})
        assert res.json()["total_count"] == 3

        res = integration_client.get("/api/statistics/summary", params={"model": "Gemini_Pro"})
        assert res.json()["total_count"] == 2

    def test_date_filter_excludes_old_records(
        self, integration_client, db_session, csrf_headers
    ):
        """日付フィルターで古いレコードが除外される"""
        _add_usage(db_session, "Claude", "内科", days_ago=30, count=2)
        _add_usage(db_session, "Claude", "内科")

        today = datetime.now(JST)
        start = (today - timedelta(days=1)).isoformat()
        end = today.isoformat()

        res = integration_client.get(
            "/api/statistics/summary",
            params={"start_date": start, "end_date": end},
        )
        assert res.json()["total_count"] == 1

    def test_aggregated_records_grouping(
        self, integration_client, db_session, csrf_headers
    ):
        """集計レコードが診療科・医師・文書タイプでグループ化される"""
        _add_usage(db_session, "Claude", "内科", count=2)
        _add_usage(db_session, "Claude", "外科", count=3)

        res = integration_client.get("/api/statistics/aggregated")
        assert res.status_code == status.HTTP_200_OK
        records = res.json()
        assert len(records) == 2
        # 件数が多い順にソートされている
        assert records[0]["count"] >= records[1]["count"]
        assert records[0]["count"] == 3

    def test_aggregated_records_model_filter(
        self, integration_client, db_session, csrf_headers
    ):
        """集計レコードのモデルフィルターが機能する"""
        _add_usage(db_session, "Claude", "内科", count=2)
        _add_usage(db_session, "Gemini_Pro", "内科")

        res = integration_client.get(
            "/api/statistics/aggregated", params={"model": "Claude"}
        )
        records = res.json()
        assert len(records) == 1
        assert records[0]["count"] == 2

    def test_pagination_limit_and_offset(
        self, integration_client, db_session, csrf_headers
    ):
        """ページネーションのlimit/offsetが正しく機能する"""
        _add_usage(db_session, "Claude", "内科", count=5)

        page1 = integration_client.get(
            "/api/statistics/records", params={"limit": 3, "offset": 0}
        )
        page2 = integration_client.get(
            "/api/statistics/records", params={"limit": 3, "offset": 3}
        )

        assert len(page1.json()) == 3
        assert len(page2.json()) == 2

    def test_empty_result_when_no_records(
        self, integration_client, db_session, csrf_headers
    ):
        """レコードが存在しない場合は空の統計が返る"""
        res = integration_client.get("/api/statistics/summary")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["total_count"] == 0
        assert data["total_input_tokens"] == 0
        assert data["total_output_tokens"] == 0
