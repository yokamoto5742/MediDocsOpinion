"""統合テスト: 評価フロー（API層→Service層→DB）"""
from unittest.mock import MagicMock, patch

from fastapi import status

from app.models.evaluation_prompt import EvaluationPrompt
from tests.integration.conftest import parse_sse_events

VALID_OUTPUT_SUMMARY = (
    "現病歴: 2型糖尿病にて加療中。\n"
    "入院経過: 血糖コントロール良好となり退院。\n"
    "退院時状況: 全身状態良好。"
)


def _make_mock_gemini_cls(evaluation_text: str = "評価結果: 適切な要約です。"):
    """GeminiAPIClientクラスのモックを生成"""
    mock_instance = MagicMock()
    mock_instance.initialize.return_value = None
    mock_instance._generate_content.return_value = (evaluation_text, 500, 200)
    mock_cls = MagicMock(return_value=mock_instance)
    return mock_cls


class TestSyncEvaluation:
    def test_success_returns_evaluation_result(
        self, integration_client, db_session, csrf_headers
    ):
        """正常系: 評価プロンプトあり状態で評価が成功する"""
        db_session.add(EvaluationPrompt(
            document_type="退院時サマリ",
            content="以下の退院時サマリを評価してください。",
            is_active=True,
        ))
        db_session.commit()

        with patch(
            "app.services.evaluation_service.GeminiAPIClient",
            _make_mock_gemini_cls(),
        ):
            response = integration_client.post(
                "/api/evaluation/evaluate",
                json={
                    "document_type": "退院時サマリ",
                    "input_text": "患者は67歳男性。糖尿病にて加療中。",
                    "current_prescription": "メトホルミン500mg",
                    "additional_info": "",
                    "output_summary": VALID_OUTPUT_SUMMARY,
                },
                headers=csrf_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["evaluation_result"] != ""
        assert data["input_tokens"] == 500
        assert data["output_tokens"] == 200
        assert data["error_message"] is None

    def test_no_evaluation_prompt_returns_error(
        self, integration_client, db_session, csrf_headers
    ):
        """評価プロンプトが未設定の場合はエラーレスポンスを返す"""
        response = integration_client.post(
            "/api/evaluation/evaluate",
            json={
                "document_type": "退院時サマリ",
                "input_text": "患者情報テキスト",
                "current_prescription": "",
                "additional_info": "",
                "output_summary": VALID_OUTPUT_SUMMARY,
            },
            headers=csrf_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert "退院時サマリ" in data["error_message"]

    def test_empty_output_summary_returns_validation_error(
        self, integration_client, db_session, csrf_headers
    ):
        """評価対象の出力が空の場合はバリデーションエラーを返す"""
        response = integration_client.post(
            "/api/evaluation/evaluate",
            json={
                "document_type": "退院時サマリ",
                "input_text": "患者情報",
                "current_prescription": "",
                "additional_info": "",
                "output_summary": "",
            },
            headers=csrf_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert data["error_message"] is not None

    def test_evaluation_prompt_crud_then_evaluate(
        self, integration_client, db_session, csrf_headers
    ):
        """評価プロンプトをAPI経由で登録してから評価を実行できる"""
        integration_client.post(
            "/api/evaluation/prompts",
            json={
                "document_type": "現病歴",
                "content": "以下の現病歴を詳細に評価してください。",
            },
            headers=csrf_headers,
        )

        with patch(
            "app.services.evaluation_service.GeminiAPIClient",
            _make_mock_gemini_cls("詳細な評価結果です。"),
        ):
            response = integration_client.post(
                "/api/evaluation/evaluate",
                json={
                    "document_type": "現病歴",
                    "input_text": "患者情報テキスト",
                    "current_prescription": "",
                    "additional_info": "",
                    "output_summary": VALID_OUTPUT_SUMMARY,
                },
                headers=csrf_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True


class TestStreamingEvaluation:
    def test_success_emits_complete_event(
        self, integration_client, db_session, csrf_headers
    ):
        """ストリーミング評価でcompleteイベントが返る"""
        db_session.add(EvaluationPrompt(
            document_type="退院時サマリ",
            content="以下の退院時サマリを評価してください。",
            is_active=True,
        ))
        db_session.commit()

        with patch(
            "app.services.evaluation_service.GeminiAPIClient",
            _make_mock_gemini_cls("評価完了: 高品質なサマリです。"),
        ):
            response = integration_client.post(
                "/api/evaluation/evaluate-stream",
                json={
                    "document_type": "退院時サマリ",
                    "input_text": "患者情報テキスト",
                    "current_prescription": "",
                    "additional_info": "",
                    "output_summary": VALID_OUTPUT_SUMMARY,
                },
                headers=csrf_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers["content-type"]

        events = parse_sse_events(response.text)
        complete_events = [e for e in events if e["type"] == "complete"]
        assert len(complete_events) > 0
        assert complete_events[0]["data"]["success"] is True
        assert complete_events[0]["data"]["evaluation_result"] != ""

    def test_no_prompt_emits_error_event(
        self, integration_client, db_session, csrf_headers
    ):
        """評価プロンプト未設定時のストリーミングはerrorイベントが返る"""
        response = integration_client.post(
            "/api/evaluation/evaluate-stream",
            json={
                "document_type": "退院時サマリ",
                "input_text": "患者情報",
                "current_prescription": "",
                "additional_info": "",
                "output_summary": VALID_OUTPUT_SUMMARY,
            },
            headers=csrf_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        events = parse_sse_events(response.text)
        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) > 0
        assert error_events[0]["data"]["success"] is False
