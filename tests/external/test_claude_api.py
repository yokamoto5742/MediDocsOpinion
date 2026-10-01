"""ClaudeAPIClient のテスト"""

from unittest.mock import MagicMock, patch

import pytest
from anthropic import omit
from anthropic.types import TextBlock

from app.core.constants import CLAUDE_GENERATION_TEMPERATURE, MESSAGES
from app.external.claude_api import ClaudeAPIClient
from app.schemas.summary import SummaryRequest
from app.utils.exceptions import APIError


def create_response(content, stop_reason="end_turn", input_tokens=1500, output_tokens=800):
    """テスト用の Messages API レスポンスを作成"""
    response = MagicMock()
    response.content = content
    response.stop_reason = stop_reason
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    return response


@pytest.fixture
def bedrock():
    """AnthropicBedrock をモックに差し替え、生成されたモッククライアントを返す"""
    with (
        patch("app.external.claude_api.get_settings") as mock_get_settings,
        patch("app.external.claude_api.AnthropicBedrock") as mock_bedrock,
    ):
        mock_get_settings.return_value.aws_region = "ap-northeast-1"
        yield mock_bedrock


class TestClaudeAPIClientInit:
    """ClaudeAPIClient 初期化のテスト"""

    def test_init_creates_bedrock_client(self, bedrock):
        """初期化 - リージョンを指定して Bedrock クライアントを生成する"""
        client = ClaudeAPIClient()

        bedrock.assert_called_once_with(aws_region="ap-northeast-1")
        assert client.client is bedrock.return_value

    def test_init_error_propagates(self, bedrock):
        """初期化 - クライアント生成時の例外はそのまま伝播する"""
        bedrock.side_effect = ConnectionError("Network unreachable")

        with pytest.raises(ConnectionError):
            ClaudeAPIClient()


class TestClaudeAPIClientGenerateContent:
    """ClaudeAPIClient generate_content メソッドのテスト"""

    def test_generate_content_success(self, bedrock):
        """generate_content - 正常系"""
        create = bedrock.return_value.messages.create
        create.return_value = create_response(
            [TextBlock(type="text", text="生成されたサマリー")]
        )

        result = ClaudeAPIClient().generate_content(
            prompt="テストプロンプト", model_name="claude-3-5-sonnet-20241022"
        )

        assert result == ("生成されたサマリー", 1500, 800)
        create.assert_called_once_with(
            model="claude-3-5-sonnet-20241022",
            max_tokens=6000,
            system=omit,
            messages=[{"role": "user", "content": "テストプロンプト"}],
            extra_body={"temperature": CLAUDE_GENERATION_TEMPERATURE},
        )

    def test_generate_content_with_system_prompt(self, bedrock):
        """generate_content - システムプロンプト指定"""
        create = bedrock.return_value.messages.create
        create.return_value = create_response(
            [TextBlock(type="text", text="生成されたサマリー")]
        )

        ClaudeAPIClient().generate_content(
            prompt="ユーザープロンプト",
            model_name="claude-3-5-sonnet-20241022",
            system_prompt="システムプロンプト",
        )

        assert create.call_args.kwargs["system"] == "システムプロンプト"

    def test_generate_content_truncated_output(self, bedrock):
        """generate_content - max_tokens到達時に警告を付加"""
        bedrock.return_value.messages.create.return_value = create_response(
            [TextBlock(type="text", text="途中で切れた文書")],
            stop_reason="max_tokens",
            output_tokens=6000,
        )

        summary_text, _, _ = ClaudeAPIClient().generate_content(
            prompt="テストプロンプト", model_name="claude-3-5-sonnet-20241022"
        )

        assert summary_text.startswith("途中で切れた文書")
        assert MESSAGES["WARNING"]["OUTPUT_TRUNCATED"] in summary_text

    def test_generate_content_uses_first_text_block(self, bedrock):
        """generate_content - テキスト以外のブロックを読み飛ばし、最初のテキストを返す"""
        bedrock.return_value.messages.create.return_value = create_response(
            [
                MagicMock(),
                TextBlock(type="text", text="1つ目"),
                TextBlock(type="text", text="2つ目"),
            ]
        )

        summary_text, _, _ = ClaudeAPIClient().generate_content(
            prompt="プロンプト", model_name="test-model"
        )

        assert summary_text == "1つ目"

    @pytest.mark.parametrize("content", [[], [MagicMock()]])
    def test_generate_content_empty_response_raises(self, bedrock, content):
        """generate_content - テキストのない応答は APIError"""
        bedrock.return_value.messages.create.return_value = create_response(content)

        with pytest.raises(APIError) as exc_info:
            ClaudeAPIClient().generate_content(prompt="プロンプト", model_name="test-model")

        assert str(exc_info.value) == MESSAGES["ERROR"]["EMPTY_RESPONSE"]

    def test_generate_content_api_error_propagates(self, bedrock):
        """generate_content - API呼び出しの例外はラップせずに伝播する"""
        bedrock.return_value.messages.create.side_effect = TimeoutError("timed out")

        with pytest.raises(TimeoutError):
            ClaudeAPIClient().generate_content(prompt="プロンプト", model_name="test-model")

    def test_generate_content_special_characters_in_prompt(self, bedrock):
        """generate_content - 特殊文字を含むプロンプトをそのまま送信する"""
        create = bedrock.return_value.messages.create
        create.return_value = create_response([TextBlock(type="text", text="OK")])
        prompt = "患者: 山田<太郎> & \"引用\" \n改行\t タブ 😀"

        ClaudeAPIClient().generate_content(prompt=prompt, model_name="test-model")

        assert create.call_args.kwargs["messages"] == [{"role": "user", "content": prompt}]


class TestClaudeAPIClientGenerateSummary:
    """generate_summary を通した一連の流れのテスト"""

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_generate_summary_flow(self, mock_db_session, mock_get_prompt, bedrock):
        """generate_summary - プロンプトを組み立てて API を呼び出す"""
        mock_db_session.return_value.__enter__.return_value = MagicMock()
        mock_get_prompt.return_value = None
        create = bedrock.return_value.messages.create
        create.return_value = create_response(
            [TextBlock(type="text", text="生成された文書")], input_tokens=2000, output_tokens=1000
        )

        result = ClaudeAPIClient().generate_summary(
            SummaryRequest(medical_text="患者情報", additional_info="追加情報"),
            "claude-3-5-sonnet-20241022",
        )

        assert result == ("生成された文書", 2000, 1000)
        kwargs = create.call_args.kwargs
        assert kwargs["model"] == "claude-3-5-sonnet-20241022"
        assert "患者情報" in kwargs["messages"][0]["content"]
        assert "追加情報" in kwargs["messages"][0]["content"]
