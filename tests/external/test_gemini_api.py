import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from google.genai import interactions

from app.core.constants import MESSAGES
from app.external.gemini_api import GeminiAPIClient
from app.utils.exceptions import APIError


def create_mock_settings(**kwargs):
    """テスト用の設定モックを作成"""
    mock = MagicMock()
    mock.gemini_model = kwargs.get("gemini_model", "gemini-1.5-pro-002")
    mock.google_project_id = kwargs.get("google_project_id", "test-project")
    mock.google_location = kwargs.get("google_location", "global")
    mock.google_credentials_json = kwargs.get("google_credentials_json", None)
    mock.gemini_thinking_level = kwargs.get("gemini_thinking_level", "HIGH")
    mock.gemini_evaluation_model = kwargs.get("gemini_evaluation_model", "gemini-eval")
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


def create_text_delta_event(text):
    """テスト用のテキスト差分イベントを作成"""
    return interactions.StepDelta.model_validate(
        {"delta": {"type": "text", "text": text}, "index": 0, "event_type": "step.delta"}
    )


def create_completed_event(input_tokens, output_tokens):
    """テスト用の完了イベントを作成"""
    return interactions.InteractionCompletedEvent.model_validate({
        "interaction": {
            "id": "interaction-1",
            "status": "completed",
            "usage": {"total_input_tokens": input_tokens, "total_output_tokens": output_tokens},
        },
        "event_type": "interaction.completed",
    })


class TestGeminiAPIClientInitialization:
    """GeminiAPIClient 初期化のテスト"""

    @patch("app.external.gemini_api.get_settings")
    def test_init_with_default_model(self, mock_get_settings):
        """初期化 - デフォルトモデル使用"""
        mock_get_settings.return_value = create_mock_settings(
            gemini_model="gemini-1.5-pro-002"
        )

        client = GeminiAPIClient()

        assert client.default_model == "gemini-1.5-pro-002"
        assert client.client is None

    @patch("app.external.gemini_api.get_settings")
    def test_init_with_custom_model(self, mock_get_settings):
        """初期化 - カスタムモデル指定"""
        mock_get_settings.return_value = create_mock_settings()

        client = GeminiAPIClient(model_name="gemini-custom-model")

        assert client.default_model == "gemini-custom-model"
        assert client.client is None

    @patch("app.external.gemini_api.get_settings")
    def test_init_without_gemini_model(self, mock_get_settings):
        """初期化 - gemini_model なし"""
        mock_get_settings.return_value = create_mock_settings(gemini_model=None)

        client = GeminiAPIClient()

        assert client.default_model is None


class TestGeminiAPIClientInitialize:
    """GeminiAPIClient initialize メソッドのテスト"""

    @patch("app.external.gemini_api.genai.Client")
    @patch("app.external.gemini_api.service_account.Credentials.from_service_account_info")
    @patch("app.external.gemini_api.get_settings")
    def test_initialize_with_credentials_json_success(
        self, mock_get_settings, mock_from_service_account_info, mock_genai_client
    ):
        """initialize - GOOGLE_CREDENTIALS_JSON を使用して成功"""
        credentials_dict = {
            "type": "service_account",
            "project_id": "test-project-123",
            "private_key_id": "key123",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }

        mock_get_settings.return_value = create_mock_settings(
            google_project_id="test-project-123",
            google_location="us-central1",
            google_credentials_json=json.dumps(credentials_dict)
        )

        mock_credentials = MagicMock()
        mock_from_service_account_info.return_value = mock_credentials

        mock_client_instance = MagicMock()
        mock_genai_client.return_value = mock_client_instance

        client = GeminiAPIClient()
        result = client.initialize()

        assert result is True
        assert client.client is mock_client_instance

        mock_from_service_account_info.assert_called_once_with(
            credentials_dict,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )

        mock_genai_client.assert_called_once_with(
            vertexai=True,
            project="test-project-123",
            location="us-central1",
            credentials=mock_credentials,
        )

    @patch("app.external.gemini_api.genai.Client")
    @patch("app.external.gemini_api.get_settings")
    def test_initialize_without_credentials_json(
        self, mock_get_settings, mock_genai_client
    ):
        """initialize - GOOGLE_CREDENTIALS_JSON なし（デフォルト認証）"""
        mock_get_settings.return_value = create_mock_settings(
            google_project_id="test-project-456",
            google_location="global",
            google_credentials_json=None
        )

        mock_client_instance = MagicMock()
        mock_genai_client.return_value = mock_client_instance

        client = GeminiAPIClient()
        result = client.initialize()

        assert result is True
        assert client.client is mock_client_instance

        mock_genai_client.assert_called_once_with(
            vertexai=True,
            project="test-project-456",
            location="global",
        )

    @patch("app.external.gemini_api.get_settings")
    def test_initialize_missing_project_id(self, mock_get_settings):
        """initialize - GOOGLE_PROJECT_ID 未設定"""
        mock_get_settings.return_value = create_mock_settings(
            google_project_id=None
        )

        client = GeminiAPIClient()

        with pytest.raises(APIError) as exc_info:
            client.initialize()

        assert str(exc_info.value) == MESSAGES["CONFIG"]["VERTEX_AI_PROJECT_MISSING"]

    @patch("app.external.gemini_api.get_settings")
    def test_initialize_invalid_json_format(self, mock_get_settings):
        """initialize - 不正なJSON形式"""
        mock_get_settings.return_value = create_mock_settings(
            google_credentials_json="{ invalid json format"
        )

        client = GeminiAPIClient()

        with pytest.raises(APIError) as exc_info:
            client.initialize()

        assert "認証情報JSONのパースに失敗しました" in str(exc_info.value)

    @patch("app.external.gemini_api.service_account.Credentials.from_service_account_info")
    @patch("app.external.gemini_api.get_settings")
    def test_initialize_missing_credential_fields(
        self, mock_get_settings, mock_from_service_account_info
    ):
        """initialize - 認証情報フィールド不足"""
        incomplete_credentials = {"type": "service_account"}

        mock_get_settings.return_value = create_mock_settings(
            google_credentials_json=json.dumps(incomplete_credentials)
        )
        mock_from_service_account_info.side_effect = KeyError("project_id")

        client = GeminiAPIClient()

        with pytest.raises(APIError) as exc_info:
            client.initialize()

        assert "認証情報に必要なフィールドがありません" in str(exc_info.value)

    @patch("app.external.gemini_api.genai.Client")
    @patch("app.external.gemini_api.get_settings")
    def test_initialize_genai_client_error(self, mock_get_settings, mock_genai_client):
        """initialize - genai.Client 作成エラー"""
        mock_get_settings.return_value = create_mock_settings(
            google_credentials_json=None
        )
        mock_genai_client.side_effect = Exception("API接続エラー")

        client = GeminiAPIClient()

        with pytest.raises(APIError) as exc_info:
            client.initialize()

        error_message = str(exc_info.value)
        assert "Vertex AI初期化エラー" in error_message
        assert "API接続エラー" in error_message

    @patch("app.external.gemini_api.service_account.Credentials.from_service_account_info")
    @patch("app.external.gemini_api.get_settings")
    def test_initialize_credentials_creation_error(
        self, mock_get_settings, mock_from_service_account_info
    ):
        """initialize - 認証情報作成エラー"""
        credentials_dict = {"type": "service_account"}
        mock_get_settings.return_value = create_mock_settings(
            google_credentials_json=json.dumps(credentials_dict)
        )
        mock_from_service_account_info.side_effect = Exception("認証情報作成失敗")

        client = GeminiAPIClient()

        with pytest.raises(APIError) as exc_info:
            client.initialize()

        assert "認証情報の処理中にエラーが発生しました" in str(exc_info.value)


class TestGeminiAPIClientGenerateContent:
    """GeminiAPIClient _generate_content メソッドのテスト"""

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_success(self, mock_get_settings):
        """_generate_content - 正常系"""
        mock_get_settings.return_value = create_mock_settings()

        mock_client = MagicMock()
        mock_client.interactions.create.return_value = create_interaction(
            "生成されたサマリー", 2000, 1000
        )

        client = GeminiAPIClient()
        client.client = mock_client

        result = client._generate_content(
            prompt="テストプロンプト", model_name="gemini-3.8-flash"
        )

        assert result == ("生成されたサマリー", 2000, 1000)

        call_kwargs = mock_client.interactions.create.call_args[1]
        assert call_kwargs["model"] == "gemini-3.8-flash"
        assert call_kwargs["input"] == "テストプロンプト"
        assert call_kwargs["store"] is False
        assert "stream" not in call_kwargs
        assert "system_instruction" not in call_kwargs

    @pytest.mark.parametrize(
        ("setting", "expected"),
        [("LOW", "low"), ("HIGH", "high")],
    )
    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_thinking_level(self, mock_get_settings, setting, expected):
        """_generate_content - thinking_level が小文字で渡されること"""
        mock_get_settings.return_value = create_mock_settings(
            gemini_thinking_level=setting
        )

        mock_client = MagicMock()
        mock_client.interactions.create.return_value = create_interaction("テキスト")

        client = GeminiAPIClient()
        client.client = mock_client

        client._generate_content(prompt="プロンプト", model_name="test-model")

        call_kwargs = mock_client.interactions.create.call_args[1]
        assert call_kwargs["generation_config"] == {"thinking_level": expected}

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_with_system_prompt(self, mock_get_settings):
        """_generate_content - システムプロンプトが system_instruction で渡されること"""
        mock_get_settings.return_value = create_mock_settings()

        mock_client = MagicMock()
        mock_client.interactions.create.return_value = create_interaction("テキスト")

        client = GeminiAPIClient()
        client.client = mock_client

        client._generate_content(
            prompt="プロンプト", model_name="test-model", system_prompt="システム指示"
        )

        call_kwargs = mock_client.interactions.create.call_args[1]
        assert call_kwargs["system_instruction"] == "システム指示"

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_no_usage(self, mock_get_settings):
        """_generate_content - usage なし"""
        mock_get_settings.return_value = create_mock_settings()

        mock_client = MagicMock()
        mock_client.interactions.create.return_value = create_interaction("サマリー")

        client = GeminiAPIClient()
        client.client = mock_client

        result = client._generate_content(prompt="プロンプト", model_name="test-model")

        assert result == ("サマリー", 0, 0)

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_unexpected_response(self, mock_get_settings):
        """_generate_content - Interaction 以外の応答"""
        mock_get_settings.return_value = create_mock_settings()

        mock_client = MagicMock()
        mock_client.interactions.create.return_value = MagicMock()

        client = GeminiAPIClient()
        client.client = mock_client

        with pytest.raises(APIError) as exc_info:
            client._generate_content(prompt="プロンプト", model_name="test-model")

        assert MESSAGES["ERROR"]["GEMINI_UNEXPECTED_RESPONSE"] in str(exc_info.value)

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_api_error(self, mock_get_settings):
        """_generate_content - API呼び出しエラー"""
        mock_get_settings.return_value = create_mock_settings()

        mock_client = MagicMock()
        mock_client.interactions.create.side_effect = Exception("Vertex AI APIエラー")

        client = GeminiAPIClient()
        client.client = mock_client

        with pytest.raises(APIError) as exc_info:
            client._generate_content(prompt="プロンプト", model_name="test-model")

        error_message = str(exc_info.value)
        assert "Vertex AI API呼び出しエラー" in error_message
        assert "Vertex AI APIエラー" in error_message

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_client_not_initialized(self, mock_get_settings):
        """_generate_content - クライアント未初期化"""
        mock_get_settings.return_value = create_mock_settings()

        client = GeminiAPIClient()
        # client.client は None のまま

        with pytest.raises(APIError) as exc_info:
            client._generate_content(prompt="プロンプト", model_name="test-model")

        assert "Gemini API クライアントが初期化されていません" in str(exc_info.value)


class TestGeminiAPIClientGenerateContentStream:
    """GeminiAPIClient _generate_content_stream メソッドのテスト"""

    @patch("app.external.gemini_api.get_settings")
    def test_stream_success(self, mock_get_settings):
        """テキスト差分を順に返し、最後にトークン数を返すこと"""
        mock_get_settings.return_value = create_mock_settings()

        mock_client = MagicMock()
        mock_client.interactions.create.return_value = iter([
            create_text_delta_event("紹介"),
            create_text_delta_event("状"),
            create_completed_event(300, 120),
        ])

        client = GeminiAPIClient()
        client.client = mock_client

        chunks = list(
            client._generate_content_stream(
                prompt="プロンプト", model_name="test-model", system_prompt="システム指示"
            )
        )

        assert chunks == ["紹介", "状", {"input_tokens": 300, "output_tokens": 120}]

        call_kwargs = mock_client.interactions.create.call_args[1]
        assert call_kwargs["stream"] is True
        assert call_kwargs["store"] is False
        assert call_kwargs["system_instruction"] == "システム指示"

    @patch("app.external.gemini_api.get_settings")
    def test_stream_without_completed_event(self, mock_get_settings):
        """完了イベントがない場合はトークン数 0 を返すこと"""
        mock_get_settings.return_value = create_mock_settings()

        mock_client = MagicMock()
        mock_client.interactions.create.return_value = iter([
            create_text_delta_event("本文"),
        ])

        client = GeminiAPIClient()
        client.client = mock_client

        chunks = list(client._generate_content_stream(prompt="プロンプト", model_name="test-model"))

        assert chunks == ["本文", {"input_tokens": 0, "output_tokens": 0}]

    @patch("app.external.gemini_api.get_settings")
    def test_stream_client_not_initialized(self, mock_get_settings):
        """クライアント未初期化時に APIError を発生させること"""
        mock_get_settings.return_value = create_mock_settings()

        client = GeminiAPIClient()

        with pytest.raises(APIError) as exc_info:
            list(client._generate_content_stream(prompt="プロンプト", model_name="test-model"))

        assert "Gemini API クライアントが初期化されていません" in str(exc_info.value)


class TestGeminiAPIClientIntegration:
    """GeminiAPIClient 統合テスト"""

    @patch("app.external.gemini_api.genai.Client")
    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    @patch("app.external.gemini_api.get_settings")
    def test_full_generate_summary_flow(
        self, mock_get_settings, mock_db_session, mock_get_prompt, mock_genai_client
    ):
        """完全な文書生成フロー"""
        mock_get_settings.return_value = create_mock_settings(
            google_project_id="test-project",
            google_location="global",
            gemini_model="gemini-1.5-pro-002",
            gemini_thinking_level="HIGH",
            google_credentials_json=None
        )

        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_get_prompt.return_value = None

        mock_client_instance = MagicMock()
        mock_client_instance.interactions.create.return_value = create_interaction(
            "生成された診療情報提供書", 3000, 1500
        )
        mock_genai_client.return_value = mock_client_instance

        client = GeminiAPIClient()
        result = client.generate_summary(
            medical_text="患者情報",
            additional_info="追加情報",
            current_prescription="処方内容",
            document_type="他院への紹介",
            model_name="gemini-1.5-pro-002",
        )

        assert result == ("生成された診療情報提供書", 3000, 1500)

    @patch("app.external.gemini_api.get_settings")
    def test_generate_summary_initialization_error(self, mock_get_settings):
        """generate_summary - 初期化エラー"""
        mock_get_settings.return_value = create_mock_settings(
            google_project_id=None
        )

        client = GeminiAPIClient()

        with pytest.raises(APIError) as exc_info:
            client.generate_summary(medical_text="データ")

        assert MESSAGES["CONFIG"]["VERTEX_AI_PROJECT_MISSING"] in str(exc_info.value)


class TestGeminiAPIClientEdgeCases:
    """GeminiAPIClient エッジケース"""

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_very_long_prompt(self, mock_get_settings):
        """_generate_content - 非常に長いプロンプト"""
        mock_get_settings.return_value = create_mock_settings(
            gemini_thinking_level="LOW"
        )

        mock_client = MagicMock()
        mock_client.interactions.create.return_value = create_interaction(
            "サマリー", 100000, 5000
        )

        client = GeminiAPIClient()
        client.client = mock_client

        long_prompt = "あ" * 200000
        result = client._generate_content(prompt=long_prompt, model_name="test-model")

        assert result == ("サマリー", 100000, 5000)

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_special_characters(self, mock_get_settings):
        """_generate_content - 特殊文字を含むプロンプト"""
        mock_get_settings.return_value = create_mock_settings(
            gemini_thinking_level="LOW"
        )

        mock_client = MagicMock()
        mock_client.interactions.create.return_value = create_interaction("結果", 100, 50)

        client = GeminiAPIClient()
        client.client = mock_client

        special_prompt = "特殊文字: \n\t\r\n!@#$%^&*(){}[]<>?/\\|`~"
        result = client._generate_content(
            prompt=special_prompt, model_name="test-model"
        )

        assert result[0] == "結果"

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_empty_prompt(self, mock_get_settings):
        """_generate_content - 空のプロンプト"""
        mock_get_settings.return_value = create_mock_settings(
            gemini_thinking_level="LOW"
        )

        mock_client = MagicMock()
        mock_client.interactions.create.return_value = create_interaction(
            "空レスポンス", 0, 10
        )

        client = GeminiAPIClient()
        client.client = mock_client

        result = client._generate_content(prompt="", model_name="test-model")

        assert result == ("空レスポンス", 0, 10)

    @patch("app.external.gemini_api.genai.Client")
    @patch("app.external.gemini_api.get_settings")
    def test_initialize_empty_project_id(self, mock_get_settings, mock_genai_client):
        """initialize - 空の PROJECT_ID"""
        mock_get_settings.return_value = create_mock_settings(
            google_project_id=""
        )

        client = GeminiAPIClient()

        with pytest.raises(APIError) as exc_info:
            client.initialize()

        assert MESSAGES["CONFIG"]["VERTEX_AI_PROJECT_MISSING"] in str(exc_info.value)

    @patch("app.external.gemini_api.genai.Client")
    @patch("app.external.gemini_api.get_settings")
    def test_initialize_empty_credentials_json(
        self, mock_get_settings, mock_genai_client
    ):
        """initialize - 空の GOOGLE_CREDENTIALS_JSON"""
        mock_get_settings.return_value = create_mock_settings(
            google_project_id="test-project",
            google_location="global",
            google_credentials_json=""
        )

        mock_client_instance = MagicMock()
        mock_genai_client.return_value = mock_client_instance

        client = GeminiAPIClient()
        result = client.initialize()

        assert result is True
        mock_genai_client.assert_called_once_with(
            vertexai=True,
            project="test-project",
            location="global",
        )


class TestGeminiAPIClientEvaluationModel:
    """評価用モデル指定のテスト"""

    @patch("app.external.gemini_api.get_settings")
    def test_init_with_evaluation_model(self, mock_get_settings):
        """初期化 - 評価用モデル指定"""
        mock_get_settings.return_value = create_mock_settings(
            gemini_model="gemini-1.5-pro-002",
            gemini_evaluation_model="gemini-eval-model"
        )

        client = GeminiAPIClient(model_name="gemini-eval-model")

        assert client.default_model == "gemini-eval-model"

    @patch("app.external.gemini_api.genai.Client")
    @patch("app.external.gemini_api.get_settings")
    def test_evaluation_flow(self, mock_get_settings, mock_genai_client):
        """評価フローのテスト"""
        mock_settings = create_mock_settings(
            google_credentials_json=None,
            gemini_thinking_level="HIGH"
        )
        mock_get_settings.return_value = mock_settings

        mock_client_instance = MagicMock()
        mock_client_instance.interactions.create.return_value = create_interaction(
            "評価結果", 500, 200
        )
        mock_genai_client.return_value = mock_client_instance

        client = GeminiAPIClient(model_name="gemini-eval-model")
        client.initialize()

        result = client._generate_content(
            prompt="評価プロンプト",
            model_name="gemini-eval-model"
        )

        assert result == ("評価結果", 500, 200)


class TestGeminiAPIClientNetworkErrors:
    """GeminiAPIClient ネットワークエラーシナリオのテスト"""

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_connection_timeout(self, mock_get_settings):
        """接続タイムアウト時に APIError を発生させること"""
        import socket
        mock_get_settings.return_value = create_mock_settings()

        mock_client = MagicMock()
        mock_client.interactions.create.side_effect = socket.timeout("接続タイムアウト")

        client = GeminiAPIClient()
        client.client = mock_client
        client.settings = mock_get_settings.return_value

        with pytest.raises(APIError) as exc_info:
            client._generate_content(prompt="テストプロンプト", model_name="test-model")

        assert "Vertex AI API呼び出しエラー" in str(exc_info.value)

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_connection_reset(self, mock_get_settings):
        """接続リセット時に APIError を発生させること"""
        mock_get_settings.return_value = create_mock_settings()

        mock_client = MagicMock()
        mock_client.interactions.create.side_effect = ConnectionResetError("接続がリセットされました")

        client = GeminiAPIClient()
        client.client = mock_client
        client.settings = mock_get_settings.return_value

        with pytest.raises(APIError) as exc_info:
            client._generate_content(prompt="テストプロンプト", model_name="test-model")

        assert "Vertex AI API呼び出しエラー" in str(exc_info.value)

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_service_unavailable(self, mock_get_settings):
        """503 Service Unavailable 相当エラー時に APIError を発生させること"""
        mock_get_settings.return_value = create_mock_settings()

        mock_client = MagicMock()
        mock_client.interactions.create.side_effect = Exception("503 Service Unavailable")

        client = GeminiAPIClient()
        client.client = mock_client
        client.settings = mock_get_settings.return_value

        with pytest.raises(APIError) as exc_info:
            client._generate_content(prompt="テストプロンプト", model_name="test-model")

        assert "Vertex AI API呼び出しエラー" in str(exc_info.value)
        assert "503" in str(exc_info.value)

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_stream_connection_timeout(self, mock_get_settings):
        """ストリーム生成中のタイムアウト時に APIError を発生させること"""
        import socket
        mock_get_settings.return_value = create_mock_settings()

        mock_client = MagicMock()
        mock_client.interactions.create.side_effect = socket.timeout("ストリームタイムアウト")

        client = GeminiAPIClient()
        client.client = mock_client
        client.settings = mock_get_settings.return_value

        with pytest.raises(APIError) as exc_info:
            list(client._generate_content_stream(prompt="テスト", model_name="test-model"))

        assert "Vertex AI API呼び出しエラー" in str(exc_info.value)

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_stream_error_mid_stream(self, mock_get_settings):
        """ストリーム途中でエラーが発生した場合に APIError を発生させること"""
        mock_get_settings.return_value = create_mock_settings()

        def error_generator():
            yield create_text_delta_event("最初のチャンク")
            raise ConnectionError("ストリーム途中で切断")

        mock_client = MagicMock()
        mock_client.interactions.create.return_value = error_generator()

        client = GeminiAPIClient()
        client.client = mock_client
        client.settings = mock_get_settings.return_value

        with pytest.raises(APIError) as exc_info:
            list(client._generate_content_stream(prompt="テスト", model_name="test-model"))

        assert "Vertex AI API呼び出しエラー" in str(exc_info.value)

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_no_text_output(self, mock_get_settings):
        """テキスト出力がない場合に空文字を返すこと"""
        mock_get_settings.return_value = create_mock_settings()

        mock_client = MagicMock()
        mock_client.interactions.create.return_value = create_interaction()

        client = GeminiAPIClient()
        client.client = mock_client
        client.settings = mock_get_settings.return_value

        result = client._generate_content(prompt="テスト", model_name="test-model")

        assert result == ("", 0, 0)

    @patch("app.external.gemini_api.genai.Client")
    @patch("app.external.gemini_api.get_settings")
    def test_initialize_missing_project_id(self, mock_get_settings, mock_genai_client):
        """google_project_id が未設定の場合に APIError を発生させること"""
        mock_get_settings.return_value = create_mock_settings(google_project_id=None)

        client = GeminiAPIClient()

        with pytest.raises(APIError) as exc_info:
            client.initialize()

        assert "GOOGLE_PROJECT_ID" in str(exc_info.value)
