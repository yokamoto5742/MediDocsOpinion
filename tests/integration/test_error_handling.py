"""統合テスト: エラーハンドリング（AI API障害・設定不備）"""

import json
import logging
from unittest.mock import MagicMock, patch

from app.core.constants import MESSAGES
from app.models.evaluation_prompt import EvaluationPrompt
from app.models.usage import SummaryUsage
from tests.integration.conftest import last_event

_VALID_MEDICAL_TEXT = (
    "患者は70歳女性。慢性心不全、2型糖尿病にて長期加療中。"
    "今回は心不全増悪にて入院し、治療後症状改善し退院となった。"
)

_VALID_OUTPUT_SUMMARY = (
    "治療経過: 慢性心不全、糖尿病にて加療中。心不全増悪後、治療により改善。\n"
    "特記事項: 症状改善し退院。"
)

_DOCUMENT_TYPE = "主治医意見書"


def _audit_records(caplog) -> list[dict]:
    """監査ログに記録されたイベントを取り出す"""
    return [json.loads(r.getMessage()) for r in caplog.records if r.name == "audit"]


class TestSummaryErrors:
    def test_ai_exception_emits_error_event_and_audit_log(
        self, integration_client, db_session, csrf_headers, caplog
    ):
        """文書生成でAI APIが例外を投げるとerrorイベントが返り、失敗が監査ログに残る"""
        mock_create = MagicMock()
        mock_create.return_value.generate_summary.side_effect = Exception("Bedrock接続エラー")

        with (
            caplog.at_level(logging.INFO, logger="audit"),
            patch("app.services.summary_service.create_client", mock_create),
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

        error = last_event(response)
        assert error["type"] == "error"
        # 例外詳細はクライアントに返さない
        assert error["data"] == {
            "success": False,
            "error_message": MESSAGES["ERROR"]["API_ERROR"],
        }

        failure = _audit_records(caplog)[-1]
        assert failure["event_type"] == MESSAGES["AUDIT"]["DOCUMENT_GENERATION_FAILURE"]
        assert failure["success"] is False
        assert failure["error_message"] == "Exception"

        # 失敗した生成は使用量に計上しない
        db_session.expire_all()
        assert db_session.query(SummaryUsage).count() == 0

    def test_invalid_model_name_emits_error_event(
        self, integration_client, db_session, csrf_headers
    ):
        """サポートされていないモデル名はerrorイベントが返る"""
        response = integration_client.post(
            "/api/summary/generate-stream",
            json={
                "medical_text": _VALID_MEDICAL_TEXT,
                "model": "UnsupportedModel",
                "model_explicitly_selected": True,
            },
            headers=csrf_headers,
        )

        error = last_event(response)
        assert error["type"] == "error"
        assert "UnsupportedModel" in error["data"]["error_message"]

    def test_empty_ai_response_emits_complete_event(
        self, integration_client, db_session, csrf_headers
    ):
        """AI APIが空文字を返した場合でもcompleteイベントが返る"""
        mock_create = MagicMock()
        mock_create.return_value.generate_summary.return_value = ("", 0, 0)

        with patch("app.services.summary_service.create_client", mock_create):
            response = integration_client.post(
                "/api/summary/generate-stream",
                json={
                    "medical_text": _VALID_MEDICAL_TEXT,
                    "model": "Claude",
                    "model_explicitly_selected": True,
                },
                headers=csrf_headers,
            )

        complete = last_event(response)
        assert complete["type"] == "complete"
        assert complete["data"]["success"] is True
        assert complete["data"]["output_summary"] == ""


class TestEvaluationErrors:
    def test_ai_exception_emits_error_event_and_audit_log(
        self, integration_client, db_session, csrf_headers, caplog
    ):
        """評価でAI APIが例外を投げるとerrorイベントが返り、失敗が監査ログに残る"""
        db_session.add(
            EvaluationPrompt(
                document_type=_DOCUMENT_TYPE,
                content="評価プロンプト",
                is_active=True,
            )
        )
        db_session.commit()

        mock_create = MagicMock()
        mock_create.return_value.generate_content.side_effect = Exception("Gemini API障害")

        with (
            caplog.at_level(logging.INFO, logger="audit"),
            patch("app.services.evaluation_service.create_client", mock_create),
        ):
            response = integration_client.post(
                "/api/evaluation/evaluate-stream",
                json={
                    "document_type": _DOCUMENT_TYPE,
                    "input_text": "患者情報テキスト",
                    "previous_text": "",
                    "additional_info": "",
                    "output_summary": _VALID_OUTPUT_SUMMARY,
                },
                headers=csrf_headers,
            )

        error = last_event(response)
        assert error["type"] == "error"
        assert error["data"] == {
            "success": False,
            "error_message": MESSAGES["ERROR"]["EVALUATION_ERROR"],
        }

        failure = _audit_records(caplog)[-1]
        assert failure["event_type"] == MESSAGES["AUDIT"]["EVALUATION_FAILURE"]
        assert failure["success"] is False
        assert failure["error_message"] == "Exception"
