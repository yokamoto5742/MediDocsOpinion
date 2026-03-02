from app.core.config import get_settings
from app.core.constants import MESSAGES, ModelType
from app.core.database import get_db_session
from app.external.api_factory import APIProvider

settings = get_settings()


def determine_model(
    requested_model: str,
    input_length: int,
    department: str,
    document_type: str,
    doctor: str,
    model_explicitly_selected: bool = False
) -> tuple[str, bool]:
    """モデル自動切替判定"""
    if not model_explicitly_selected:
        try:
            from app.services.prompt_service import get_selected_model

            with get_db_session() as db:
                selected = get_selected_model(db, department, document_type, doctor)
                if selected is not None:
                    requested_model = selected
        except Exception:
            # プロンプト取得に失敗しても処理を続行
            pass

    # 入力長による自動切替
    if input_length > settings.max_token_threshold and requested_model == ModelType.CLAUDE:
        if settings.gemini_model:
            return ModelType.GEMINI_PRO, True
        else:
            raise ValueError(MESSAGES["CONFIG"]["THRESHOLD_EXCEEDED_NO_GEMINI"])

    return requested_model, False


def get_provider_and_model(selected_model: str) -> tuple[str, str]:
    """モデル名からプロバイダーとモデル名を取得"""
    if selected_model == ModelType.CLAUDE:
        model = settings.claude_model or settings.anthropic_model
        if not model:
            raise ValueError(MESSAGES["CONFIG"]["CLAUDE_MODEL_NOT_SET"])
        return APIProvider.CLAUDE.value, model
    elif selected_model == ModelType.GEMINI_PRO:
        model = settings.gemini_model
        if not model:
            raise ValueError(MESSAGES["CONFIG"]["GEMINI_MODEL_NOT_SET"])
        return APIProvider.GEMINI.value, model
    else:
        raise ValueError(
            MESSAGES["CONFIG"]["UNSUPPORTED_MODEL"].format(model=selected_model)
        )
