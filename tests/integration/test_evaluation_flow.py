"""統合テスト: 評価フロー（API層→Service層→DB）"""

from unittest.mock import MagicMock, patch

from app.core.constants import MESSAGES, ModelType
from app.models.evaluation_prompt import EvaluationPrompt
from tests.integration.conftest import last_event, parse_sse_events

STREAM_URL = "/api/evaluation/evaluate-stream"

DOCUMENT_TYPE = "主治医意見書"

VALID_OUTPUT_SUMMARY = (
    "治療経過: 2型糖尿病にて加療中。血糖コントロール良好。\n"
    "特記事項: 全身状態良好。"
)


def _make_mock_create_client(evaluation_text: str = "評価結果: 適切な要約です。"):
    """create_client のモックを生成"""
    mock_instance = MagicMock()
    mock_instance.generate_content.return_value = (evaluation_text, 500, 200)
    return MagicMock(return_value=mock_instance)


def _payload(**overrides) -> dict:
    return {
        "document_type": DOCUMENT_TYPE,
        "input_text": "患者は67歳男性。糖尿病にて加療中。",
        "previous_text": "メトホルミン500mg",
        "additional_info": "",
        "output_summary": VALID_OUTPUT_SUMMARY,
        **overrides,
    }


class TestEvaluation:
    def test_success_emits_complete_event(
        self, integration_client, db_session, csrf_headers
    ):
        """正常系: 評価プロンプトあり状態で progress→complete のSSEイベントが返る"""
        db_session.add(
            EvaluationPrompt(
                document_type=DOCUMENT_TYPE,
                content="以下の主治医意見書を評価してください。",
                is_active=True,
            )
        )
        db_session.commit()

        mock_create = _make_mock_create_client()
        with patch("app.services.evaluation_service.create_client", mock_create):
            response = integration_client.post(
                STREAM_URL, json=_payload(), headers=csrf_headers
            )

        events = parse_sse_events(response.text)
        assert [e["type"] for e in events[:-1]] == ["progress", "progress"]

        complete = last_event(response)
        assert complete["type"] == "complete"
        assert complete["data"] == {
            "success": True,
            "evaluation_result": "評価結果: 適切な要約です。",
            "input_tokens": 500,
            "output_tokens": 200,
            "processing_time": complete["data"]["processing_time"],
        }

        # 評価モデルの設定（Gemini）とDBの評価プロンプトが使われる
        mock_create.assert_called_once_with(ModelType.GEMINI)
        user_message, model_name, system_prompt = (
            mock_create.return_value.generate_content.call_args[0]
        )
        assert VALID_OUTPUT_SUMMARY in user_message
        assert "メトホルミン500mg" in user_message
        assert model_name == "gemini-test-model"
        assert system_prompt.startswith("以下の主治医意見書を評価してください。")

    def test_no_evaluation_prompt_emits_error(
        self, integration_client, db_session, csrf_headers
    ):
        """評価プロンプトが未設定の場合はerrorイベントを返す"""
        response = integration_client.post(
            STREAM_URL, json=_payload(), headers=csrf_headers
        )

        error = last_event(response)
        assert error["type"] == "error"
        assert error["data"]["success"] is False
        assert DOCUMENT_TYPE in error["data"]["error_message"]

    def test_empty_output_summary_emits_validation_error(
        self, integration_client, db_session, csrf_headers
    ):
        """評価対象の出力が空の場合はバリデーションエラーを返す"""
        response = integration_client.post(
            STREAM_URL, json=_payload(output_summary=""), headers=csrf_headers
        )

        error = last_event(response)
        assert error["type"] == "error"
        assert error["data"] == {
            "success": False,
            "error_message": MESSAGES["VALIDATION"]["EVALUATION_NO_OUTPUT"],
        }

    def test_evaluation_prompt_crud_then_evaluate(
        self, integration_client, db_session, csrf_headers
    ):
        """評価プロンプトをAPI経由で登録してから評価を実行できる"""
        integration_client.post(
            "/api/evaluation/prompts",
            json={
                "document_type": "訪問看護指示書",
                "content": "以下の訪問看護指示書を詳細に評価してください。",
            },
            headers=csrf_headers,
        )

        with patch(
            "app.services.evaluation_service.create_client",
            _make_mock_create_client("詳細な評価結果です。"),
        ):
            response = integration_client.post(
                STREAM_URL,
                json=_payload(document_type="訪問看護指示書"),
                headers=csrf_headers,
            )

        complete = last_event(response)
        assert complete["type"] == "complete"
        assert complete["data"]["evaluation_result"] == "詳細な評価結果です。"
