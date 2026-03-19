"""統合テスト: エラーハンドリング（AI API障害・ストリーミングエラー）"""
from unittest.mock import MagicMock, patch

from fastapi import status

from app.models.evaluation_prompt import EvaluationPrompt
from tests.integration.conftest import parse_sse_events

_VALID_MEDICAL_TEXT = (
    "患者は70歳女性。慢性心不全、2型糖尿病にて長期加療中。"
    "今回は心不全増悪にて入院し、治療後症状改善し退院となった。"
)

_VALID_OUTPUT_SUMMARY = (
    "現病歴: 慢性心不全、糖尿病にて加療中。\n"
    "入院経過: 心不全増悪後、治療により改善。\n"
    "退院時状況: 症状改善し退院。"
)


class TestSyncAPIErrors:
    def test_ai_api_exception_returns_error_response(
        self, integration_client, db_session, csrf_headers
    ):
        """同期生成でAI APIが例外を投げるとsuccess=Falseレスポンスが返る"""
        with patch(
            "app.services.summary_service.generate_summary_with_provider",
            side_effect=Exception("Bedrock接続エラー"),
        ):
            response = integration_client.post(
                "/api/summary/generate",
                json={
                    "medical_text": _VALID_MEDICAL_TEXT,
                    "model": "Claude",
                    "model_explicitly_selected": True,
                },
                headers=csrf_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert "Bedrock接続エラー" in data["error_message"]

    def test_evaluation_api_exception_returns_error_response(
        self, integration_client, db_session, csrf_headers
    ):
        """評価でAI APIが例外を投げるとsuccess=Falseレスポンスが返る"""
        db_session.add(EvaluationPrompt(
            document_type="退院時サマリ",
            content="評価プロンプト",
            is_active=True,
        ))
        db_session.commit()

        mock_instance = MagicMock()
        mock_instance.initialize.return_value = None
        mock_instance._generate_content.side_effect = Exception("Gemini API障害")
        mock_cls = MagicMock(return_value=mock_instance)

        with patch("app.services.evaluation_service.GeminiAPIClient", mock_cls):
            response = integration_client.post(
                "/api/evaluation/evaluate",
                json={
                    "document_type": "退院時サマリ",
                    "input_text": "患者情報テキスト",
                    "current_prescription": "",
                    "additional_info": "",
                    "output_summary": _VALID_OUTPUT_SUMMARY,
                },
                headers=csrf_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert data["error_message"] is not None

    def test_invalid_model_name_returns_error_response(
        self, integration_client, db_session, csrf_headers
    ):
        """サポートされていないモデル名はエラーレスポンスが返る"""
        response = integration_client.post(
            "/api/summary/generate",
            json={
                "medical_text": _VALID_MEDICAL_TEXT,
                "model": "UnsupportedModel",
                "model_explicitly_selected": True,
            },
            headers=csrf_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert data["error_message"] is not None


class TestStreamingErrors:
    def test_ai_exception_during_stream_emits_error_event(
        self, integration_client, db_session, csrf_headers
    ):
        """ストリーミング生成でAI APIが例外を投げるとerror SSEイベントが返る"""
        with patch(
            "app.services.summary_service.generate_summary_stream_with_provider",
            side_effect=Exception("ストリーミングエラー"),
        ):
            response = integration_client.post(
                "/api/summary/generate-stream",
                json={
                    "medical_text": _VALID_MEDICAL_TEXT,
                    "model": "Claude",
                    "model_explicitly_selected": True,
                },
                headers=csrf_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        events = parse_sse_events(response.text)
        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) > 0
        assert error_events[0]["data"]["success"] is False

    def test_evaluation_exception_during_stream_emits_error_event(
        self, integration_client, db_session, csrf_headers
    ):
        """ストリーミング評価でAI APIが例外を投げるとerror SSEイベントが返る"""
        db_session.add(EvaluationPrompt(
            document_type="退院時サマリ",
            content="評価プロンプト",
            is_active=True,
        ))
        db_session.commit()

        mock_instance = MagicMock()
        mock_instance.initialize.return_value = None
        mock_instance._generate_content.side_effect = Exception("評価APIエラー")
        mock_cls = MagicMock(return_value=mock_instance)

        with patch("app.services.evaluation_service.GeminiAPIClient", mock_cls):
            response = integration_client.post(
                "/api/evaluation/evaluate-stream",
                json={
                    "document_type": "退院時サマリ",
                    "input_text": "患者情報テキスト",
                    "current_prescription": "",
                    "additional_info": "",
                    "output_summary": _VALID_OUTPUT_SUMMARY,
                },
                headers=csrf_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        events = parse_sse_events(response.text)
        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) > 0
        assert error_events[0]["data"]["success"] is False

    def test_stream_with_empty_ai_response(
        self, integration_client, db_session, csrf_headers
    ):
        """AI APIが空のレスポンスを返した場合でも正常にcompleteイベントが返る"""
        def empty_stream():
            yield {"input_tokens": 0, "output_tokens": 0}

        with patch(
            "app.services.summary_service.generate_summary_stream_with_provider",
            return_value=empty_stream(),
        ):
            response = integration_client.post(
                "/api/summary/generate-stream",
                json={
                    "medical_text": _VALID_MEDICAL_TEXT,
                    "model": "Claude",
                    "model_explicitly_selected": True,
                },
                headers=csrf_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        events = parse_sse_events(response.text)
        complete_events = [e for e in events if e["type"] == "complete"]
        assert len(complete_events) > 0
        assert complete_events[0]["data"]["success"] is True
