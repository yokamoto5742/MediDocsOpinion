import logging
from typing import Tuple

from anthropic import AnthropicBedrock
from anthropic.types import TextBlock

from app.core.config import get_settings
from app.core.constants import MESSAGES
from app.external.base_api import BaseAPIClient
from app.utils.exceptions import APIError

logger = logging.getLogger(__name__)


class ClaudeAPIClient(BaseAPIClient):
    def __init__(self):
        settings = get_settings()
        self.aws_access_key_id = settings.aws_access_key_id
        self.aws_secret_access_key = settings.aws_secret_access_key
        self.aws_region = settings.aws_region
        self.anthropic_model = settings.anthropic_model

        super().__init__(None, self.anthropic_model)
        self.client = None

    def initialize(self) -> bool:
        try:
            self.client = AnthropicBedrock(
                aws_region=self.aws_region,
            )
            return True

        except Exception as e:
            raise APIError(MESSAGES["ERROR"]["BEDROCK_INIT_ERROR"].format(error=str(e)))

    def _generate_content(self, prompt: str, model_name: str) -> Tuple[str, int, int]:
        """
        プロンプトから要約を生成
        Args:
            prompt: 生成用プロンプト
            model_name: 使用するモデル名
        Returns:
            Tuple[str, int, int]: (生成された要約, 入力トークン数, 出力トークン数)
        Raises:
            APIError: API呼び出しに失敗した場合
        """
        try:
            if self.client is None:
                raise APIError(MESSAGES["ERROR"]["CLAUDE_CLIENT_NOT_INITIALIZED"])

            response = self.client.messages.create(
                model=model_name,
                max_tokens=6000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            summary_text = MESSAGES["ERROR"]["EMPTY_RESPONSE"]
            if response.content:
                for content_block in response.content:
                    if isinstance(content_block, TextBlock):
                        summary_text = content_block.text
                        break

            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            return summary_text, input_tokens, output_tokens

        except Exception as e:
            raise APIError(MESSAGES["ERROR"]["BEDROCK_API_ERROR"].format(error=str(e)))
