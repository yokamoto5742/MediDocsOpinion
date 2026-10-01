import json
from typing import Any

from google import genai
from google.genai import interactions
from google.oauth2 import service_account

from app.core.config import get_settings
from app.core.constants import MESSAGES
from app.external.base_api import BaseAPIClient
from app.utils.exceptions import APIError


class GeminiAPIClient(BaseAPIClient):
    """Gemini (Vertex AI) API クライアント"""

    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.google_project_id:
            raise APIError(MESSAGES["CONFIG"]["VERTEX_AI_PROJECT_MISSING"])

        # 認証情報JSONが未設定の場合は実行環境の既定の認証情報を使う
        credentials = None
        if self.settings.google_credentials_json:
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(self.settings.google_credentials_json),
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )

        self.client = genai.Client(
            vertexai=True,
            project=self.settings.google_project_id,
            location=self.settings.google_location,
            credentials=credentials,
        )

    def _thinking_level(self) -> str:
        return "low" if self.settings.gemini_thinking_level == "LOW" else "high"

    def generate_content(
        self, prompt: str, model_name: str, system_prompt: str = ""
    ) -> tuple[str, int, int]:
        request: dict[str, Any] = {
            "model": model_name,
            "input": prompt,
            "generation_config": {"thinking_level": self._thinking_level()},
            # 患者情報を含むためサーバー側に保存しない
            "store": False,
        }
        if system_prompt:
            request["system_instruction"] = system_prompt

        interaction = self.client.interactions.create(**request)
        if not isinstance(interaction, interactions.Interaction):
            raise APIError(MESSAGES["ERROR"]["GEMINI_UNEXPECTED_RESPONSE"])

        input_tokens, output_tokens = _token_counts(interaction.usage)
        return interaction.output_text or "", input_tokens, output_tokens


def _token_counts(usage: interactions.Usage | None) -> tuple[int, int]:
    """(入力トークン数, 出力トークン数) を返す"""
    if usage is None:
        return 0, 0
    return usage.total_input_tokens or 0, usage.total_output_tokens or 0
