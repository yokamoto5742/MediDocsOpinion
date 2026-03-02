from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.constants import get_message
from app.core.database import get_db
from app.schemas.prompt import PromptCreate, PromptListItem, PromptResponse
from app.services import prompt_service
from app.utils.audit_logger import log_audit_event

# 公開ルーター(読み取り専用、CSRF保護なし)
public_router = APIRouter(prefix="/prompts", tags=["prompts"])

# 管理用ルーター(変更操作、CSRF保護あり)
router = APIRouter(prefix="/prompts", tags=["prompts"])


@public_router.get("/", response_model=list[PromptListItem])
def list_prompts(db: Session = Depends(get_db)):
    """プロンプト一覧を取得"""
    prompts = prompt_service.get_all_prompts(db)
    return prompts


@public_router.get("/{prompt_id}", response_model=PromptResponse)
def get_prompt(prompt_id: int, db: Session = Depends(get_db)):
    """単一プロンプトを取得"""
    prompt = prompt_service.get_prompt_by_id(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.post("/", response_model=PromptResponse)
def create_prompt(http_request: Request, prompt: PromptCreate, db: Session = Depends(get_db)):
    """プロンプトを作成または更新"""
    user_ip = http_request.client.host if http_request.client else None
    existing = prompt_service.get_prompt(
        db, prompt.department, prompt.document_type, prompt.doctor
    )
    is_update = existing is not None

    result = prompt_service.create_or_update_prompt(
        db,
        department=prompt.department,
        document_type=prompt.document_type,
        doctor=prompt.doctor,
        content=prompt.content,
        selected_model=prompt.selected_model,
    )
    db.commit()
    db.refresh(result)

    log_audit_event(
        event_type=get_message("AUDIT", "PROMPT_UPDATED" if is_update else "PROMPT_CREATED"),
        user_ip=user_ip,
        document_type=prompt.document_type,
        department=prompt.department,
        doctor=prompt.doctor,
        prompt_id=result.id,
    )

    return result


@router.delete("/{prompt_id}")
def delete_prompt(http_request: Request, prompt_id: int, db: Session = Depends(get_db)):
    """プロンプトを削除"""
    user_ip = http_request.client.host if http_request.client else None
    if not prompt_service.delete_prompt(db, prompt_id):
        raise HTTPException(status_code=404, detail="Prompt not found")
    db.commit()

    log_audit_event(
        event_type=get_message("AUDIT", "PROMPT_DELETED"),
        user_ip=user_ip,
        prompt_id=prompt_id,
    )

    return {"status": "deleted"}
