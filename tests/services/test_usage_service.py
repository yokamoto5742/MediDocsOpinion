from unittest.mock import MagicMock, patch

import pytest

from app.core.constants import get_message
from app.services.usage_service import DailyUsageSummary, check_daily_limit, get_daily_usage


class TestGetDailyUsage:
    """get_daily_usage 関数のテスト"""

    @patch("app.services.usage_service.get_db_session")
    def test_get_daily_usage_returns_correct_counts(self, mock_get_db_session):
        """DBクエリが正常に返った場合、DailyUsageSummaryが正しい値を持つこと"""
        mock_db = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = (42, 150000, 30000)

        result = get_daily_usage()

        assert isinstance(result, DailyUsageSummary)
        assert result.request_count == 42
        assert result.total_input_tokens == 150000
        assert result.total_output_tokens == 30000

    @patch("app.services.usage_service.get_db_session")
    def test_get_daily_usage_empty_result(self, mock_get_db_session):
        """レコードが0件の場合、すべて0になること（coalesceのNone→0変換）"""
        mock_db = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db
        # coalesceによりNoneは0に変換されるため、DBレイヤーで(0, 0, 0)が返る
        mock_db.query.return_value.filter.return_value.first.return_value = (0, 0, 0)

        result = get_daily_usage()

        assert result.request_count == 0
        assert result.total_input_tokens == 0
        assert result.total_output_tokens == 0


class TestCheckDailyLimit:
    """check_daily_limit 関数のテスト"""

    @patch("app.services.usage_service.get_daily_usage")
    @patch("app.services.usage_service.get_settings")
    def test_check_daily_limit_within_limits(self, mock_get_settings, mock_get_daily_usage):
        """制限内の場合はNoneを返す"""
        mock_get_settings.return_value.daily_request_limit = 100
        mock_get_settings.return_value.daily_input_token_limit = 2000000
        mock_get_settings.return_value.daily_output_token_limit = 100000
        mock_get_daily_usage.return_value = DailyUsageSummary(
            request_count=50,
            total_input_tokens=1000000,
            total_output_tokens=50000,
        )

        result = check_daily_limit()

        assert result is None

    @patch("app.services.usage_service.get_daily_usage")
    @patch("app.services.usage_service.get_settings")
    def test_check_daily_limit_request_count_exceeded(self, mock_get_settings, mock_get_daily_usage):
        """request_countが制限に達したらエラーメッセージを返す"""
        mock_get_settings.return_value.daily_request_limit = 100
        mock_get_settings.return_value.daily_input_token_limit = 2000000
        mock_get_settings.return_value.daily_output_token_limit = 100000
        mock_get_daily_usage.return_value = DailyUsageSummary(
            request_count=100,
            total_input_tokens=500000,
            total_output_tokens=20000,
        )

        result = check_daily_limit()

        expected = get_message("ERROR", "DAILY_REQUEST_LIMIT_EXCEEDED", limit="100")
        assert result == expected

    @patch("app.services.usage_service.get_daily_usage")
    @patch("app.services.usage_service.get_settings")
    def test_check_daily_limit_input_token_exceeded(self, mock_get_settings, mock_get_daily_usage):
        """total_input_tokensが制限に達したらエラーメッセージを返す"""
        mock_get_settings.return_value.daily_request_limit = 100
        mock_get_settings.return_value.daily_input_token_limit = 2000000
        mock_get_settings.return_value.daily_output_token_limit = 100000
        mock_get_daily_usage.return_value = DailyUsageSummary(
            request_count=10,
            total_input_tokens=2000000,
            total_output_tokens=20000,
        )

        result = check_daily_limit()

        expected = get_message("ERROR", "DAILY_INPUT_TOKEN_LIMIT_EXCEEDED", limit="2000000")
        assert result == expected

    @patch("app.services.usage_service.get_daily_usage")
    @patch("app.services.usage_service.get_settings")
    def test_check_daily_limit_output_token_exceeded(self, mock_get_settings, mock_get_daily_usage):
        """total_output_tokensが制限に達したらエラーメッセージを返す"""
        mock_get_settings.return_value.daily_request_limit = 100
        mock_get_settings.return_value.daily_input_token_limit = 2000000
        mock_get_settings.return_value.daily_output_token_limit = 100000
        mock_get_daily_usage.return_value = DailyUsageSummary(
            request_count=10,
            total_input_tokens=500000,
            total_output_tokens=100000,
        )

        result = check_daily_limit()

        expected = get_message("ERROR", "DAILY_OUTPUT_TOKEN_LIMIT_EXCEEDED", limit="100000")
        assert result == expected

    @patch("app.services.usage_service.get_daily_usage")
    @patch("app.services.usage_service.get_settings")
    def test_check_daily_limit_db_error_returns_none(self, mock_get_settings, mock_get_daily_usage):
        """get_daily_usageが例外を投げた場合、フェイルオープンでNoneを返す"""
        mock_get_settings.return_value.daily_request_limit = 100
        mock_get_settings.return_value.daily_input_token_limit = 2000000
        mock_get_settings.return_value.daily_output_token_limit = 100000
        mock_get_daily_usage.side_effect = Exception("DB接続エラー")

        result = check_daily_limit()

        assert result is None
