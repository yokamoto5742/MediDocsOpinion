import json
from abc import ABC, abstractmethod
from typing import Generator, Optional, Tuple, Union

from app.core.constants import (
    DEFAULT_DOCUMENT_TYPE,
    DEFAULT_SUMMARY_PROMPT,
    GROUNDING_INSTRUCTION,
    KARTE_JSON_INSTRUCTION,
    MESSAGES,
    REFINEMENT_INSTRUCTION,
)
from app.core.database import get_db_session
from app.services.prompt_service import get_prompt, get_selected_model
from app.utils.exceptions import APIError


def _is_json_text(text: str) -> bool:
    """テキストがJSON(オブジェクトまたは配列)としてパース可能か判定"""
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return False
    return isinstance(parsed, (dict, list))


class BaseAPIClient(ABC):
    def __init__(self, api_key: str | None, default_model: str | None):
        self.api_key: str | None = api_key
        self.default_model: str | None = default_model

    @abstractmethod
    def initialize(self) -> bool:
        """APIクライアントを初期化"""
        pass

    @abstractmethod
    def _generate_content(
        self, prompt: str, model_name: str, system_prompt: str | None = None
    ) -> Tuple[str, int, int]:
        """
        プロンプトから要約を生成
        Args:
            prompt: userメッセージ(カルテ等のデータ)
            model_name: 使用モデル名
            system_prompt: system prompt(指示)
        Returns:
            Tuple[str, int, int]: (生成された要約, 入力トークン数, 出力トークン数)
        Raises:
            APIError: API呼び出しに失敗した場合
        """
        pass

    def create_summary_prompt(
        self,
        medical_text: str,
        additional_info: str = "",
        previous_text: str = "",
        department: str = "default",
        document_type: str = DEFAULT_DOCUMENT_TYPE,
        doctor: str = "default",
        previous_summary: str = "",
        evaluation_feedback: str = "",
    ) -> Tuple[str, str]:
        """system prompt(指示)とuserメッセージ(データ)を生成"""
        try:
            with get_db_session() as db:
                prompt_data = get_prompt(db, department, document_type, doctor)
                if prompt_data:
                    prompt_template = prompt_data.content
                else:
                    prompt_template = DEFAULT_SUMMARY_PROMPT
        except Exception:
            prompt_template = DEFAULT_SUMMARY_PROMPT

        system_prompt = f"{prompt_template}\n\n{GROUNDING_INSTRUCTION}"
        if _is_json_text(medical_text):
            system_prompt += f"\n\n{KARTE_JSON_INSTRUCTION}"

        user_message = f"<カルテ情報>\n{medical_text}\n</カルテ情報>"

        if previous_text.strip():
            user_message += f"\n\n<前回の記載>\n{previous_text}\n</前回の記載>"

        if additional_info.strip():
            user_message += f"\n\n<追加情報>\n{additional_info}\n</追加情報>"

        # 評価の指摘を反映した再生成（両方指定時のみ有効）
        if previous_summary.strip() and evaluation_feedback.strip():
            system_prompt += f"\n\n{REFINEMENT_INSTRUCTION}"
            user_message += (
                f"\n\n<前回の生成結果>\n{previous_summary}\n</前回の生成結果>"
                f"\n\n<評価結果>\n{evaluation_feedback}\n</評価結果>"
            )

        return system_prompt, user_message

    def get_model_name(
        self,
        department: str,
        document_type: str,
        doctor: str
    ) -> str | None:
        """プロンプトから選択されたモデル名を取得"""
        try:
            with get_db_session() as db:
                selected = get_selected_model(db, department, document_type, doctor)
                if selected is not None:
                    return selected
        except Exception:
            pass
        return self.default_model

    def generate_summary(
        self,
        medical_text: str,
        additional_info: str = "",
        previous_text: str = "",
        department: str = "default",
        document_type: str = DEFAULT_DOCUMENT_TYPE,
        doctor: str = "default",
        model_name: Optional[str] = None,
        previous_summary: str = "",
        evaluation_feedback: str = "",
    ) -> Tuple[str, int, int]:
        try:
            self.initialize()

            if not model_name:
                model_name = self.get_model_name(department, document_type, doctor)

            if not model_name:
                raise APIError(MESSAGES["ERROR"]["MODEL_NAME_NOT_SPECIFIED"])

            system_prompt, user_message = self.create_summary_prompt(
                medical_text,
                additional_info,
                previous_text,
                department,
                document_type,
                doctor,
                previous_summary,
                evaluation_feedback,
            )

            return self._generate_content(user_message, model_name, system_prompt)

        except APIError as e:
            raise e
        except Exception as e:
            raise APIError(
                f"{self.__class__.__name__}でエラーが発生しました: {str(e)}"
            )

    def _generate_content_stream(
        self, prompt: str, model_name: str, system_prompt: str | None = None
    ) -> Generator[Union[str, dict], None, None]:
        """ストリーミングのデフォルト実装"""
        text, input_tokens, output_tokens = self._generate_content(
            prompt, model_name, system_prompt
        )
        yield text
        yield {"input_tokens": input_tokens, "output_tokens": output_tokens}

    def generate_summary_stream(
        self,
        medical_text: str,
        additional_info: str = "",
        previous_text: str = "",
        department: str = "default",
        document_type: str = DEFAULT_DOCUMENT_TYPE,
        doctor: str = "default",
        model_name: Optional[str] = None,
        previous_summary: str = "",
        evaluation_feedback: str = "",
    ) -> Generator[Union[str, dict], None, None]:
        """ストリーミングで要約を生成"""
        try:
            self.initialize()

            if not model_name:
                model_name = self.get_model_name(department, document_type, doctor)

            if not model_name:
                raise APIError(MESSAGES["ERROR"]["MODEL_NAME_NOT_SPECIFIED"])

            system_prompt, user_message = self.create_summary_prompt(
                medical_text,
                additional_info,
                previous_text,
                department,
                document_type,
                doctor,
                previous_summary,
                evaluation_feedback,
            )

            yield from self._generate_content_stream(
                user_message, model_name, system_prompt
            )

        except APIError:
            raise
        except Exception as e:
            raise APIError(
                f"{self.__class__.__name__}でエラーが発生しました: {str(e)}"
            )
