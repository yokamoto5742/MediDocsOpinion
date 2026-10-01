import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from google.genai import interactions

from app.core.constants import MESSAGES
from app.external.gemini_api import GeminiAPIClient
from app.schemas.summary import SummaryRequest
from app.utils.exceptions import APIError


def create_mock_settings(**kwargs):
    """テスト用の設定モックを作成"""
    mock = MagicMock()
    mock.google_project_id = kwargs.get("google_project_id", "test-project")
    mock.google_location = kwargs.get("google_location", "global")
    mock.google_credentials_json = kwargs.get("google_credentials_json", None)
    mock.gemini_thinking_level = kwargs.get("gemini_thinking_level", "HIGH")
    return mock


def create_interaction(text=None, input_tokens=None, output_tokens=None):
    """テスト用の Interaction を作成"""
    data: dict[str, Any] = {
        "id": "interaction-1",
        "status": "completed",
        "created": "2026-01-01T00:00:00Z",
        "updated": "2026-01-01T00:00:00Z",
        "model": "test-model",
    }
    if text is not None:
        data["steps"] = [{"type": "model_output", "content": [{"type": "text", "text": text}]}]
    if input_tokens is not None or output_tokens is not None:
        data["usage"] = {"total_input_tokens": input_tokens, "total_output_tokens": output_tokens}
    return interactions.Interaction.model_validate(data)


@pytest.fixture
def genai_client():
    """genai.Client をモックに差し替える（設定は既定のモック）"""
    with (
        patch("app.external.gemini_api.get_settings") as mock_get_settings,
        patch("app.external.gemini_api.genai.Client") as mock_client,
    ):
        mock_get_settings.return_value = create_mock_settings()
        mock_client.get_settings = mock_get_settings
        yield mock_client


class TestGeminiAPIClientInit:
    """GeminiAPIClient 初期化のテスト"""

    @patch("app.external.gemini_api.service_account.Credentials.from_service_account_info")
    def test_init_with_credentials_json(self, mock_from_service_account_info, genai_client):
        """初期化 - GOOGLE_CREDENTIALS_JSON の認証情報を使用する"""
        credentials_dict = {
            "type": "service_account",
            "project_id": "test-project-123",
            "client_email": "test@test-project.iam.gserviceaccount.com",
        }
        genai_client.get_settings.return_value = create_mock_settings(
            google_project_id="test-project-123",
            google_location="us-central1",
            google_credentials_json=json.dumps(credentials_dict),
        )

        client = GeminiAPIClient()

        assert client.client is genai_client.return_value
        mock_from_service_account_info.assert_called_once_with(
            credentials_dict,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        genai_client.assert_called_once_with(
            vertexai=True,
            project="test-project-123",
            location="us-central1",
            credentials=mock_from_service_account_info.return_value,
        )

    @pytest.mark.parametrize("credentials_json", [None, ""])
    def test_init_without_credentials_json(self, genai_client, credentials_json):
        """初期化 - 認証情報JSONなしの場合は既定の認証情報に任せる"""
        genai_client.get_settings.return_value = create_mock_settings(
            google_project_id="test-project-456",
            google_credentials_json=credentials_json,
        )

        GeminiAPIClient()

        genai_client.assert_called_once_with(
            vertexai=True,
            project="test-project-456",
            location="global",
            credentials=None,
        )

    @pytest.mark.parametrize("project_id", [None, ""])
    def test_init_missing_project_id(self, genai_client, project_id):
        """初期化 - GOOGLE_PROJECT_ID 未設定は APIError"""
        genai_client.get_settings.return_value = create_mock_settings(
            google_project_id=project_id
        )

        with pytest.raises(APIError) as exc_info:
            GeminiAPIClient()

        assert str(exc_info.value) == MESSAGES["CONFIG"]["VERTEX_AI_PROJECT_MISSING"]
        genai_client.assert_not_called()

    def test_init_invalid_credentials_json(self, genai_client):
        """初期化 - 認証情報JSONが壊れている場合はパースエラーが伝播する"""
        genai_client.get_settings.return_value = create_mock_settings(
            google_credentials_json="{invalid json"
        )

        with pytest.raises(json.JSONDecodeError):
            GeminiAPIClient()

    def test_init_client_error_propagates(self, genai_client):
        """初期化 - クライアント生成時の例外はそのまま伝播する"""
        genai_client.side_effect = ConnectionError("Network unreachable")

        with pytest.raises(ConnectionError):
            GeminiAPIClient()


class TestGeminiAPIClientGenerateContent:
    """GeminiAPIClient generate_content メソッドのテスト"""

    def test_generate_content_success(self, genai_client):
        """generate_content - 正常系"""
        create = genai_client.return_value.interactions.create
        create.return_value = create_interaction("生成されたサマリー", 2000, 1000)

        result = GeminiAPIClient().generate_content(
            prompt="テストプロンプト", model_name="gemini-3.8-flash"
        )

        assert result == ("生成されたサマリー", 2000, 1000)
        call_kwargs = create.call_args.kwargs
        assert call_kwargs["model"] == "gemini-3.8-flash"
        assert call_kwargs["input"] == "テストプロンプト"
        # 患者情報を含むためサーバー側に保存しない
        assert call_kwargs["store"] is False
        assert "stream" not in call_kwargs
        assert "system_instruction" not in call_kwargs

    @pytest.mark.parametrize(
        ("setting", "expected"),
        [("LOW", "low"), ("HIGH", "high")],
    )
    def test_generate_content_thinking_level(self, genai_client, setting, expected):
        """generate_content - thinking_level が小文字で渡されること"""
        genai_client.get_settings.return_value = create_mock_settings(
            gemini_thinking_level=setting
        )
        create = genai_client.return_value.interactions.create
        create.return_value = create_interaction("テキスト")

        GeminiAPIClient().generate_content(prompt="プロンプト", model_name="test-model")

        assert create.call_args.kwargs["generation_config"] == {"thinking_level": expected}

    def test_generate_content_with_system_prompt(self, genai_client):
        """generate_content - システムプロンプトが system_instruction で渡されること"""
        create = genai_client.return_value.interactions.create
        create.return_value = create_interaction("テキスト")

        GeminiAPIClient().generate_content(
            prompt="プロンプト", model_name="test-model", system_prompt="システム指示"
        )

        assert create.call_args.kwargs["system_instruction"] == "システム指示"

    def test_generate_content_no_usage(self, genai_client):
        """generate_content - usage なしの場合はトークン数 0"""
        genai_client.return_value.interactions.create.return_value = create_interaction(
            "サマリー"
        )

        result = GeminiAPIClient().generate_content(prompt="プロンプト", model_name="test-model")

        assert result == ("サマリー", 0, 0)

    def test_generate_content_no_text_output(self, genai_client):
        """generate_content - テキスト出力なしの場合は空文字"""
        genai_client.return_value.interactions.create.return_value = create_interaction(
            None, 100, 0
        )

        result = GeminiAPIClient().generate_content(prompt="プロンプト", model_name="test-model")

        assert result == ("", 100, 0)

    def test_generate_content_unexpected_response(self, genai_client):
        """generate_content - Interaction 以外の応答は APIError"""
        genai_client.return_value.interactions.create.return_value = iter([])

        with pytest.raises(APIError) as exc_info:
            GeminiAPIClient().generate_content(prompt="プロンプト", model_name="test-model")

        assert str(exc_info.value) == MESSAGES["ERROR"]["GEMINI_UNEXPECTED_RESPONSE"]

    def test_generate_content_api_error_propagates(self, genai_client):
        """generate_content - API呼び出しの例外はラップせずに伝播する"""
        genai_client.return_value.interactions.create.side_effect = TimeoutError("timed out")

        with pytest.raises(TimeoutError):
            GeminiAPIClient().generate_content(prompt="プロンプト", model_name="test-model")


class TestGeminiAPIClientGenerateSummary:
    """generate_summary を通した一連の流れのテスト"""

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_generate_summary_flow(self, mock_db_session, mock_get_prompt, genai_client):
        """generate_summary - プロンプトを組み立てて API を呼び出す"""
        mock_db_session.return_value.__enter__.return_value = MagicMock()
        mock_get_prompt.return_value = None
        create = genai_client.return_value.interactions.create
        create.return_value = create_interaction("生成された文書", 3000, 1500)

        result = GeminiAPIClient().generate_summary(
            SummaryRequest(medical_text="患者情報", previous_text="前回の内容"),
            "gemini-test-model",
        )

        assert result == ("生成された文書", 3000, 1500)
        call_kwargs = create.call_args.kwargs
        assert call_kwargs["model"] == "gemini-test-model"
        assert "患者情報" in call_kwargs["input"]
        assert "前回の内容" in call_kwargs["input"]
