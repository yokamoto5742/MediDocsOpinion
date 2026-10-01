import json
from abc import ABC, abstractmethod

from app.core.constants import (
    DEFAULT_SUMMARY_PROMPT,
    GROUNDING_INSTRUCTION,
    KARTE_JSON_INSTRUCTION,
    REFINEMENT_INSTRUCTION,
)
from app.core.database import get_db_session
from app.schemas.summary import SummaryRequest
from app.services.prompt_service import get_prompt


def _is_json_text(text: str) -> bool:
    """テキストがJSON(オブジェクトまたは配列)としてパース可能か判定"""
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return False
    return isinstance(parsed, (dict, list))


class BaseAPIClient(ABC):
    @abstractmethod
    def generate_content(
        self, prompt: str, model_name: str, system_prompt: str = ""
    ) -> tuple[str, int, int]:
        """
        プロンプトから文章を生成
        Args:
            prompt: userメッセージ(カルテ等のデータ)
            model_name: 使用モデル名
            system_prompt: system prompt(指示)
        Returns:
            (生成された文章, 入力トークン数, 出力トークン数)
        """
        pass

    def create_summary_prompt(self, request: SummaryRequest) -> tuple[str, str]:
        """system prompt(指示)とuserメッセージ(データ)を生成"""
        # プロンプト取得に失敗しても、既定のプロンプトで生成を続行する
        try:
            with get_db_session() as db:
                prompt_data = get_prompt(
                    db, request.department, request.document_type, request.doctor
                )
                prompt_template = (
                    prompt_data.content if prompt_data else DEFAULT_SUMMARY_PROMPT
                )
        except Exception:
            prompt_template = DEFAULT_SUMMARY_PROMPT

        system_prompt = f"{prompt_template}\n\n{GROUNDING_INSTRUCTION}"
        if _is_json_text(request.medical_text):
            system_prompt += f"\n\n{KARTE_JSON_INSTRUCTION}"

        user_message = f"<カルテ情報>\n{request.medical_text}\n</カルテ情報>"

        if request.previous_text.strip():
            user_message += f"\n\n<前回の記載>\n{request.previous_text}\n</前回の記載>"

        if request.additional_info.strip():
            user_message += f"\n\n<追加情報>\n{request.additional_info}\n</追加情報>"

        # 評価の指摘を反映した再生成（両方指定時のみ有効）
        if request.previous_summary.strip() and request.evaluation_feedback.strip():
            system_prompt += f"\n\n{REFINEMENT_INSTRUCTION}"
            user_message += (
                f"\n\n<前回の生成結果>\n{request.previous_summary}\n</前回の生成結果>"
                f"\n\n<評価結果>\n{request.evaluation_feedback}\n</評価結果>"
            )

        return system_prompt, user_message

    def generate_summary(
        self, request: SummaryRequest, model_name: str
    ) -> tuple[str, int, int]:
        """リクエスト内容から文書を生成"""
        system_prompt, user_message = self.create_summary_prompt(request)
        return self.generate_content(user_message, model_name, system_prompt)
