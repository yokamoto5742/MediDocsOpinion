import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.constants import MESSAGES

logger = logging.getLogger(__name__)


async def api_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # 例外詳細はサーバーログのみに記録し、クライアントには定型メッセージを返す
    logger.error("未処理の例外: %s", type(exc).__name__, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error_message": MESSAGES["ERROR"]["GENERIC_ERROR"]},
    )


async def validation_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.warning("リクエスト検証エラー: %s", type(exc).__name__)
    return JSONResponse(
        status_code=422,
        content={"success": False, "error_message": MESSAGES["ERROR"]["INPUT_ERROR"]},
    )
