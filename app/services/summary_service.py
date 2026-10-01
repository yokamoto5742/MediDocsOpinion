import asyncio
import logging
import time
from collections.abc import AsyncGenerator

from app.core.config import get_settings
from app.core.constants import MESSAGES
from app.external.api_factory import create_client
from app.schemas.summary import SummaryRequest
from app.services.model_selector import determine_model, get_provider_and_model
from app.services.sse_helpers import heartbeat_until_done, sse_error, sse_event
from app.services.usage_service import check_daily_limit, save_usage
from app.utils.audit_logger import log_audit_event
from app.utils.input_sanitizer import sanitize_medical_text, validate_medical_input
from app.utils.text_processor import format_output_summary, parse_output_summary

logger = logging.getLogger(__name__)

settings = get_settings()


def validate_input(medical_text: str) -> str | None:
    """
    テキスト入力検証（長さチェックとプロンプトインジェクション検出）

    問題があればエラーメッセージ、なければNoneを返す
    """
    if not medical_text or not medical_text.strip():
        return MESSAGES["VALIDATION"]["NO_INPUT"]

    # min/max_input_tokens は設定名に反してトークン数ではなく文字数で比較している
    input_length = len(medical_text.strip())
    if input_length < settings.min_input_tokens:
        return MESSAGES["VALIDATION"]["INPUT_TOO_SHORT"]
    if input_length > settings.max_input_tokens:
        return MESSAGES["VALIDATION"]["INPUT_TOO_LONG"]

    return validate_medical_input(medical_text)


def _sanitize_request(request: SummaryRequest) -> SummaryRequest:
    """自由入力のテキスト項目をサニタイズしたリクエストを返す"""
    return request.model_copy(
        update={
            "medical_text": sanitize_medical_text(request.medical_text),
            "additional_info": sanitize_medical_text(request.additional_info),
            "previous_text": sanitize_medical_text(request.previous_text),
            "previous_summary": sanitize_medical_text(request.previous_summary),
            "evaluation_feedback": sanitize_medical_text(request.evaluation_feedback),
        }
    )


def _failure_event(
    request: SummaryRequest,
    user_ip: str | None,
    model: str,
    error_message: str,
    audit_message: str | None = None,
) -> str:
    """
    失敗を監査ログに記録し、クライアント向けのエラーイベントを返す

    audit_message を指定すると、監査ログにはそちらを記録する
    （例外文字列に入力断片が含まれる可能性がある場合に例外クラス名だけを残す）
    """
    log_audit_event(
        event_type=MESSAGES["AUDIT"]["DOCUMENT_GENERATION_FAILURE"],
        user_ip=user_ip,
        document_type=request.document_type,
        model=model,
        success=False,
        error_message=audit_message or error_message,
    )
    return sse_error(error_message)


async def execute_summary_generation_stream(
    request: SummaryRequest,
    user_ip: str | None = None,
) -> AsyncGenerator[str]:
    """SSEで進捗を通知しながら文書生成を実行"""
    log_audit_event(
        event_type=MESSAGES["AUDIT"]["DOCUMENT_GENERATION_START"],
        user_ip=user_ip,
        document_type=request.document_type,
        model=request.model,
        department=request.department,
        doctor=request.doctor,
    )

    limit_error = check_daily_limit()
    if limit_error:
        yield sse_error(limit_error)
        return

    request = _sanitize_request(request)

    error_msg = validate_input(request.medical_text)
    if error_msg:
        yield _failure_event(request, user_ip, request.model, error_msg)
        return

    # モデル決定（入力が長い場合は Claude から Gemini へ自動切替）
    final_model = request.model
    try:
        final_model, model_switched = determine_model(
            requested_model=request.model,
            input_length=len(request.medical_text) + len(request.additional_info),
            department=request.department,
            document_type=request.document_type,
            doctor=request.doctor,
            model_explicitly_selected=request.model_explicitly_selected,
        )
        model_type, model_name = get_provider_and_model(final_model)
    except ValueError as e:
        yield _failure_event(request, user_ip, final_model, str(e), type(e).__name__)
        return

    # AI APIの呼び出しは同期処理のためスレッドプールで実行し、完了までハートビートを送る
    start_time = time.time()
    task = asyncio.create_task(
        asyncio.to_thread(
            lambda: create_client(model_type).generate_summary(request, model_name)
        )
    )
    async for event in heartbeat_until_done(
        task,
        start_message=MESSAGES["STATUS"]["DOCUMENT_GENERATION_START"],
        running_status="generating",
        running_message=MESSAGES["STATUS"]["DOCUMENT_GENERATING"],
        elapsed_message_template=MESSAGES["STATUS"]["DOCUMENT_GENERATING_ELAPSED"],
    ):
        yield event

    try:
        output_summary, input_tokens, output_tokens = task.result()
    except Exception as e:
        # 例外詳細はサーバーログのみに記録（外部APIの例外文字列に入力断片が含まれる可能性があるため）
        logger.error("文書生成API呼び出しエラー", exc_info=True)
        yield _failure_event(
            request, user_ip, final_model, MESSAGES["ERROR"]["API_ERROR"], type(e).__name__
        )
        return

    processing_time = time.time() - start_time

    formatted_summary = format_output_summary(output_summary)
    parsed_summary = parse_output_summary(formatted_summary)

    save_usage(
        department=request.department,
        doctor=request.doctor,
        document_type=request.document_type,
        model=final_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        processing_time=processing_time,
    )

    log_audit_event(
        event_type=MESSAGES["AUDIT"]["DOCUMENT_GENERATION_SUCCESS"],
        user_ip=user_ip,
        document_type=request.document_type,
        model=final_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        processing_time=processing_time,
    )

    yield sse_event(
        "complete",
        {
            "success": True,
            "output_summary": formatted_summary,
            "parsed_summary": parsed_summary,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "processing_time": processing_time,
            "model_used": final_model,
            "model_switched": model_switched,
        },
    )
