import json
from unittest.mock import MagicMock

from app.core.constants import MESSAGES
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
        body_str = (
            response.body if isinstance(response.body, str) else response.body.decode()
        )  # type: ignore
        body = json.loads(body_str)
        assert body["success"] is False

    async def test_error_message_is_generic(self):
        """error_message が定型文で例外詳細を含まない"""
        request = MagicMock()
        exc = RuntimeError("詳細なエラーメッセージ")
        response = await api_exception_handler(request, exc)
        body_str = (
            response.body if isinstance(response.body, str) else response.body.decode()
        )  # type: ignore
        body = json.loads(body_str)
        assert body["error_message"] == MESSAGES["ERROR"]["GENERIC_ERROR"]
        # 例外詳細はクライアントに返さない
        assert "詳細なエラーメッセージ" not in body["error_message"]


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
        body_str = (
            response.body if isinstance(response.body, str) else response.body.decode()
        )  # type: ignore
        body = json.loads(body_str)
        assert body["success"] is False

    async def test_error_message_is_generic(self):
        """error_message が定型文で検証失敗値を含まない"""
        request = MagicMock()
        exc = ValueError("フィールドが不正です")
        response = await validation_exception_handler(request, exc)
        body_str = (
            response.body if isinstance(response.body, str) else response.body.decode()
        )  # type: ignore
        body = json.loads(body_str)
        assert body["error_message"] == MESSAGES["ERROR"]["INPUT_ERROR"]
        # 検証に失敗した入力値はクライアントに返さない
        assert "フィールドが不正です" not in body["error_message"]
