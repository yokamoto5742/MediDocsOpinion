from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.models.usage import SummaryUsage
from app.services import statistics_service

JST = ZoneInfo("Asia/Tokyo")


def test_get_usage_summary_empty(test_db):
    """使用統計サマリー取得 - データなし"""
    summary = statistics_service.get_usage_summary(test_db)
    assert summary["total_count"] == 0
    assert summary["total_input_tokens"] == 0
    assert summary["total_output_tokens"] == 0
    assert summary["average_processing_time"] == 0


def test_get_usage_summary_with_data(test_db, sample_usage_records):
    """使用統計サマリー取得 - データあり"""
    summary = statistics_service.get_usage_summary(test_db)
    assert summary["total_count"] == 2
    assert summary["total_input_tokens"] == 3000
    assert summary["total_output_tokens"] == 1300
    assert 2.0 < summary["average_processing_time"] < 3.5


def test_get_usage_summary_filtered_by_model(test_db, sample_usage_records):
    """使用統計サマリー取得 - モデルフィルター"""
    summary = statistics_service.get_usage_summary(test_db, model="Claude")
    assert summary["total_count"] == 1
    assert summary["total_input_tokens"] == 1000
    assert summary["total_output_tokens"] == 500


def test_get_usage_summary_filtered_by_date_range(test_db, sample_usage_records):
    """使用統計サマリー取得 - 日付範囲フィルター"""
    now = datetime.now()
    start_date = now - timedelta(days=1)
    end_date = now + timedelta(days=1)

    summary = statistics_service.get_usage_summary(
        test_db,
        start_date=start_date,
        end_date=end_date,
    )
    assert summary["total_count"] == 2


def test_get_usage_summary_no_data_in_range(test_db, sample_usage_records):
    """使用統計サマリー取得 - 範囲外の日付"""
    start_date = datetime.now() + timedelta(days=10)
    end_date = datetime.now() + timedelta(days=20)

    summary = statistics_service.get_usage_summary(
        test_db,
        start_date=start_date,
        end_date=end_date,
    )
    assert summary["total_count"] == 0


def test_get_usage_records_empty(test_db):
    """使用統計レコード取得 - データなし"""
    records = statistics_service.get_usage_records(test_db)
    assert records == []


def test_get_usage_records_with_data(test_db, sample_usage_records):
    """使用統計レコード取得 - データあり"""
    records = statistics_service.get_usage_records(test_db)
    assert len(records) == 2
    assert records[0].department in ["眼科", "default"]


def test_get_usage_records_with_limit(test_db, sample_usage_records):
    """使用統計レコード取得 - limit指定"""
    records = statistics_service.get_usage_records(test_db, limit=1)
    assert len(records) == 1


def test_get_usage_records_with_offset(test_db, sample_usage_records):
    """使用統計レコード取得 - offset指定"""
    all_records: list[SummaryUsage] = statistics_service.get_usage_records(test_db)
    offset_records: list[SummaryUsage] = statistics_service.get_usage_records(test_db, offset=1)

    assert len(offset_records) == 1
    assert len(all_records) != 0
    assert len(offset_records) != 0
    assert offset_records[0].id != all_records[0].id


def test_get_usage_records_ordering(test_db, sample_usage_records):
    """使用統計レコード取得 - 降順ソート"""
    records: list[SummaryUsage] = statistics_service.get_usage_records(test_db)
    assert len(records) > 1
    assert records[0].date >= records[1].date


class TestApplyDefaultPeriod:
    """_apply_default_period 関数のテスト"""

    def test_no_args_applies_default_period(self):
        """引数なし: end_date=now, start_date=now-DEFAULT_STATISTICS_PERIOD_DAYS"""
        from app.core.constants import DEFAULT_STATISTICS_PERIOD_DAYS
        from app.services.statistics_service import _apply_default_period

        start, end = _apply_default_period(None, None)

        now = datetime.now(JST)
        assert abs((end - now).total_seconds()) < 5
        expected_start = now - timedelta(days=DEFAULT_STATISTICS_PERIOD_DAYS)
        assert abs((start - expected_start).total_seconds()) < 5

    def test_with_start_date_only(self):
        """start_date のみ指定: end_date が now に設定される"""
        from app.services.statistics_service import _apply_default_period

        fixed_start = datetime.now(JST) - timedelta(days=3)
        start, end = _apply_default_period(fixed_start, None)

        assert start == fixed_start
        now = datetime.now(JST)
        assert abs((end - now).total_seconds()) < 5

    def test_with_both_dates(self):
        """両方指定: そのまま返る"""
        from app.services.statistics_service import _apply_default_period

        fixed_start = datetime(2024, 1, 1)
        fixed_end = datetime(2024, 1, 31)
        start, end = _apply_default_period(fixed_start, fixed_end)

        assert start == fixed_start
        assert end == fixed_end


class TestGetAggregatedRecords:
    """get_aggregated_records 関数のテスト"""

    def test_empty(self, test_db):
        """データなし: 空リスト"""
        results = statistics_service.get_aggregated_records(test_db)
        assert results == []

    def test_with_data(self, test_db, sample_usage_records):
        """データあり: 文書タイプ・診療科・医師でグループ化される"""
        results = statistics_service.get_aggregated_records(test_db)
        assert len(results) == 2
        keys = {(r["document_type"], r["count"]) for r in results}
        assert ("他院への紹介", 1) in keys
        assert ("返書", 1) in keys

    def test_result_fields(self, test_db, sample_usage_records):
        """結果に必要なフィールドが全て含まれる"""
        results = statistics_service.get_aggregated_records(test_db)
        required_keys = {"document_type", "department", "doctor", "count", "input_tokens", "output_tokens"}
        for r in results:
            assert required_keys.issubset(r.keys())

    def test_default_department_label(self, test_db, sample_usage_records):
        """department='default' が定数ラベルに変換される"""
        from app.core.constants import MESSAGES

        results = statistics_service.get_aggregated_records(test_db)
        default_record = next(r for r in results if r["document_type"] == "返書")
        assert default_record["department"] == MESSAGES["INFO"]["DEFAULT_DEPARTMENT_LABEL"]
        assert default_record["doctor"] == MESSAGES["INFO"]["DEFAULT_DOCTOR_LABEL"]

    def test_filtered_by_model(self, test_db, sample_usage_records):
        """model フィルター: Claude のみ返る"""
        results = statistics_service.get_aggregated_records(test_db, model="Claude")
        assert len(results) == 1
        assert results[0]["document_type"] == "他院への紹介"

    def test_filtered_by_document_type(self, test_db, sample_usage_records):
        """document_type フィルター: 指定した文書タイプのみ返る"""
        results = statistics_service.get_aggregated_records(test_db, document_type="返書")
        assert len(results) == 1
        assert results[0]["document_type"] == "返書"

    def test_filtered_by_date_range(self, test_db, sample_usage_records):
        """日付範囲フィルター: 範囲内のみ返る"""
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now() + timedelta(days=1)
        results = statistics_service.get_aggregated_records(
            test_db, start_date=start_date, end_date=end_date
        )
        assert len(results) == 2

    def test_out_of_range_returns_empty(self, test_db, sample_usage_records):
        """範囲外の日付: 空リスト"""
        start_date = datetime.now() + timedelta(days=10)
        end_date = datetime.now() + timedelta(days=20)
        results = statistics_service.get_aggregated_records(
            test_db, start_date=start_date, end_date=end_date
        )
        assert results == []

    def test_tokens_are_aggregated(self, test_db, sample_usage_records):
        """トークン数が集計される"""
        results = statistics_service.get_aggregated_records(test_db, model="Claude")
        assert results[0]["input_tokens"] == 1000
        assert results[0]["output_tokens"] == 500
