"""CSRF認証のテスト"""
import asyncio
import time
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.security import (
    generate_csrf_token,
    get_secret_key,
    require_csrf_token,
    verify_csrf_token,
)


class TestGenerateCsrfToken:
    """generate_csrf_token関数のテスト"""

    def test_generate_token_format(self):
        """トークン生成のフォーマット検証"""
        mock_settings = MagicMock()
        mock_settings.csrf_secret_key = "test-secret-key"

        token = generate_csrf_token(mock_settings)

        assert isinstance(token, str)
        assert "." in token
        parts = token.split(".")
        assert len(parts) == 2
        assert parts[0].isdigit()  # タイムスタンプ
        assert len(parts[1]) == 64  # SHA256ハッシュ


class TestVerifyCsrfToken:
    """verify_csrf_token関数のテスト"""

    def test_valid_token(self):
        """有効なトークンで検証成功"""
        mock_settings = MagicMock()
        mock_settings.csrf_secret_key = "test-secret-key"
        mock_settings.csrf_token_expire_minutes = 60

        token = generate_csrf_token(mock_settings)
        assert verify_csrf_token(token, mock_settings) is True

    def test_invalid_signature(self):
        """無効な署名でFalse"""
        mock_settings = MagicMock()
        mock_settings.csrf_secret_key = "test-secret-key"
        mock_settings.csrf_token_expire_minutes = 60

        timestamp = int(time.time())
        invalid_token = f"{timestamp}.invalid_signature"

        assert verify_csrf_token(invalid_token, mock_settings) is False

    def test_expired_token(self):
        """期限切れトークンでFalse"""
        mock_settings = MagicMock()
        mock_settings.csrf_secret_key = "test-secret-key"
        mock_settings.csrf_token_expire_minutes = 0  # 即座に期限切れ

        token = generate_csrf_token(mock_settings)
        time.sleep(1)  # 1秒待機

        assert verify_csrf_token(token, mock_settings) is False

    def test_malformed_token(self):
        """不正なフォーマットのトークンでFalse"""
        mock_settings = MagicMock()
        mock_settings.csrf_secret_key = "test-secret-key"
        mock_settings.csrf_token_expire_minutes = 60

        assert verify_csrf_token("invalid-token", mock_settings) is False
        assert verify_csrf_token("", mock_settings) is False
        assert verify_csrf_token("only-one-part", mock_settings) is False

    def test_different_secret_key(self):
        """異なる秘密鍵で署名検証失敗"""
        mock_settings1 = MagicMock()
        mock_settings1.csrf_secret_key = "secret-key-1"
        mock_settings1.csrf_token_expire_minutes = 60

        mock_settings2 = MagicMock()
        mock_settings2.csrf_secret_key = "secret-key-2"
        mock_settings2.csrf_token_expire_minutes = 60

        token = generate_csrf_token(mock_settings1)
        assert verify_csrf_token(token, mock_settings2) is False


class TestRequireCsrfToken:
    """require_csrf_token依存関数のテスト"""

    def test_valid_token_passes(self):
        """有効なトークンで認証成功"""
        mock_settings = MagicMock()
        mock_settings.csrf_secret_key = "test-secret-key"
        mock_settings.csrf_token_expire_minutes = 60

        token = generate_csrf_token(mock_settings)
        result = asyncio.run(
            require_csrf_token(csrf_token=token, settings=mock_settings)
        )

        assert result == token

    def test_missing_token_raises_401(self):
        """トークン未提供で401エラー"""
        mock_settings = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(require_csrf_token(csrf_token=None, settings=mock_settings))

        assert exc_info.value.status_code == 401
        assert "CSRFトークンが必要です" in exc_info.value.detail

    def test_invalid_token_raises_403(self):
        """無効なトークンで403エラー"""
        mock_settings = MagicMock()
        mock_settings.csrf_secret_key = "test-secret-key"
        mock_settings.csrf_token_expire_minutes = 60

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                require_csrf_token(
                    csrf_token="invalid.token", settings=mock_settings
                )
            )

        assert exc_info.value.status_code == 403
        assert "無効または期限切れのCSRFトークンです" in exc_info.value.detail

    def test_expired_token_raises_403(self):
        """期限切れトークンで403エラー"""
        mock_settings = MagicMock()
        mock_settings.csrf_secret_key = "test-secret-key"
        mock_settings.csrf_token_expire_minutes = 0

        token = generate_csrf_token(mock_settings)
        time.sleep(1)

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                require_csrf_token(csrf_token=token, settings=mock_settings)
            )

        assert exc_info.value.status_code == 403
        assert "無効または期限切れのCSRFトークンです" in exc_info.value.detail


class TestGetSecretKey:
    """get_secret_key関数のテスト"""

    def test_uses_configured_key(self):
        """設定された秘密鍵を使用"""
        mock_settings = MagicMock()
        mock_settings.csrf_secret_key = "test-secret-key"

        key = get_secret_key(mock_settings)
        assert key == b"test-secret-key"

    def test_requires_configured_key(self):
        """csrf_secret_keyが必須であることをテスト"""
        mock_settings = MagicMock()
        mock_settings.csrf_secret_key = "required-secret-key"

        key = get_secret_key(mock_settings)
        assert key == b"required-secret-key"


class TestSecurityHeadersMiddleware:
    """SecurityHeadersMiddleware のテスト"""

    def _make_response(self, url: str = "http://testserver/"):
        """TestClient 経由でレスポンスヘッダーを取得するヘルパー"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.core.security import SecurityHeadersMiddleware

        mini_app = FastAPI()
        mini_app.add_middleware(SecurityHeadersMiddleware)

        @mini_app.get("/")
        def _root():
            return {"ok": True}

        with TestClient(mini_app, base_url=url) as c:
            return c.get("/").headers

    def test_x_content_type_options(self):
        """X-Content-Type-Options: nosniff が設定される"""
        headers = self._make_response()
        assert headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options(self):
        """X-Frame-Options: DENY が設定される"""
        headers = self._make_response()
        assert headers.get("x-frame-options") == "DENY"

    def test_x_xss_protection(self):
        """X-XSS-Protection が設定される"""
        headers = self._make_response()
        assert headers.get("x-xss-protection") == "1; mode=block"

    def test_no_hsts_on_http(self):
        """HTTP アクセス時は HSTS ヘッダーが付かない"""
        headers = self._make_response()
        assert "strict-transport-security" not in headers

    def test_csp_header_present(self):
        """Content-Security-Policy ヘッダーが存在する"""
        headers = self._make_response()
        csp = headers.get("content-security-policy", "")
        assert "default-src 'self'" in csp

    def test_csp_frame_ancestors_none(self):
        """CSP に frame-ancestors 'none' が含まれる"""
        headers = self._make_response()
        csp = headers.get("content-security-policy", "")
        assert "frame-ancestors 'none'" in csp
