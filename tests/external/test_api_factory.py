from unittest.mock import patch

from app.core.constants import ModelType
from app.external.api_factory import create_client


class TestCreateClient:
    """create_client 関数のテスト"""

    @patch("app.external.api_factory.GeminiAPIClient")
    @patch("app.external.api_factory.ClaudeAPIClient")
    def test_create_client_claude(self, mock_claude, mock_gemini):
        """クライアント作成 - Claude"""
        client = create_client(ModelType.CLAUDE)

        assert client is mock_claude.return_value
        mock_gemini.assert_not_called()

    @patch("app.external.api_factory.GeminiAPIClient")
    @patch("app.external.api_factory.ClaudeAPIClient")
    def test_create_client_gemini(self, mock_claude, mock_gemini):
        """クライアント作成 - Gemini"""
        client = create_client(ModelType.GEMINI)

        assert client is mock_gemini.return_value
        mock_claude.assert_not_called()

    @patch("app.external.api_factory.ClaudeAPIClient")
    def test_create_client_returns_new_instance_each_time(self, mock_claude):
        """クライアント作成 - 呼び出しごとに生成する"""
        create_client(ModelType.CLAUDE)
        create_client(ModelType.CLAUDE)

        assert mock_claude.call_count == 2

    @patch("app.external.api_factory.ClaudeAPIClient")
    def test_create_client_propagates_init_error(self, mock_claude):
        """クライアント作成 - 初期化時の例外はそのまま伝播する"""
        mock_claude.side_effect = RuntimeError("初期化失敗")

        try:
            create_client(ModelType.CLAUDE)
        except RuntimeError as e:
            assert str(e) == "初期化失敗"
        else:
            raise AssertionError("例外が送出されなかった")
