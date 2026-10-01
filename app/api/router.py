from fastapi import APIRouter, Depends

from app.api import evaluation, prompts, settings, statistics, summary
from app.core.security import require_csrf_token

# 公開ルーター(読み取り専用、CSRF保護なし)
public_router = APIRouter()
public_router.include_router(settings.router)  # GET: departments, doctors, document_types
public_router.include_router(statistics.router)  # GET: summary, aggregated, records
public_router.include_router(prompts.public_router)  # GET: list_prompts, get_prompt
public_router.include_router(evaluation.public_router)  # GET: get_all_evaluation_prompts, get_evaluation_prompt
public_router.include_router(summary.public_router)  # GET: list_available_models

# CSRF保護ありのルーター(CSRFトークン検証によりUI経由の操作のみ許可)
csrf_router = APIRouter(dependencies=[Depends(require_csrf_token)])
csrf_router.include_router(prompts.router)  # POST/DELETE: create_prompt, delete_prompt
csrf_router.include_router(summary.router)  # POST: generate-stream
csrf_router.include_router(evaluation.router)  # POST/DELETE: evaluate-stream, 評価プロンプトの保存・削除

# 統合ルーター
api_router = APIRouter()
api_router.include_router(public_router)
api_router.include_router(csrf_router)
