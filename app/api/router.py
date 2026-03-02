from fastapi import APIRouter, Depends

from app.api import evaluation, prompts, settings, statistics, summary
from app.core.security import require_csrf_token

# 公開ルーター(読み取り専用、CSRF保護なし)
public_router = APIRouter()
public_router.include_router(settings.router)  # GET: departments, doctors, document_types
public_router.include_router(statistics.router)  # GET: summary, aggregated, records
public_router.include_router(prompts.public_router)  # GET: list_prompts, get_prompt
public_router.include_router(evaluation.public_router)  # GET: get_all_evaluation_prompts, get_evaluation_prompt
public_router.include_router(summary.public_router)  # GET: get_available_models

# 管理用ルーター(変更操作、CSRF保護あり)
admin_router = APIRouter(dependencies=[Depends(require_csrf_token)])
admin_router.include_router(prompts.router)  # POST/DELETE: create_prompt, delete_prompt
admin_router.include_router(evaluation.router)  # POST/DELETE: save_evaluation_prompt, delete_evaluation_prompt

# 保護されたAPIルーター(認証必須)
protected_api_router = APIRouter(dependencies=[Depends(require_csrf_token)])
protected_api_router.include_router(summary.protected_router)  # /generate エンドポイント
protected_api_router.include_router(evaluation.protected_router)  # /evaluate エンドポイント

# 統合ルーター
api_router = APIRouter()
api_router.include_router(public_router)
api_router.include_router(admin_router)
api_router.include_router(protected_api_router)
