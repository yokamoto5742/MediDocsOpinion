from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_client_ip
from app.core.constants import MESSAGES
from app.core.database import get_db
from app.schemas.evaluation import (
    EvaluationPromptListResponse,
    EvaluationPromptRequest,
    EvaluationPromptResponse,
    EvaluationPromptSaveResponse,
    EvaluationRequest,
)
from app.services import evaluation_prompt_service
from app.services.evaluation_service import execute_evaluation_stream
from app.services.sse_helpers import sse_response
from app.utils.audit_logger import log_audit_event

# 公開ルーター(読み取り専用、CSRF保護なし)
public_router = APIRouter(prefix="/evaluation", tags=["evaluation"])

# CSRF保護ありのルーター(UI経由の操作のみ許可)
router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/evaluate-stream")
async def evaluate_output_stream(
    request: EvaluationRequest, user_ip: str | None = Depends(get_client_ip)
) -> StreamingResponse:
    """SSEストリーミング出力評価API"""
    return sse_response(execute_evaluation_stream(request, user_ip))


@public_router.get("/prompts", response_model=EvaluationPromptListResponse)
def get_all_evaluation_prompts(db: Session = Depends(get_db)):
    """全ての評価プロンプトを取得"""
    return {"prompts": evaluation_prompt_service.get_all_evaluation_prompts(db)}


@public_router.get("/prompts/{document_type}", response_model=EvaluationPromptResponse)
def get_evaluation_prompt(
    document_type: str,
    db: Session = Depends(get_db)
):
    """評価プロンプトを取得"""
    prompt = evaluation_prompt_service.get_evaluation_prompt(db, document_type)
    if prompt:
        return prompt
    # 未設定の文書タイプは空の内容で返す（編集画面の新規作成用）
    return EvaluationPromptResponse(
        document_type=document_type,
        content=None,
        is_active=False,
    )


@router.post("/prompts", response_model=EvaluationPromptSaveResponse)
def save_evaluation_prompt(
    request: EvaluationPromptRequest,
    user_ip: str | None = Depends(get_client_ip),
    db: Session = Depends(get_db)
):
    """評価プロンプトを保存"""
    success, message = evaluation_prompt_service.create_or_update_evaluation_prompt(
        db, request.document_type, request.content
    )
    if success:
        db.commit()
        log_audit_event(
            event_type=MESSAGES["AUDIT"]["EVALUATION_PROMPT_SAVED"],
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
    document_type: str,
    user_ip: str | None = Depends(get_client_ip),
    db: Session = Depends(get_db)
):
    """評価プロンプトを削除"""
    success, message = evaluation_prompt_service.delete_evaluation_prompt(db, document_type)
    if success:
        db.commit()
        log_audit_event(
            event_type=MESSAGES["AUDIT"]["EVALUATION_PROMPT_DELETED"],
            user_ip=user_ip,
            document_type=document_type,
        )
    return EvaluationPromptSaveResponse(
        success=success,
        message=message,
        document_type=document_type,
    )
