import json
from unittest.mock import MagicMock, patch

import pytest

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
    def test_generate_content_success_with_low_thinking(self, mock_get_settings):
        """_generate_content - 正常系（ThinkingLevel.LOW）"""
        mock_get_settings.return_value = create_mock_settings(
            gemini_thinking_level="LOW"
        )

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "生成されたサマリー"
        mock_response.usage_metadata.prompt_token_count = 2000
        mock_response.usage_metadata.candidates_token_count = 1000

        mock_client.models.generate_content.return_value = mock_response

        client = GeminiAPIClient()
        client.client = mock_client

        result = client._generate_content(
            prompt="テストプロンプト", model_name="gemini-1.5-pro-002"
        )

        assert result == ("生成されたサマリー", 2000, 1000)

        call_args = mock_client.models.generate_content.call_args
        assert call_args[1]["model"] == "gemini-1.5-pro-002"
        assert call_args[1]["contents"] == "テストプロンプト"

    @patch("app.external.gemini_api.types")
    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_success_with_high_thinking(
        self, mock_get_settings, mock_types
    ):
        """_generate_content - 正常系（ThinkingLevel.HIGH）"""
        mock_get_settings.return_value = create_mock_settings(
            gemini_thinking_level="HIGH"
        )

        mock_types.ThinkingLevel.HIGH = "HIGH"
        mock_types.ThinkingLevel.LOW = "LOW"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "高品質サマリー"
        mock_response.usage_metadata.prompt_token_count = 3000
        mock_response.usage_metadata.candidates_token_count = 1500

        mock_client.models.generate_content.return_value = mock_response

        client = GeminiAPIClient()
        client.client = mock_client

        result = client._generate_content(
            prompt="プロンプト", model_name="gemini-1.5-pro-002"
        )

        assert result == ("高品質サマリー", 3000, 1500)

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_no_text_attribute(self, mock_get_settings):
        """_generate_content - text 属性なし"""
        mock_get_settings.return_value = create_mock_settings(
            gemini_thinking_level="LOW"
        )

        mock_client = MagicMock()

        class NoTextResponse:
            def __init__(self):
                self.usage_metadata = MagicMock()
                self.usage_metadata.prompt_token_count = 100
                self.usage_metadata.candidates_token_count = 50

            def __str__(self):
                return "文字列化されたレスポンス"

        mock_response = NoTextResponse()
        mock_client.models.generate_content.return_value = mock_response

        client = GeminiAPIClient()
        client.client = mock_client

        result = client._generate_content(prompt="プロンプト", model_name="test-model")

        assert result == ("文字列化されたレスポンス", 100, 50)

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_no_usage_metadata(self, mock_get_settings):
        """_generate_content - usage_metadata なし"""
        mock_get_settings.return_value = create_mock_settings(
            gemini_thinking_level="LOW"
        )

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "サマリー"
        delattr(mock_response, "usage_metadata")

        mock_client.models.generate_content.return_value = mock_response

        client = GeminiAPIClient()
        client.client = mock_client

        result = client._generate_content(prompt="プロンプト", model_name="test-model")

        assert result == ("サマリー", 0, 0)

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_api_error(self, mock_get_settings):
        """_generate_content - API呼び出しエラー"""
        mock_get_settings.return_value = create_mock_settings(
            gemini_thinking_level="LOW"
        )

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception(
            "Vertex AI APIエラー"
        )

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

    @patch("app.external.gemini_api.get_settings")
    def test_generate_content_thinking_level_config(self, mock_get_settings):
        """_generate_content - ThinkingLevel 設定確認"""
        mock_get_settings.return_value = create_mock_settings(
            gemini_thinking_level="LOW"
        )

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "テキスト"
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50

        mock_client.models.generate_content.return_value = mock_response

        client = GeminiAPIClient()
        client.client = mock_client

        client._generate_content(prompt="プロンプト", model_name="test-model")

        call_args = mock_client.models.generate_content.call_args
        config = call_args[1]["config"]
        assert config is not None


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
        mock_response = MagicMock()
        mock_response.text = "生成された診療情報提供書"
        mock_response.usage_metadata.prompt_token_count = 3000
        mock_response.usage_metadata.candidates_token_count = 1500

        mock_client_instance.models.generate_content.return_value = mock_response
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
        mock_response = MagicMock()
        mock_response.text = "サマリー"
        mock_response.usage_metadata.prompt_token_count = 100000
        mock_response.usage_metadata.candidates_token_count = 5000

        mock_client.models.generate_content.return_value = mock_response

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
        mock_response = MagicMock()
        mock_response.text = "結果"
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50

        mock_client.models.generate_content.return_value = mock_response

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
        mock_response = MagicMock()
        mock_response.text = "空レスポンス"
        mock_response.usage_metadata.prompt_token_count = 0
        mock_response.usage_metadata.candidates_token_count = 10

        mock_client.models.generate_content.return_value = mock_response

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
        mock_response = MagicMock()
        mock_response.text = "評価結果"
        mock_response.usage_metadata.prompt_token_count = 500
        mock_response.usage_metadata.candidates_token_count = 200

        mock_client_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        client = GeminiAPIClient(model_name="gemini-eval-model")
        client.initialize()

        result = client._generate_content(
            prompt="評価プロンプト",
            model_name="gemini-eval-model"
        )

        assert result == ("評価結果", 500, 200)
