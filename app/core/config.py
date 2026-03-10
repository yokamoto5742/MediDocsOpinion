import logging
import os
from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import ModelType

logger = logging.getLogger(__name__)

_SECRET_NAME = os.getenv("AWS_SECRET_NAME", "medidocs/production")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = ""
    postgres_db: str = "medidocs"
    postgres_ssl: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    database_url: str | None = None

    # AWS Bedrock (Claude)
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "ap-northeast-1"
    anthropic_model: str | None = None
    claude_model: str | None = None

    # Google Vertex AI (Gemini)
    google_credentials_json: str | None = None
    gemini_model: str | None = None
    google_project_id: str | None = None
    google_location: str = "global"
    gemini_thinking_level: str = "HIGH"
    gemini_evaluation_model: str | None = None

    # Application
    max_input_tokens: int = 200000
    min_input_tokens: int = 100
    max_token_threshold: int = 100000
    prompt_management: bool = True
    app_type: str = "default"
    selected_ai_model: str = ModelType.CLAUDE.value

    # 日次利用制限
    daily_request_limit: int = 100
    daily_input_token_limit: int = 5000000
    daily_output_token_limit: int = 100000

    # CSRF認証
    csrf_secret_key: str = "default-csrf-secret-key"
    csrf_token_expire_minutes: int = 60

    # CORS設定
    cors_origins: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = ["*"]

    def get_database_url(self) -> str:
        """データベース接続URLを構築"""
        if self.database_url:
            return self.database_url
        ssl_param = "?sslmode=require" if self.postgres_ssl else ""
        encoded_password = quote_plus(self.postgres_password)
        return (
            f"postgresql://{self.postgres_user}:{encoded_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}{ssl_param}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
