import json
from typing import Generator, Tuple, Union

from google import genai
from google.genai import types
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

    def _generate_content(self, prompt: str, model_name: str) -> Tuple[str, int, int]:
        try:
            if self.client is None:
                raise APIError(MESSAGES["ERROR"]["GEMINI_CLIENT_NOT_INITIALIZED"])

            thinking_level = (
                types.ThinkingLevel.LOW
                if self.settings.gemini_thinking_level == "LOW"
                else types.ThinkingLevel.HIGH
            )
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_level=thinking_level
                    )
                )
            )

            result_text = ""
            if hasattr(response, 'text') and response.text is not None:
                result_text = str(response.text)
            else:
                result_text = str(response)

            input_tokens = 0
            output_tokens = 0

            if hasattr(response, 'usage_metadata') and response.usage_metadata is not None:
                metadata = response.usage_metadata
                if hasattr(metadata, 'prompt_token_count') and metadata.prompt_token_count is not None:
                    input_tokens = int(metadata.prompt_token_count)
                if hasattr(metadata, 'candidates_token_count') and metadata.candidates_token_count is not None:
                    output_tokens = int(metadata.candidates_token_count)

            return result_text, input_tokens, output_tokens
        except Exception as e:
            raise APIError(MESSAGES["ERROR"]["VERTEX_AI_API_ERROR"].format(error=str(e)))

    def _generate_content_stream(
        self, prompt: str, model_name: str
    ) -> Generator[Union[str, dict], None, None]:
        """ストリーミングでコンテンツを生成"""
        try:
            if self.client is None:
                raise APIError(MESSAGES["ERROR"]["GEMINI_CLIENT_NOT_INITIALIZED"])

            thinking_level = (
                types.ThinkingLevel.LOW
                if self.settings.gemini_thinking_level == "LOW"
                else types.ThinkingLevel.HIGH
            )

            response_stream = self.client.models.generate_content_stream(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_level=thinking_level
                    )
                )
            )

            input_tokens = 0
            output_tokens = 0

            for chunk in response_stream:
                if hasattr(chunk, 'text') and chunk.text:
                    yield chunk.text

                if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                    metadata = chunk.usage_metadata
                    if hasattr(metadata, 'prompt_token_count') and metadata.prompt_token_count:
                        input_tokens = int(metadata.prompt_token_count)
                    if hasattr(metadata, 'candidates_token_count') and metadata.candidates_token_count:
                        output_tokens = int(metadata.candidates_token_count)

            yield {"input_tokens": input_tokens, "output_tokens": output_tokens}

        except Exception as e:
            raise APIError(MESSAGES["ERROR"]["VERTEX_AI_API_ERROR"].format(error=str(e)))
