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
            create_client("invalid_provider")  # type: ignore


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
        # DEFAULT_DOCUMENT_TYPE が使用される（constants.py: "退院時サマリ"）
        assert call_args[4] == "退院時サマリ"


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


class TestGenerateSummaryStreamWithProvider:
    """generate_summary_stream_with_provider 関数のテスト"""

    @patch.object(ClaudeAPIClient, "generate_summary_stream")
    @patch.object(ClaudeAPIClient, "initialize")
    def test_stream_with_claude(self, _mock_init, mock_stream):
        """Claude プロバイダーでストリームジェネレータを返す"""
        from app.external.api_factory import generate_summary_stream_with_provider

        mock_stream.return_value = iter(["チャンク1", "チャンク2"])

        result = generate_summary_stream_with_provider(
            provider=APIProvider.CLAUDE,
            medical_text="カルテ情報",
            additional_info="追加情報",
            current_prescription="薬剤A",
        )

        mock_stream.assert_called_once()
        chunks = list(result)
        assert chunks == ["チャンク1", "チャンク2"]

    @patch.object(GeminiAPIClient, "generate_summary_stream")
    @patch.object(GeminiAPIClient, "initialize")
    def test_stream_with_gemini(self, _mock_init, mock_stream):
        """Gemini プロバイダーでストリームジェネレータを返す"""
        from app.external.api_factory import generate_summary_stream_with_provider

        mock_stream.return_value = iter(["チャンクA", "チャンクB"])

        result = generate_summary_stream_with_provider(
            provider=APIProvider.GEMINI,
            medical_text="カルテ情報",
        )

        mock_stream.assert_called_once()
        chunks = list(result)
        assert chunks == ["チャンクA", "チャンクB"]

    @patch.object(ClaudeAPIClient, "generate_summary_stream")
    @patch.object(ClaudeAPIClient, "initialize")
    def test_stream_passes_model_name(self, _mock_init, mock_stream):
        """model_name がクライアントに渡される"""
        from app.external.api_factory import generate_summary_stream_with_provider

        mock_stream.return_value = iter([])

        generate_summary_stream_with_provider(
            provider="claude",
            medical_text="テキスト",
            model_name="claude-3-5-sonnet",
        )

        call_args = mock_stream.call_args[0]
        assert "claude-3-5-sonnet" in call_args


class TestCreateClientErrorScenarios:
    """create_client エラーシナリオのテスト"""

    def test_create_client_invalid_string_raises_api_error(self):
        """無効なプロバイダー文字列が APIError を発生させること"""
        with pytest.raises(APIError) as exc_info:
            create_client("gpt4")

        assert "gpt4" in str(exc_info.value)

    def test_create_client_empty_string_raises_api_error(self):
        """空文字列が APIError を発生させること"""
        with pytest.raises(APIError):
            create_client("")

    def test_create_client_numeric_string_raises_api_error(self):
        """数値文字列が APIError を発生させること"""
        with pytest.raises(APIError):
            create_client("123")

    def test_create_client_returns_independent_instances(self):
        """複数回呼び出しで独立したインスタンスを返すこと"""
        client1 = create_client(APIProvider.CLAUDE)
        client2 = create_client(APIProvider.CLAUDE)
        assert client1 is not client2

    def test_create_client_openai_raises_api_error(self):
        """サポート外プロバイダー 'openai' が APIError を発生させること"""
        with pytest.raises(APIError) as exc_info:
            create_client("openai")

        assert "openai" in str(exc_info.value)


class TestGenerateSummaryWithProviderErrors:
    """generate_summary_with_provider エラーシナリオのテスト"""

    def test_generate_with_invalid_provider_raises_api_error(self):
        """無効なプロバイダーで APIError を発生させること"""
        with pytest.raises(APIError):
            generate_summary_with_provider(
                provider="invalid_provider",
                medical_text="カルテ情報",
            )

    @patch.object(ClaudeAPIClient, "initialize")
    @patch.object(ClaudeAPIClient, "generate_summary")
    def test_generate_propagates_api_error(self, mock_generate, mock_init):
        """クライアントから APIError が伝播すること"""
        mock_generate.side_effect = APIError("API呼び出し失敗")

        with pytest.raises(APIError, match="API呼び出し失敗"):
            generate_summary_with_provider(
                provider=APIProvider.CLAUDE,
                medical_text="カルテ情報",
            )

    @patch.object(GeminiAPIClient, "initialize")
    @patch.object(GeminiAPIClient, "generate_summary")
    def test_generate_gemini_propagates_connection_error(self, mock_generate, mock_init):
        """Gemini クライアントの接続エラーが伝播すること"""
        mock_generate.side_effect = APIError("Vertex AI接続エラー")

        with pytest.raises(APIError, match="Vertex AI接続エラー"):
            generate_summary_with_provider(
                provider=APIProvider.GEMINI,
                medical_text="カルテ情報",
            )
