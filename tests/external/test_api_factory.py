from unittest.mock import patch

import pytest

from app.external.api_factory import (
    APIProvider,
    create_client,
    generate_summary_with_provider,
)
from app.external.claude_api import ClaudeAPIClient
from app.external.gemini_api import GeminiAPIClient
from app.utils.exceptions import APIError


class TestAPIProvider:
    """APIProvider Enum のテスト"""

    def test_api_provider_values(self):
        """APIProvider の値確認"""
        assert APIProvider.CLAUDE.value == "claude"
        assert APIProvider.GEMINI.value == "gemini"

    def test_api_provider_from_string(self):
        """文字列からAPIProvider取得"""
        assert APIProvider("claude") == APIProvider.CLAUDE
        assert APIProvider("gemini") == APIProvider.GEMINI

    def test_api_provider_invalid_string(self):
        """無効な文字列"""
        with pytest.raises(ValueError):
            APIProvider("invalid")


class TestCreateClient:
    """create_client 関数のテスト"""

    def test_create_client_claude_enum(self):
        """クライアント作成 - Claude（Enum）"""
        client = create_client(APIProvider.CLAUDE)
        assert isinstance(client, ClaudeAPIClient)

    def test_create_client_gemini_enum(self):
        """クライアント作成 - Gemini（Enum）"""
        client = create_client(APIProvider.GEMINI)
        assert isinstance(client, GeminiAPIClient)

    def test_create_client_claude_string(self):
        """クライアント作成 - Claude（文字列）"""
        client = create_client("claude")
        assert isinstance(client, ClaudeAPIClient)

    def test_create_client_gemini_string(self):
        """クライアント作成 - Gemini（文字列）"""
        client = create_client("gemini")
        assert isinstance(client, GeminiAPIClient)

    def test_create_client_case_insensitive(self):
        """クライアント作成 - 大文字小文字を無視"""
        client1 = create_client("CLAUDE")
        client2 = create_client("Claude")
        client3 = create_client("claude")

        assert isinstance(client1, ClaudeAPIClient)
        assert isinstance(client2, ClaudeAPIClient)
        assert isinstance(client3, ClaudeAPIClient)

    def test_create_client_invalid_provider_string(self):
        """クライアント作成 - 無効なプロバイダー（文字列）"""
        with pytest.raises(APIError) as exc_info:
            create_client("gpt-4")

        assert "未対応のAPIプロバイダー" in str(exc_info.value)

    def test_create_client_invalid_provider_type(self):
        """クライアント作成 - 無効なプロバイダータイプ"""
        with pytest.raises(APIError):
            create_client(123)


class TestGenerateSummaryWithProvider:
    """generate_summary_with_provider 関数のテスト"""

    @patch.object(ClaudeAPIClient, "generate_summary")
    def test_generate_summary_claude_minimal(self, mock_generate):
        """文書生成 - Claude 最小パラメータ"""
        mock_generate.return_value = ("生成された文書", 1000, 500)

        result = generate_summary_with_provider(
            provider="claude",
            medical_text="患者情報",
        )

        assert result == ("生成された文書", 1000, 500)
        mock_generate.assert_called_once()

        call_args = mock_generate.call_args[0]
        assert call_args[0] == "患者情報"
        assert call_args[1] == ""  # additional_info
        assert call_args[2] == ""  # current_prescription

    @patch.object(GeminiAPIClient, "generate_summary")
    def test_generate_summary_gemini_all_params(self, mock_generate):
        """文書生成 - Gemini 全パラメータ"""
        mock_generate.return_value = ("生成された文書", 2000, 800)

        result = generate_summary_with_provider(
            provider="gemini",
            medical_text="カルテ情報",
            additional_info="追加情報",
            current_prescription="処方内容",
            department="眼科",
            document_type="他院への紹介",
            doctor="橋本義弘",
            model_name="gemini-1.5-pro-002",
        )

        assert result == ("生成された文書", 2000, 800)
        mock_generate.assert_called_once()

        # generate_summary(medical_text, additional_info, current_prescription, department, document_type, doctor, model_name)
        call_args = mock_generate.call_args[0]
        assert call_args[0] == "カルテ情報"
        assert call_args[1] == "追加情報"
        assert call_args[2] == "処方内容"
        assert call_args[3] == "眼科"
        assert call_args[4] == "他院への紹介"
        assert call_args[5] == "橋本義弘"
        assert call_args[6] == "gemini-1.5-pro-002"

    @patch.object(ClaudeAPIClient, "generate_summary")
    def test_generate_summary_with_enum(self, mock_generate):
        """文書生成 - Enum を使用"""
        mock_generate.return_value = ("文書", 1500, 600)

        result = generate_summary_with_provider(
            provider=APIProvider.CLAUDE,
            medical_text="テストデータ",
        )

        assert result == ("文書", 1500, 600)

    def test_generate_summary_invalid_provider(self):
        """文書生成 - 無効なプロバイダー"""
        with pytest.raises(APIError) as exc_info:
            generate_summary_with_provider(
                provider="invalid",
                medical_text="データ",
            )

        assert "未対応のAPIプロバイダー" in str(exc_info.value)

    @patch.object(ClaudeAPIClient, "generate_summary")
    def test_generate_summary_client_exception(self, mock_generate):
        """文書生成 - クライアント例外"""
        mock_generate.side_effect = Exception("API エラー")

        with pytest.raises(Exception) as exc_info:
            generate_summary_with_provider(
                provider="claude",
                medical_text="データ",
            )

        assert "API エラー" in str(exc_info.value)

    @patch.object(ClaudeAPIClient, "generate_summary")
    def test_generate_summary_default_document_type(self, mock_generate):
        """文書生成 - デフォルト文書タイプ"""
        mock_generate.return_value = ("文書", 1000, 500)

        generate_summary_with_provider(
            provider="claude",
            medical_text="データ",
        )

        # generate_summary(medical_text, additional_info, current_prescription, department, document_type, doctor, model_name)
        call_args = mock_generate.call_args[0]
        # DEFAULT_DOCUMENT_TYPE が使用される（constants.py: "他院への紹介"）
        assert call_args[4] == "他院への紹介"


class TestEdgeCases:
    """API Factory 関数のエッジケース"""

    def test_create_multiple_clients_independence(self):
        """複数クライアント作成 - 独立性確認"""
        client1 = create_client("claude")
        client2 = create_client("claude")

        assert client1 is not client2
        assert isinstance(client1, ClaudeAPIClient)
        assert isinstance(client2, ClaudeAPIClient)

    def test_create_different_clients(self):
        """異なるクライアントの作成"""
        claude_client = create_client("claude")
        gemini_client = create_client("gemini")

        assert type(claude_client) != type(gemini_client)
        assert isinstance(claude_client, ClaudeAPIClient)
        assert isinstance(gemini_client, GeminiAPIClient)

    @patch.object(ClaudeAPIClient, "generate_summary")
    def test_generate_summary_empty_optional_fields(self, mock_generate):
        """文書生成 - 空のオプションフィールド"""
        mock_generate.return_value = ("文書", 1000, 500)

        result = generate_summary_with_provider(provider="claude", medical_text="患者データ")

        assert result == ("文書", 1000, 500)

        # generate_summary(medical_text, additional_info, current_prescription, department, document_type, doctor, model_name)
        call_args = mock_generate.call_args[0]
        assert call_args[1] == ""   # additional_info
        assert call_args[2] == ""   # current_prescription

    @patch.object(ClaudeAPIClient, "generate_summary")
    def test_generate_summary_none_model_name(self, mock_generate):
        """文書生成 - model_name が None"""
        mock_generate.return_value = ("文書", 1000, 500)

        result = generate_summary_with_provider(provider="claude", medical_text="データ")

        assert result == ("文書", 1000, 500)

        # generate_summary(medical_text, additional_info, current_prescription, department, document_type, doctor, model_name)
        call_args = mock_generate.call_args[0]
        assert call_args[6] is None  # model_name
