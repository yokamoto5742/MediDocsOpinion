import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.router import api_router
from app.core.config import get_settings
from app.core.constants import (
    DEFAULT_DEPARTMENT,
    DEFAULT_SECTION_NAMES,
    DOCUMENT_TYPES,
    DOCUMENT_TYPE_TO_PURPOSE_MAPPING,
    FRONTEND_MESSAGES,
    ModelType,
)
from app.core.security import SecurityHeadersMiddleware, generate_csrf_token
from app.utils.error_handlers import api_exception_handler, validation_exception_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:\t%(name)s - %(message)s",
)

settings = get_settings()

app = FastAPI(
    title="MediDocsLM API",
    version="1.0.0",
    docs_url=None, # 開発段階では "/api/docs"
    redoc_url=None,
)

# 明示的なCORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

app.add_middleware(SecurityHeadersMiddleware)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, api_exception_handler)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

app.include_router(api_router, prefix="/api")


def get_available_models() -> list[str]:
    """利用可能なモデル一覧を取得"""
    models = []
    if settings.anthropic_model:
        models.append(ModelType.CLAUDE.value)
    if settings.gemini_model:
        models.append(ModelType.GEMINI_PRO.value)
    return models if models else [ModelType.CLAUDE.value]


def get_common_context(active_page: str = "index") -> dict:
    """共通コンテキストを取得"""
    return {
        "departments": DEFAULT_DEPARTMENT,
        "document_types": DOCUMENT_TYPES,
        "document_purpose_mapping": DOCUMENT_TYPE_TO_PURPOSE_MAPPING,
        "available_models": get_available_models(),
        "tab_names": ["全文"] + list(DEFAULT_SECTION_NAMES),
        "active_page": active_page,
        "csrf_token": generate_csrf_token(settings),
        "messages": FRONTEND_MESSAGES,
        "prompt_management": settings.prompt_management,
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """メインページ"""
    return templates.TemplateResponse(
        request,
        "index.html",
        get_common_context(),
    )


@app.get("/prompts/add", response_class=HTMLResponse)
async def prompts_new_page(request: Request):
    """プロンプト新規作成ページ"""
    return templates.TemplateResponse(
        request,
        "prompts_new.html",
        get_common_context("prompts"),
    )


@app.get("/prompts/edit/{prompt_id}", response_class=HTMLResponse)
async def prompts_edit_page(request: Request, prompt_id: int):
    """プロンプト編集ページ"""
    return templates.TemplateResponse(
        request,
        "prompts_edit.html",
        {"prompt_id": prompt_id, **get_common_context("prompts")},
    )


@app.get("/prompts", response_class=HTMLResponse)
async def prompts_page(request: Request):
    """プロンプト管理ページ"""
    return templates.TemplateResponse(
        request,
        "prompts.html",
        get_common_context("prompts"),
    )


@app.get("/statistics", response_class=HTMLResponse)
async def statistics_page(request: Request):
    """統計情報ページ"""
    return templates.TemplateResponse(
        request,
        "statistics.html",
        get_common_context("statistics"),
    )


@app.get("/evaluation-prompts", response_class=HTMLResponse)
async def evaluation_prompts_page(request: Request):
    """評価プロンプト管理ページ"""
    return templates.TemplateResponse(
        request,
        "evaluation_prompts.html",
        get_common_context("prompts"),
    )


@app.get("/evaluation-prompts/edit/{document_type}", response_class=HTMLResponse)
async def evaluation_prompts_edit_page(request: Request, document_type: str):
    """評価プロンプト編集ページ"""
    return templates.TemplateResponse(
        request,
        "evaluation_prompts_edit.html",
        {"document_type": document_type, **get_common_context("prompts")},
    )


@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy"}
