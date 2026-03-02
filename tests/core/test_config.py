import os
from unittest.mock import patch

import pytest

from app.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """各テスト前にsettingsキャッシュをクリア"""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestSettingsInitialization:
    """Settings 初期化のテスト"""

    @patch.dict(
        os.environ,
        {
            "POSTGRES_HOST": "testhost",
            "POSTGRES_PORT": "5433",
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass",
            "POSTGRES_DB": "testdb",
        },
        clear=True,
    )
    def test_settings_from_environment(self):
        """設定 - 環境変数から取得"""
        settings = Settings()

        assert settings.postgres_host == "testhost"
        assert settings.postgres_port == 5433
        assert settings.postgres_user == "testuser"
        assert settings.postgres_password == "testpass"
        assert settings.postgres_db == "testdb"

    @patch.dict(
        os.environ,
        {
            "ANTHROPIC_MODEL": "claude-3-opus-20240229",
            "CLAUDE_MODEL": "claude-3-5-sonnet-20241022",
            "GEMINI_MODEL": "gemini-1.5-pro-002",
        },
        clear=True,
    )
    def test_settings_ai_models(self):
        """設定 - AIモデル設定"""
        settings = Settings()

        assert settings.anthropic_model == "claude-3-opus-20240229"
        assert settings.claude_model == "claude-3-5-sonnet-20241022"
        assert settings.gemini_model == "gemini-1.5-pro-002"

    @patch.dict(
        os.environ,
        {
            "MAX_INPUT_TOKENS": "300000",
            "MIN_INPUT_TOKENS": "200",
            "MAX_TOKEN_THRESHOLD": "150000",
        },
        clear=True,
    )
    def test_settings_token_limits(self):
        """設定 - トークン制限"""
        settings = Settings()

        assert settings.max_input_tokens == 300000
        assert settings.min_input_tokens == 200
        assert settings.max_token_threshold == 150000


class TestGetDatabaseUrl:
    """get_database_url メソッドのテスト"""

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgres://user:pass@heroku-host:5432/heroku-db",
        },
        clear=True,
    )
    def test_get_database_url_from_database_url(self):
        """DB URL構築 - DATABASE_URL（Heroku形式）使用"""
        settings = Settings()
        url = settings.get_database_url()

        # DATABASE_URL はそのまま返される
        assert url == "postgres://user:pass@heroku-host:5432/heroku-db"

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://user:pass@heroku-host:5432/heroku-db",
        },
        clear=True,
    )
    def test_get_database_url_already_postgresql(self):
        """DB URL構築 - すでに postgresql:// の場合"""
        settings = Settings()
        url = settings.get_database_url()

        # 変換不要
        assert url == "postgresql://user:pass@heroku-host:5432/heroku-db"

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgres://user:pass@host:5432/db",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_USER": "otheruser",
        },
        clear=True,
    )
    def test_get_database_url_database_url_priority(self):
        """DB URL構築 - DATABASE_URLが優先"""
        settings = Settings()
        url = settings.get_database_url()

        # DATABASE_URL が優先される（個別設定は無視）
        assert url == "postgres://user:pass@host:5432/db"


class TestGetSettings:
    """get_settings 関数のテスト"""

    def test_get_settings_returns_settings_instance(self):
        """get_settings - Settingsインスタンスを返す"""
        settings = get_settings()

        assert isinstance(settings, Settings)

    def test_get_settings_cached(self):
        """get_settings - キャッシュ動作確認"""
        # lru_cache により同じインスタンスが返される
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2


class TestSettingsEdgeCases:
    """Settings エッジケース"""

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgres://user:pass@host/db",
        },
        clear=True,
    )
    def test_get_database_url_no_port(self):
        """DB URL構築 - ポートなし"""
        settings = Settings()
        url = settings.get_database_url()

        # ポートがない場合も正常に処理
        assert url == "postgres://user:pass@host/db"

    @patch.dict(
        os.environ,
        {
            "GEMINI_THINKING_LEVEL": "LOW",
        },
        clear=True,
    )
    def test_settings_gemini_thinking_level(self):
        """設定 - Gemini Thinking Level"""
        settings = Settings()

        assert settings.gemini_thinking_level == "LOW"

    @patch.dict(
        os.environ,
        {
            "GOOGLE_PROJECT_ID": "test-project-123",
            "GOOGLE_LOCATION": "us-central1",
        },
        clear=True,
    )
    def test_settings_google_credentials(self):
        """設定 - Google認証情報"""
        settings = Settings()

        assert settings.google_project_id == "test-project-123"
        assert settings.google_location == "us-central1"

    @patch.dict(os.environ, {}, clear=True)
    def test_settings_google_location_default(self):
        """設定 - Google Location デフォルト値"""
        settings = Settings()

        assert settings.google_location == "global"

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "AWS_REGION": "ap-northeast-1",
        },
        clear=True,
    )
    def test_settings_aws_credentials(self):
        """設定 - AWS認証情報"""
        settings = Settings()

        assert settings.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert settings.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert settings.aws_region == "ap-northeast-1"

    @patch.dict(
        os.environ,
        {
            "DB_POOL_SIZE": "10",
            "DB_MAX_OVERFLOW": "20",
            "DB_POOL_TIMEOUT": "60",
            "DB_POOL_RECYCLE": "3600",
        },
        clear=True,
    )
    def test_settings_db_pool_configuration(self):
        """設定 - DBプール設定"""
        settings = Settings()

        assert settings.db_pool_size == 10
        assert settings.db_max_overflow == 20
        assert settings.db_pool_timeout == 60
        assert settings.db_pool_recycle == 3600

    @patch.dict(os.environ, {}, clear=True)
    def test_settings_db_pool_defaults(self):
        """設定 - DBプールデフォルト値"""
        settings = Settings()

        assert settings.db_pool_size == 5
        assert settings.db_max_overflow == 10
        assert settings.db_pool_timeout == 30
        assert settings.db_pool_recycle == 1800

    @patch.dict(
        os.environ,
        {
            "PROMPT_MANAGEMENT": "false",
            "APP_TYPE": "summary",
            "SELECTED_AI_MODEL": "Gemini_Pro",
        },
        clear=True,
    )
    def test_settings_application_config(self):
        """設定 - アプリケーション設定"""
        settings = Settings()

        assert settings.prompt_management is False
        assert settings.app_type == "summary"
        assert settings.selected_ai_model == "Gemini_Pro"

    @patch.dict(os.environ, {}, clear=True)
    def test_settings_application_config_defaults(self):
        """設定 - アプリケーション設定デフォルト値"""
        settings = Settings()

        assert settings.prompt_management is True
        assert settings.app_type == "default"
        assert settings.selected_ai_model == "Claude"

    @patch.dict(
        os.environ,
        {
            "UNKNOWN_ENV_VAR": "unknown_value",
        },
        clear=True,
    )
    def test_settings_ignore_extra_env_vars(self):
        """設定 - 未定義の環境変数は無視"""
        # extra="ignore" により未定義の環境変数はエラーにならない
        settings = Settings()

        assert not hasattr(settings, "unknown_env_var")


class TestSettingsValidation:
    """Settings バリデーションのテスト"""

    @patch.dict(
        os.environ,
        {
            "POSTGRES_PORT": "invalid",
        },
        clear=True,
    )
    def test_settings_invalid_port_type(self):
        """設定 - 無効なポート型"""
        with pytest.raises(Exception):
            Settings()

    @patch.dict(
        os.environ,
        {
            "MAX_INPUT_TOKENS": "not_a_number",
        },
        clear=True,
    )
    def test_settings_invalid_integer_type(self):
        """設定 - 無効な整数型"""
        with pytest.raises(Exception):
            Settings()

    def test_settings_invalid_boolean_type(self):
        """設定 - 無効なブール型"""
        # Pydantic v2 は無効なブール値でバリデーションエラーを発生させる
        with patch.dict(
            os.environ,
            {
                "POSTGRES_SSL": "invalid_bool",
            },
            clear=True,
        ):
            with pytest.raises(Exception) as exc_info:
                Settings()

            # Pydantic ValidationError が発生
            assert "validation error" in str(exc_info.value).lower() or "bool" in str(exc_info.value).lower()
