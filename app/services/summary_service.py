import time
from typing import AsyncGenerator

from app.core.config import get_settings
from app.core.constants import MESSAGES, get_message
from app.external.api_factory import generate_summary_with_provider, generate_summary_stream_with_provider
from app.schemas.summary import SummaryResponse
from app.services.model_selector import determine_model, get_provider_and_model
from app.services.sse_helpers import sse_event, stream_with_heartbeat
from app.services.usage_service import save_usage
from app.utils.audit_logger import log_audit_event
from app.utils.input_sanitizer import sanitize_medical_text, validate_medical_input
from app.utils.text_processor import format_output_summary, parse_output_summary

settings = get_settings()


def _error_response(
        error_msg: str,
        model: str,
        model_switched: bool = False
) -> SummaryResponse:
    return SummaryResponse(
        success=False,
        output_summary="",
        parsed_summary={},
        input_tokens=0,
        output_tokens=0,
        processing_time=0,
        model_used=model,
        model_switched=model_switched,
        error_message=error_msg,
    )


def validate_input(medical_text: str) -> tuple[bool, str | None]:
    """テキスト入力検証（長さチェックとプロンプトインジェクション検出）"""
    if not medical_text or not medical_text.strip():
        return False, MESSAGES["VALIDATION"]["NO_INPUT"]

    input_length = len(medical_text.strip())
    if input_length < settings.min_input_tokens:
        return False, MESSAGES["VALIDATION"]["INPUT_TOO_SHORT"]
    if input_length > settings.max_input_tokens:
        return False, MESSAGES["VALIDATION"]["INPUT_TOO_LONG"]

    # プロンプトインジェクション検出
    is_valid, error_msg = validate_medical_input(medical_text, settings.max_input_tokens)
    if not is_valid:
        return False, error_msg

    return True, None


def execute_summary_generation(
    medical_text: str,
    additional_info: str,
    referral_purpose: str,
    current_prescription: str,
    department: str,
    doctor: str,
    document_type: str,
    model: str,
    model_explicitly_selected: bool = False,
    user_ip: str | None = None,
) -> SummaryResponse:
    """文書生成を実行"""
    # 監査ログ: 開始
    log_audit_event(
        event_type=get_message("AUDIT", "DOCUMENT_GENERATION_START"),
        user_ip=user_ip,
        document_type=document_type,
        model=model,
        department=department,
        doctor=doctor,
    )

    # サニタイゼーション適用
    medical_text = sanitize_medical_text(medical_text)
    additional_info = sanitize_medical_text(additional_info or "")
    referral_purpose = sanitize_medical_text(referral_purpose)
    current_prescription = sanitize_medical_text(current_prescription or "")

    # 入力検証
    is_valid, error_msg = validate_input(medical_text)
    if not is_valid:
        log_audit_event(
            event_type=get_message("AUDIT", "DOCUMENT_GENERATION_FAILURE"),
            user_ip=user_ip,
            document_type=document_type,
            model=model,
            success=False,
            error_message=error_msg or MESSAGES["ERROR"]["INPUT_ERROR"],
        )
        return _error_response(error_msg or MESSAGES["ERROR"]["INPUT_ERROR"], model)

    # モデル決定
    total_length = len(medical_text) + len(additional_info or "")
    try:
        final_model, model_switched = determine_model(
            model, total_length, department, document_type, doctor, model_explicitly_selected
        )
    except ValueError as e:
        log_audit_event(
            event_type=get_message("AUDIT", "DOCUMENT_GENERATION_FAILURE"),
            user_ip=user_ip,
            document_type=document_type,
            model=model,
            success=False,
            error_message=str(e),
        )
        return _error_response(str(e), model)

    # プロバイダーとモデル名を取得
    try:
        provider, model_name = get_provider_and_model(final_model)
    except ValueError as e:
        log_audit_event(
            event_type=get_message("AUDIT", "DOCUMENT_GENERATION_FAILURE"),
            user_ip=user_ip,
            document_type=document_type,
            model=final_model,
            success=False,
            error_message=str(e),
        )
        return _error_response(str(e), final_model, model_switched)

    start_time = time.time()
    try:
        output_summary, input_tokens, output_tokens = generate_summary_with_provider(
            provider=provider,
            medical_text=medical_text,
            additional_info=additional_info,
            referral_purpose=referral_purpose,
            current_prescription=current_prescription,
            department=department,
            document_type=document_type,
            doctor=doctor,
            model_name=model_name,
        )
    except Exception as e:
        log_audit_event(
            event_type=get_message("AUDIT", "DOCUMENT_GENERATION_FAILURE"),
            user_ip=user_ip,
            document_type=document_type,
            model=final_model,
            success=False,
            error_message=str(e),
        )
        return _error_response(str(e), final_model, model_switched)

    processing_time = time.time() - start_time

    formatted_summary = format_output_summary(output_summary)
    parsed_summary = parse_output_summary(formatted_summary)

    save_usage(
        department=department,
        doctor=doctor,
        document_type=document_type,
        model=final_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        processing_time=processing_time,
    )

    log_audit_event(
        event_type=get_message("AUDIT", "DOCUMENT_GENERATION_SUCCESS"),
        user_ip=user_ip,
        document_type=document_type,
        model=final_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        processing_time=processing_time,
    )

    return SummaryResponse(
        success=True,
        output_summary=formatted_summary,
        parsed_summary=parsed_summary,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        processing_time=processing_time,
        model_used=final_model,
        model_switched=model_switched,
    )


def _run_sync_generation(
    provider: str,
    medical_text: str,
    additional_info: str,
    referral_purpose: str,
    current_prescription: str,
    department: str,
    document_type: str,
    doctor: str,
    model_name: str,
) -> tuple[str, int, int]:
    """同期ストリーミングジェネレータをスレッドプールで実行"""
    stream = generate_summary_stream_with_provider(
        provider=provider,
        medical_text=medical_text,
        additional_info=additional_info,
        referral_purpose=referral_purpose,
        current_prescription=current_prescription,
        department=department,
        document_type=document_type,
        doctor=doctor,
        model_name=model_name,
    )
    chunks = []
    metadata = {}
    for item in stream:
        if isinstance(item, dict):
            metadata = item
        else:
            chunks.append(item)
    return "".join(chunks), metadata.get("input_tokens", 0), metadata.get("output_tokens", 0)


async def execute_summary_generation_stream(
    medical_text: str,
    additional_info: str,
    referral_purpose: str,
    current_prescription: str,
    department: str,
    doctor: str,
    document_type: str,
    model: str,
    model_explicitly_selected: bool = False,
    user_ip: str | None = None,
) -> AsyncGenerator[str, None]:
    """SSEストリーミングで文書生成を実行"""
    # 監査ログ: 開始
    log_audit_event(
        event_type=get_message("AUDIT", "DOCUMENT_GENERATION_START"),
        user_ip=user_ip,
        document_type=document_type,
        model=model,
        department=department,
        doctor=doctor,
    )

    # サニタイゼーション適用
    medical_text = sanitize_medical_text(medical_text)
    additional_info = sanitize_medical_text(additional_info or "")
    referral_purpose = sanitize_medical_text(referral_purpose)
    current_prescription = sanitize_medical_text(current_prescription or "")

    # 入力検証
    is_valid, error_msg = validate_input(medical_text)
    if not is_valid:
        log_audit_event(
            event_type=get_message("AUDIT", "DOCUMENT_GENERATION_FAILURE"),
            user_ip=user_ip,
            document_type=document_type,
            model=model,
            success=False,
            error_message=error_msg or MESSAGES["ERROR"]["INPUT_ERROR"],
        )
        yield sse_event("error", {
            "success": False,
            "error_message": error_msg or MESSAGES["ERROR"]["INPUT_ERROR"]
        })
        return

    # モデル決定
    total_length = len(medical_text) + len(additional_info or "")
    try:
        final_model, model_switched = determine_model(
            model, total_length, department, document_type,
            doctor, model_explicitly_selected
        )
    except ValueError as e:
        log_audit_event(
            event_type=get_message("AUDIT", "DOCUMENT_GENERATION_FAILURE"),
            user_ip=user_ip,
            document_type=document_type,
            model=model,
            success=False,
            error_message=str(e),
        )
        yield sse_event("error", {"success": False, "error_message": str(e)})
        return

    # プロバイダーとモデル名を取得
    try:
        provider, model_name = get_provider_and_model(final_model)
    except ValueError as e:
        log_audit_event(
            event_type=get_message("AUDIT", "DOCUMENT_GENERATION_FAILURE"),
            user_ip=user_ip,
            document_type=document_type,
            model=final_model,
            success=False,
            error_message=str(e),
        )
        yield sse_event("error", {"success": False, "error_message": str(e)})
        return

    start_time = time.time()

    async for item in stream_with_heartbeat(
        sync_func=_run_sync_generation,
        sync_func_args=(
            provider, medical_text, additional_info, referral_purpose,
            current_prescription, department, document_type, doctor, model_name
        ),
        start_message=MESSAGES["STATUS"]["DOCUMENT_GENERATION_START"],
        running_status="generating",
        running_message=MESSAGES["STATUS"]["DOCUMENT_GENERATING"],
        elapsed_message_template=MESSAGES["STATUS"]["DOCUMENT_GENERATING_ELAPSED"],
    ):
        if isinstance(item, str):
            yield item
        else:
            full_text, input_tokens, output_tokens = item
            processing_time = time.time() - start_time

            formatted_summary = format_output_summary(full_text)
            parsed_summary = parse_output_summary(formatted_summary)

            save_usage(
                department=department, doctor=doctor, document_type=document_type,
                model=final_model, input_tokens=input_tokens,
                output_tokens=output_tokens, processing_time=processing_time,
            )

            # 監査ログ: 成功
            log_audit_event(
                event_type=get_message("AUDIT", "DOCUMENT_GENERATION_SUCCESS"),
                user_ip=user_ip,
                document_type=document_type,
                model=final_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                processing_time=processing_time,
            )

            yield sse_event("complete", {
                "success": True,
                "output_summary": formatted_summary,
                "parsed_summary": parsed_summary,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "processing_time": processing_time,
                "model_used": final_model,
                "model_switched": model_switched,
            })
