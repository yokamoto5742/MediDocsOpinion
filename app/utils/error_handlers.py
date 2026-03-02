from fastapi import Request
from fastapi.responses import JSONResponse


async def api_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"success": False, "error_message": str(exc)},
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"success": False, "error_message": str(exc)},
    )
