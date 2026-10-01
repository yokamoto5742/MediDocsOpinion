from app.core.config import get_settings
from app.core.constants import MESSAGES, ModelType, get_message
from app.core.database import get_db_session
from app.services.prompt_service import get_selected_model

settings = get_settings()


def get_available_models() -> list[str]:
    """モデル名が設定済みで利用可能なモデル一覧を取得"""
    models = []
    if settings.anthropic_model:
        models.append(ModelType.CLAUDE.value)
    if settings.gemini_model:
        models.append(ModelType.GEMINI.value)
    return models


def determine_model(
    requested_model: str,
    input_length: int,
    department: str,
    document_type: str,
    doctor: str,
    model_explicitly_selected: bool = False,
) -> tuple[str, bool]:
    """モデル自動切替判定"""
    if not model_explicitly_selected:
        try:
            with get_db_session() as db:
                selected = get_selected_model(db, department, document_type, doctor)
                if selected is not None:
                    requested_model = selected
        except Exception:
            # プロンプト取得に失敗しても処理を続行
            pass

    # 入力長による自動切替
    if (
        input_length > settings.max_token_threshold
        and requested_model == ModelType.CLAUDE
    ):
        if settings.gemini_model:
            return ModelType.GEMINI, True
        else:
            raise ValueError(MESSAGES["CONFIG"]["THRESHOLD_EXCEEDED_NO_GEMINI"])

    return requested_model, False


def get_provider_and_model(selected_model: str) -> tuple[ModelType, str]:
    """選択されたモデルからクライアント種別と実際のモデル名を取得"""
    if selected_model == ModelType.CLAUDE:
        model = settings.anthropic_model
        if not model:
            raise ValueError(MESSAGES["CONFIG"]["CLAUDE_MODEL_NOT_SET"])
        return ModelType.CLAUDE, model
    elif selected_model == ModelType.GEMINI:
        model = settings.gemini_model
        if not model:
            raise ValueError(MESSAGES["CONFIG"]["GEMINI_MODEL_NOT_SET"])
        return ModelType.GEMINI, model
    else:
        raise ValueError(
            get_message("CONFIG", "UNSUPPORTED_MODEL", model=selected_model)
        )
