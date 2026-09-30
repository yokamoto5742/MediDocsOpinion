import json
from typing import Any, Generator, Tuple, Union

from google import genai
from google.genai import interactions
from google.oauth2 import service_account

from app.core.config import get_settings
from app.core.constants import MESSAGES
from app.external.base_api import BaseAPIClient
from app.utils.exceptions import APIError


class GeminiAPIClient(BaseAPIClient):
    """Gemini API クライアント"""

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        model = model_name or settings.gemini_model
        super().__init__(None, model)
        self.client = None
        self.settings = settings

    def initialize(self) -> bool:
        try:
            if not self.settings.google_project_id:
                raise APIError(MESSAGES["CONFIG"]["VERTEX_AI_PROJECT_MISSING"])

            google_credentials_json = self.settings.google_credentials_json

            if google_credentials_json:
                try:
                    credentials_dict = json.loads(google_credentials_json)

                    credentials = service_account.Credentials.from_service_account_info(
                        credentials_dict,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )

                    self.client = genai.Client(
                        vertexai=True,
                        project=self.settings.google_project_id,
                        location=self.settings.google_location,
                        credentials=credentials
                    )

                except json.JSONDecodeError as e:
                    raise APIError(MESSAGES["ERROR"]["VERTEX_AI_CREDENTIALS_JSON_PARSE_ERROR"].format(error=str(e)))
                except KeyError as e:
                    raise APIError(MESSAGES["ERROR"]["VERTEX_AI_CREDENTIALS_FIELD_MISSING"].format(error=str(e)))
                except Exception as e:
                    raise APIError(MESSAGES["ERROR"]["VERTEX_AI_CREDENTIALS_ERROR"].format(error=str(e)))
            else:
                self.client = genai.Client(
                    vertexai=True,
                    project=self.settings.google_project_id,
                    location=self.settings.google_location,
                )

            return True
        except APIError:
            raise
        except Exception as e:
            raise APIError(MESSAGES["ERROR"]["VERTEX_AI_INIT_ERROR"].format(error=str(e)))

    def _thinking_level(self) -> str:
        return "low" if self.settings.gemini_thinking_level == "LOW" else "high"

    def _create_interaction(
        self, prompt: str, model_name: str, system_prompt: str, stream: bool
    ) -> Any:
        if self.client is None:
            raise APIError(MESSAGES["ERROR"]["GEMINI_CLIENT_NOT_INITIALIZED"])

        request: dict[str, Any] = {
            "model": model_name,
            "input": prompt,
            "generation_config": {"thinking_level": self._thinking_level()},
            # 患者情報を含むためサーバー側に保存しない
            "store": False,
        }
        if system_prompt:
            request["system_instruction"] = system_prompt
        if stream:
            request["stream"] = True

        return self.client.interactions.create(**request)

    def _generate_content(
        self, prompt: str, model_name: str, system_prompt: str = ""
    ) -> Tuple[str, int, int]:
        try:
            interaction = self._create_interaction(
                prompt, model_name, system_prompt, stream=False
            )
            if not isinstance(interaction, interactions.Interaction):
                raise APIError(MESSAGES["ERROR"]["GEMINI_UNEXPECTED_RESPONSE"])

            input_tokens, output_tokens = _token_counts(interaction.usage)
            return interaction.output_text or "", input_tokens, output_tokens
        except Exception as e:
            raise APIError(MESSAGES["ERROR"]["VERTEX_AI_API_ERROR"].format(error=str(e)))

    def _generate_content_stream(
        self, prompt: str, model_name: str, system_prompt: str = ""
    ) -> Generator[Union[str, dict], None, None]:
        """ストリーミングでコンテンツを生成"""
        try:
            event_stream = self._create_interaction(
                prompt, model_name, system_prompt, stream=True
            )

            input_tokens = 0
            output_tokens = 0

            for event in event_stream:
                if isinstance(event, interactions.StepDelta):
                    if isinstance(event.delta, interactions.TextDelta) and event.delta.text:
                        yield event.delta.text
                elif isinstance(event, interactions.InteractionCompletedEvent):
                    input_tokens, output_tokens = _token_counts(event.interaction.usage)

            yield {"input_tokens": input_tokens, "output_tokens": output_tokens}

        except Exception as e:
            raise APIError(MESSAGES["ERROR"]["VERTEX_AI_API_ERROR"].format(error=str(e)))


def _token_counts(usage: interactions.Usage | None) -> Tuple[int, int]:
    """(入力トークン数, 出力トークン数) を返す"""
    if usage is None:
        return 0, 0
    return usage.total_input_tokens or 0, usage.total_output_tokens or 0

