import hashlib
import hmac
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings, get_settings
from app.core.constants import MESSAGES


CSRF_TOKEN_HEADER = APIKeyHeader(name="X-CSRF-Token", auto_error=False)


def _sign(timestamp: int, settings: Settings) -> str:
    """タイムスタンプに対するHMAC署名を計算"""
    return hmac.new(
        settings.csrf_secret_key.encode(), str(timestamp).encode(), hashlib.sha256
    ).hexdigest()


def generate_csrf_token(settings: Settings) -> str:
    """CSRFトークンを生成"""
    timestamp = int(time.time())
    return f"{timestamp}.{_sign(timestamp, settings)}"


def verify_csrf_token(token: str, settings: Settings) -> bool:
    """CSRFトークンを検証"""
    try:
        timestamp_str, signature = token.split(".", 1)
        timestamp = int(timestamp_str)
    except (ValueError, AttributeError):
        return False

    # 有効期限チェック
    current_time = int(time.time())
    expire_seconds = settings.csrf_token_expire_minutes * 60
    if current_time - timestamp > expire_seconds:
        return False

    # 署名検証（タイミング攻撃を避けるため定数時間で比較）
    return hmac.compare_digest(signature, _sign(timestamp, settings))


async def require_csrf_token(
    csrf_token: str | None = Depends(CSRF_TOKEN_HEADER),
    settings: Settings = Depends(get_settings),
) -> str:
    """
    CSRFトークンを検証する依存関数

    UI経由のリクエストのみ許可して外部APIクライアントを遮断
    """
    if csrf_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=MESSAGES["ERROR"]["CSRF_TOKEN_REQUIRED"],
            headers={"WWW-Authenticate": "CSRF-Token"},
        )

    if not verify_csrf_token(csrf_token, settings):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=MESSAGES["ERROR"]["CSRF_TOKEN_INVALID"],
        )

    return csrf_token


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """セキュリティヘッダーをレスポンスに追加"""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # MIMEスニッフィング防止
        response.headers["X-Content-Type-Options"] = "nosniff"

        # クリックジャッキング防止
        response.headers["X-Frame-Options"] = "DENY"

        # XSS保護
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HSTS（HTTPS環境のみ）
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # CSP設定
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        return response
