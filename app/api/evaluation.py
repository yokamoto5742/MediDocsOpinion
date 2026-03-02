from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.constants import get_message
from app.core.database import get_db
from app.schemas.evaluation import (
    EvaluationPromptListResponse,
    EvaluationPromptRequest,
    EvaluationPromptResponse,
    EvaluationPromptSaveResponse,
    EvaluationRequest,
    EvaluationResponse,
)
from app.services import evaluation_prompt_service, evaluation_service
from app.services.evaluation_service import execute_evaluation_stream
from app.utils.audit_logger import log_audit_event

# 公開ルーター(読み取り専用、CSRF保護なし)
public_router = APIRouter(prefix="/evaluation", tags=["evaluation"])

# 管理用ルーター(変更操作、CSRF保護あり)
router = APIRouter(prefix="/evaluation", tags=["evaluation"])

# 保護されたAPIルーター(認証必須)
protected_router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@protected_router.post("/evaluate", response_model=EvaluationResponse)
def evaluate_output(http_request: Request, request: EvaluationRequest):
    """出力評価API"""
    user_ip = http_request.client.host if http_request.client else None
    return evaluation_service.execute_evaluation(
        document_type=request.document_type,
        input_text=request.input_text,
        current_prescription=request.current_prescription,
        additional_info=request.additional_info,
        output_summary=request.output_summary,
        user_ip=user_ip,
    )


@protected_router.post("/evaluate-stream")
async def evaluate_output_stream(http_request: Request, request: EvaluationRequest):
    """SSEストリーミング出力評価API"""
    user_ip = http_request.client.host if http_request.client else None
    event_generator = execute_evaluation_stream(
        document_type=request.document_type,
        input_text=request.input_text,
        current_prescription=request.current_prescription,
        additional_info=request.additional_info,
        output_summary=request.output_summary,
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


@public_router.get("/prompts", response_model=EvaluationPromptListResponse)
def get_all_evaluation_prompts(db: Session = Depends(get_db)):
    """全ての評価プロンプトを取得"""
    prompts = evaluation_prompt_service.get_all_evaluation_prompts(db)
    return EvaluationPromptListResponse(
        prompts=[
            EvaluationPromptResponse(
                id=p.id,
                document_type=p.document_type,
                content=p.content,
                is_active=p.is_active,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in prompts
        ]
    )


@public_router.get("/prompts/{document_type}", response_model=EvaluationPromptResponse)
def get_evaluation_prompt(
    document_type: str,
    db: Session = Depends(get_db)
):
    """評価プロンプトを取得"""
    prompt = evaluation_prompt_service.get_evaluation_prompt(db, document_type)
    if prompt:
        return EvaluationPromptResponse(
            id=prompt.id,
            document_type=prompt.document_type,
            content=prompt.content,
            is_active=prompt.is_active,
            created_at=prompt.created_at,
            updated_at=prompt.updated_at,
        )
    return EvaluationPromptResponse(
        document_type=document_type,
        content=None,
        is_active=False,
    )


@router.post("/prompts", response_model=EvaluationPromptSaveResponse)
def save_evaluation_prompt(
    http_request: Request,
    request: EvaluationPromptRequest,
    db: Session = Depends(get_db)
):
    """評価プロンプトを保存"""
    user_ip = http_request.client.host if http_request.client else None
    success, message = evaluation_prompt_service.create_or_update_evaluation_prompt(
        db, request.document_type, request.content
    )
    if success:
        db.commit()
        log_audit_event(
            event_type=get_message("AUDIT", "EVALUATION_PROMPT_SAVED"),
            user_ip=user_ip,
            document_type=request.document_type,
        )
    return EvaluationPromptSaveResponse(
        success=success,
        message=message,
        document_type=request.document_type,
    )


@router.delete("/prompts/{document_type}", response_model=EvaluationPromptSaveResponse)
def delete_evaluation_prompt(
    http_request: Request,
    document_type: str,
    db: Session = Depends(get_db)
):
    """評価プロンプトを削除"""
    user_ip = http_request.client.host if http_request.client else None
    success, message = evaluation_prompt_service.delete_evaluation_prompt(db, document_type)
    if success:
        db.commit()
        log_audit_event(
            event_type=get_message("AUDIT", "EVALUATION_PROMPT_DELETED"),
            user_ip=user_ip,
            document_type=document_type,
        )
    return EvaluationPromptSaveResponse(
        success=success,
        message=message,
        document_type=document_type,
    )
