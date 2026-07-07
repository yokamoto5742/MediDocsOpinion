import logging
import time
from typing import AsyncGenerator, cast

from app.core.config import get_settings
from app.core.constants import (
    EVALUATION_GROUNDING_INSTRUCTION,
    MESSAGES,
    ModelType,
    get_message,
)
from app.core.database import get_db_session
from app.external.api_factory import create_client
from app.schemas.evaluation import EvaluationResponse
from app.services.evaluation_prompt_service import get_evaluation_prompt
from app.services.sse_helpers import sse_event, stream_with_heartbeat
from app.services.usage_service import check_daily_limit
from app.utils.audit_logger import log_audit_event
from app.utils.input_sanitizer import sanitize_medical_text, validate_medical_input

logger = logging.getLogger(__name__)

settings = get_settings()


def _resolve_evaluation_model() -> tuple[str, str | None]:
    """EVALUATION_MODEL からプロバイダーとモデル名を解決"""
    if settings.evaluation_model == ModelType.CLAUDE.value:
        return ModelType.CLAUDE.value, settings.anthropic_model
    return ModelType.GEMINI_PRO.value, settings.gemini_model


def _error_response(error_msg: str, processing_time: float = 0.0) -> EvaluationResponse:
    """エラーレスポンスを生成"""
    return EvaluationResponse(
        success=False,
        evaluation_result="",
        input_tokens=0,
        output_tokens=0,
        processing_time=processing_time,
        error_message=error_msg,
    )


def _validate_and_get_prompt(
    output_summary: str,
    document_type: str,
    input_text: str = "",
) -> tuple[str | None, str | None]:
    """バリデーションを実行してプロンプトを取得（プロンプトインジェクション検出を含む）"""
    if not output_summary:
        return None, MESSAGES["VALIDATION"]["EVALUATION_NO_OUTPUT"]

    # プロンプトインジェクション検出
    if output_summary:
        is_valid, error_msg = validate_medical_input(output_summary)
        if not is_valid:
            return None, error_msg

    if input_text:
        is_valid, error_msg = validate_medical_input(input_text)
        if not is_valid:
            return None, error_msg

    if not settings.evaluation_model:
        return None, MESSAGES["CONFIG"]["EVALUATION_MODEL_MISSING"]

    provider, model_name = _resolve_evaluation_model()
    if not model_name:
        model_error = (
            MESSAGES["CONFIG"]["CLAUDE_MODEL_NOT_SET"]
            if provider == ModelType.CLAUDE.value
            else MESSAGES["CONFIG"]["GEMINI_MODEL_NOT_SET"]
        )
        return None, model_error

    with get_db_session() as db:
        prompt_data = get_evaluation_prompt(db, document_type)
        if not prompt_data:
            return None, MESSAGES["VALIDATION"]["EVALUATION_PROMPT_NOT_SET"].format(
                document_type=document_type
            )
        return cast(str, prompt_data.content), None


def build_evaluation_prompt(
    prompt_template: str,
    input_text: str,
    previous_text: str,
    additional_info: str,
    output_summary: str,
) -> tuple[str, str]:
    """評価用のsystem prompt(指示)とuserメッセージ(データ)を構築"""
    system_prompt = f"{prompt_template}\n\n{EVALUATION_GROUNDING_INSTRUCTION}"
    user_message = f"""<カルテ記載>
{input_text}
</カルテ記載>

<前回の記載>
{previous_text}
</前回の記載>

<追加情報>
{additional_info}
</追加情報>

<生成された出力>
{output_summary}
</生成された出力>"""
    return system_prompt, user_message


def execute_evaluation(
    document_type: str,
    input_text: str,
    previous_text: str,
    additional_info: str,
    output_summary: str,
    user_ip: str | None = None,
) -> EvaluationResponse:
    """出力評価を実行"""
    # 監査ログ: 開始
    log_audit_event(
        event_type=get_message("AUDIT", "EVALUATION_START"),
        user_ip=user_ip,
        document_type=document_type,
    )

    # 日次利用制限チェック
    limit_error = check_daily_limit()
    if limit_error:
        return _error_response(limit_error)

    # サニタイゼーション適用
    input_text = sanitize_medical_text(input_text)
    previous_text = sanitize_medical_text(previous_text or "")
    additional_info = sanitize_medical_text(additional_info or "")
    output_summary = sanitize_medical_text(output_summary)

    prompt_template, error_msg = _validate_and_get_prompt(
        output_summary, document_type, input_text
    )
    if error_msg:
        log_audit_event(
            event_type=get_message("AUDIT", "EVALUATION_FAILURE"),
            user_ip=user_ip,
            document_type=document_type,
            success=False,
            error_message=error_msg,
        )
        return _error_response(error_msg)

    assert prompt_template is not None
    provider, model_name = _resolve_evaluation_model()
    assert model_name is not None

    system_prompt, user_message = build_evaluation_prompt(
        prompt_template, input_text, previous_text, additional_info, output_summary
    )

    start_time = time.time()
    try:
        client = create_client(provider)
        client.initialize()

        evaluation_text, input_tokens, output_tokens = client._generate_content(
            user_message, model_name, system_prompt
        )
        processing_time = time.time() - start_time

        log_audit_event(
            event_type=get_message("AUDIT", "EVALUATION_SUCCESS"),
            user_ip=user_ip,
            document_type=document_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            processing_time=processing_time,
        )

        return EvaluationResponse(
            success=True,
            evaluation_result=evaluation_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            processing_time=processing_time,
        )

    except Exception as e:
        # 例外詳細はサーバーログのみに記録（外部APIの例外文字列に入力断片が含まれる可能性があるため）
        logger.error("評価API呼び出しエラー", exc_info=True)
        log_audit_event(
            event_type=get_message("AUDIT", "EVALUATION_FAILURE"),
            user_ip=user_ip,
            document_type=document_type,
            success=False,
            error_message=type(e).__name__,
        )
        return _error_response(
            MESSAGES["ERROR"]["EVALUATION_ERROR"], time.time() - start_time
        )


def _run_sync_evaluation(
    document_type: str,
    input_text: str,
    previous_text: str,
    additional_info: str,
    output_summary: str,
    prompt_template: str,
) -> tuple[str, int, int]:
    """同期的に評価を実行"""
    system_prompt, user_message = build_evaluation_prompt(
        prompt_template, input_text, previous_text, additional_info, output_summary
    )

    provider, model_name = _resolve_evaluation_model()
    assert model_name is not None
    client = create_client(provider)
    client.initialize()

    evaluation_text, input_tokens, output_tokens = client._generate_content(
        user_message, model_name, system_prompt
    )

    return evaluation_text, input_tokens, output_tokens


async def execute_evaluation_stream(
    document_type: str,
    input_text: str,
    previous_text: str,
    additional_info: str,
    output_summary: str,
    user_ip: str | None = None,
) -> AsyncGenerator[str, None]:
    """SSEストリーミングで評価を実行"""
    # 監査ログ: 開始
    log_audit_event(
        event_type=get_message("AUDIT", "EVALUATION_START"),
        user_ip=user_ip,
        document_type=document_type,
    )

    # 日次利用制限チェック
    limit_error = check_daily_limit()
    if limit_error:
        yield sse_event("error", {"success": False, "error_message": limit_error})
        return

    # サニタイゼーション適用
    input_text = sanitize_medical_text(input_text)
    previous_text = sanitize_medical_text(previous_text or "")
    additional_info = sanitize_medical_text(additional_info or "")
    output_summary = sanitize_medical_text(output_summary)

    prompt_template, error_msg = _validate_and_get_prompt(
        output_summary, document_type, input_text
    )
    if error_msg:
        log_audit_event(
            event_type=get_message("AUDIT", "EVALUATION_FAILURE"),
            user_ip=user_ip,
            document_type=document_type,
            success=False,
            error_message=error_msg,
        )
        yield sse_event("error", {"success": False, "error_message": error_msg})
        return

    start_time = time.time()

    async for item in stream_with_heartbeat(
        sync_func=_run_sync_evaluation,
        sync_func_args=(
            document_type,
            input_text,
            previous_text,
            additional_info,
            output_summary,
            prompt_template,
        ),
        start_message=MESSAGES["STATUS"]["EVALUATION_START"],
        running_status="evaluating",
        running_message=MESSAGES["STATUS"]["EVALUATING"],
        elapsed_message_template=MESSAGES["STATUS"]["EVALUATING_ELAPSED"],
    ):
        if isinstance(item, str):
            yield item
        else:
            evaluation_text, input_tokens, output_tokens = item
            processing_time = time.time() - start_time

            log_audit_event(
                event_type=get_message("AUDIT", "EVALUATION_SUCCESS"),
                user_ip=user_ip,
                document_type=document_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                processing_time=processing_time,
            )

            yield sse_event(
                "complete",
                {
                    "success": True,
                    "evaluation_result": evaluation_text,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "processing_time": processing_time,
                },
            )
