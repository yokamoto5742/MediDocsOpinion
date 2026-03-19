import json
from unittest.mock import MagicMock

from app.utils.error_handlers import api_exception_handler, validation_exception_handler


class TestApiExceptionHandler:
    """api_exception_handler のテスト"""

    async def test_returns_status_500(self):
        """HTTP 500 を返す"""
        request = MagicMock()
        exc = RuntimeError("内部エラー")
        response = await api_exception_handler(request, exc)
        assert response.status_code == 500

    async def test_success_is_false(self):
        """レスポンスの success が False"""
        request = MagicMock()
        exc = RuntimeError("内部エラー")
        response = await api_exception_handler(request, exc)
        body_str = response.body if isinstance(response.body, str) else response.body.decode()  # type: ignore
        body = json.loads(body_str)
        assert body["success"] is False

    async def test_error_message_is_exception_string(self):
        """error_message が例外のメッセージ文字列"""
        request = MagicMock()
        exc = RuntimeError("詳細なエラーメッセージ")
        response = await api_exception_handler(request, exc)
        body_str = response.body if isinstance(response.body, str) else response.body.decode()  # type: ignore
        body = json.loads(body_str)
        assert body["error_message"] == "詳細なエラーメッセージ"


class TestValidationExceptionHandler:
    """validation_exception_handler のテスト"""

    async def test_returns_status_422(self):
        """HTTP 422 を返す"""
        request = MagicMock()
        exc = ValueError("バリデーションエラー")
        response = await validation_exception_handler(request, exc)
        assert response.status_code == 422

    async def test_success_is_false(self):
        """レスポンスの success が False"""
        request = MagicMock()
        exc = ValueError("バリデーションエラー")
        response = await validation_exception_handler(request, exc)
        body_str = response.body if isinstance(response.body, str) else response.body.decode()  # type: ignore
        body = json.loads(body_str)
        assert body["success"] is False

    async def test_error_message_is_exception_string(self):
        """error_message が例外のメッセージ文字列"""
        request = MagicMock()
        exc = ValueError("フィールドが不正です")
        response = await validation_exception_handler(request, exc)
        body_str = response.body if isinstance(response.body, str) else response.body.decode()  # type: ignore
        body = json.loads(body_str)
        assert body["error_message"] == "フィールドが不正です"
