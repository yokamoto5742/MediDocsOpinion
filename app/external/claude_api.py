from anthropic import AnthropicBedrock, omit  # type: ignore[attr-defined]
from anthropic.types import TextBlock

from app.core.config import get_settings
from app.core.constants import CLAUDE_GENERATION_TEMPERATURE, MESSAGES
from app.external.base_api import BaseAPIClient
from app.utils.exceptions import APIError


class ClaudeAPIClient(BaseAPIClient):
    """Claude (Amazon Bedrock) API クライアント"""

    def __init__(self) -> None:
        self.client = AnthropicBedrock(aws_region=get_settings().aws_region)

    def generate_content(
        self, prompt: str, model_name: str, system_prompt: str = ""
    ) -> tuple[str, int, int]:
        response = self.client.messages.create(
            model=model_name,
            max_tokens=6000,
            system=system_prompt or omit,
            messages=[{"role": "user", "content": prompt}],
            # anthropic SDK 1.x で temperature 引数が削除されたため extra_body で送信する
            extra_body={"temperature": CLAUDE_GENERATION_TEMPERATURE},
        )

        summary_text = next(
            (block.text for block in response.content if isinstance(block, TextBlock)),
            None,
        )
        # 空の応答を生成結果として扱わない（利用量も保存しない）
        if summary_text is None:
            raise APIError(MESSAGES["ERROR"]["EMPTY_RESPONSE"])

        # max_tokens到達で途中終了した場合はユーザーに分かるよう警告を付加
        if response.stop_reason == "max_tokens":
            summary_text += "\n\n" + MESSAGES["WARNING"]["OUTPUT_TRUNCATED"]

        return summary_text, response.usage.input_tokens, response.usage.output_tokens
