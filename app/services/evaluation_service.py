import asyncio
import logging
import time
from collections.abc import AsyncGenerator

from app.core.config import get_settings
from app.core.constants import (
    EVALUATION_GROUNDING_INSTRUCTION,
    MESSAGES,
    ModelType,
    get_message,
)
from app.core.database import get_db_session
from app.external.api_factory import create_client
from app.schemas.evaluation import EvaluationRequest
from app.services.evaluation_prompt_service import get_evaluation_prompt
from app.services.model_selector import get_provider_and_model
from app.services.sse_helpers import heartbeat_until_done, sse_error, sse_event
from app.services.usage_service import check_daily_limit
from app.utils.audit_logger import log_audit_event
from app.utils.input_sanitizer import sanitize_medical_text, validate_medical_input

logger = logging.getLogger(__name__)

settings = get_settings()


def _resolve_evaluation_model() -> tuple[ModelType, str]:
    """EVALUATION_MODEL からクライアント種別とモデル名を解決（未設定・未対応は ValueError）"""
    if not settings.evaluation_model:
        raise ValueError(MESSAGES["CONFIG"]["EVALUATION_MODEL_MISSING"])
    return get_provider_and_model(settings.evaluation_model)


def _validate_evaluation_input(request: EvaluationRequest) -> str | None:
    """
    評価リクエストを検証（プロンプトインジェクション検出を含む）

    問題があればエラーメッセージ、なければNoneを返す
    """
    if not request.output_summary:
        return MESSAGES["VALIDATION"]["EVALUATION_NO_OUTPUT"]
    return validate_medical_input(request.output_summary) or validate_medical_input(
        request.input_text
    )


def _get_prompt_template(document_type: str) -> str | None:
    """文書タイプに対応する評価プロンプトを取得。未設定ならNone"""
    with get_db_session() as db:
        prompt = get_evaluation_prompt(db, document_type)
        return prompt.content if prompt else None


def build_evaluation_prompt(
    prompt_template: str, request: EvaluationRequest
) -> tuple[str, str]:
    """評価用のsystem prompt(指示)とuserメッセージ(データ)を構築"""
    system_prompt = f"{prompt_template}\n\n{EVALUATION_GROUNDING_INSTRUCTION}"
    user_message = f"""<カルテ記載>
{request.input_text}
</カルテ記載>

<前回の記載>
{request.previous_text}
</前回の記載>

<追加情報>
{request.additional_info}
</追加情報>

<生成された出力>
{request.output_summary}
</生成された出力>"""
    return system_prompt, user_message


def _sanitize_request(request: EvaluationRequest) -> EvaluationRequest:
    """自由入力のテキスト項目をサニタイズしたリクエストを返す"""
    return request.model_copy(
        update={
            "input_text": sanitize_medical_text(request.input_text),
            "previous_text": sanitize_medical_text(request.previous_text),
            "additional_info": sanitize_medical_text(request.additional_info),
            "output_summary": sanitize_medical_text(request.output_summary),
        }
    )


def _failure_event(
    request: EvaluationRequest,
    user_ip: str | None,
    error_message: str,
    audit_message: str | None = None,
) -> str:
    """
    失敗を監査ログに記録し、クライアント向けのエラーイベントを返す

    audit_message を指定すると、監査ログにはそちらを記録する
    （例外文字列に入力断片が含まれる可能性がある場合に例外クラス名だけを残す）
    """
    log_audit_event(
        event_type=MESSAGES["AUDIT"]["EVALUATION_FAILURE"],
        user_ip=user_ip,
        document_type=request.document_type,
        success=False,
        error_message=audit_message or error_message,
    )
    return sse_error(error_message)


async def execute_evaluation_stream(
    request: EvaluationRequest,
    user_ip: str | None = None,
) -> AsyncGenerator[str]:
    """SSEで進捗を通知しながら出力評価を実行"""
    log_audit_event(
        event_type=MESSAGES["AUDIT"]["EVALUATION_START"],
        user_ip=user_ip,
        document_type=request.document_type,
    )

    limit_error = check_daily_limit()
    if limit_error:
        yield sse_error(limit_error)
        return

    request = _sanitize_request(request)

    error_msg = _validate_evaluation_input(request)
    if error_msg:
        yield _failure_event(request, user_ip, error_msg)
        return

    try:
        model_type, model_name = _resolve_evaluation_model()
    except ValueError as e:
        yield _failure_event(request, user_ip, str(e))
        return

    prompt_template = _get_prompt_template(request.document_type)
    if prompt_template is None:
        yield _failure_event(
            request,
            user_ip,
            get_message(
                "VALIDATION",
                "EVALUATION_PROMPT_NOT_SET",
                document_type=request.document_type,
            ),
        )
        return

    system_prompt, user_message = build_evaluation_prompt(prompt_template, request)

    # AI APIの呼び出しは同期処理のためスレッドプールで実行し、完了までハートビートを送る
    start_time = time.time()
    task = asyncio.create_task(
        asyncio.to_thread(
            lambda: create_client(model_type).generate_content(
                user_message, model_name, system_prompt
            )
        )
    )
    async for event in heartbeat_until_done(
        task,
        start_message=MESSAGES["STATUS"]["EVALUATION_START"],
        running_status="evaluating",
        running_message=MESSAGES["STATUS"]["EVALUATING"],
        elapsed_message_template=MESSAGES["STATUS"]["EVALUATING_ELAPSED"],
    ):
        yield event

    try:
        evaluation_text, input_tokens, output_tokens = task.result()
    except Exception as e:
        # 例外詳細はサーバーログのみに記録（外部APIの例外文字列に入力断片が含まれる可能性があるため）
        logger.error("評価API呼び出しエラー", exc_info=True)
        yield _failure_event(
            request, user_ip, MESSAGES["ERROR"]["EVALUATION_ERROR"], type(e).__name__
        )
        return

    processing_time = time.time() - start_time

    log_audit_event(
        event_type=MESSAGES["AUDIT"]["EVALUATION_SUCCESS"],
        user_ip=user_ip,
        document_type=request.document_type,
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
