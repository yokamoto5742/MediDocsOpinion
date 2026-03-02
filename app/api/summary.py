from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.constants import ModelType
from app.schemas.summary import SummaryRequest, SummaryResponse
from app.services.summary_service import execute_summary_generation, execute_summary_generation_stream

# 公開ルーター(読み取り専用、CSRF保護なし)
public_router = APIRouter(prefix="/summary", tags=["summary"])

# 保護されたAPIルーター(認証必須)
protected_router = APIRouter(prefix="/summary", tags=["summary"])

settings = get_settings()


@protected_router.post("/generate", response_model=SummaryResponse)
def generate_summary(http_request: Request, request: SummaryRequest):
    """文書生成API"""
    user_ip = http_request.client.host if http_request.client else None
    return execute_summary_generation(
        medical_text=request.medical_text,
        additional_info=request.additional_info,
        referral_purpose=request.referral_purpose,
        current_prescription=request.current_prescription,
        department=request.department,
        doctor=request.doctor,
        document_type=request.document_type,
        model=request.model,
        model_explicitly_selected=request.model_explicitly_selected,
        user_ip=user_ip,
    )


@protected_router.post("/generate-stream")
async def generate_summary_stream(http_request: Request, request: SummaryRequest):
    """SSEストリーミング文書生成API"""
    user_ip = http_request.client.host if http_request.client else None
    event_generator = execute_summary_generation_stream(
        medical_text=request.medical_text,
        additional_info=request.additional_info,
        referral_purpose=request.referral_purpose,
        current_prescription=request.current_prescription,
        department=request.department,
        doctor=request.doctor,
        document_type=request.document_type,
        model=request.model,
        model_explicitly_selected=request.model_explicitly_selected,
        user_ip=user_ip,
    )
    return StreamingResponse(
        event_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@public_router.get("/models")
def get_available_models():
    """利用可能なモデル一覧を取得"""
    models = []
    if settings.anthropic_model:
        models.append(ModelType.CLAUDE.value)
    if settings.gemini_model:
        models.append(ModelType.GEMINI_PRO.value)
    return {
        "available_models": models,
        "default_model": models[0] if models else None,
    }
