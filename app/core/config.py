import json
import logging
import os
from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import ModelType

logger = logging.getLogger(__name__)

_SECRET_NAME = os.getenv("AWS_SECRET_NAME", "medidocs/production")


def _load_aws_secrets() -> None:
    """AWS Secrets ManagerのシークレットをOSの環境変数に展開"""
    try:
        import boto3
    except ImportError:
        logger.warning("boto3 がインストールされていません。Secrets Manager をスキップします")
        return

    logger.info("AWS_SECRET_NAME=%s", _SECRET_NAME)
    region = os.getenv("AWS_REGION", "ap-northeast-1")
    try:
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=_SECRET_NAME)
        secrets: dict[str, str] = json.loads(response["SecretString"])
        logger.info("Secrets Manager のキー一覧: %s", list(secrets.keys()))
        injected = []
        skipped = []
        for key, value in secrets.items():
            if key not in os.environ or os.environ[key] == "":
                os.environ[key] = str(value)
                injected.append(key)
            else:
                skipped.append(key)
        if injected:
            logger.info("Secrets Manager から環境変数を展開しました: %s", injected)
        if skipped:
            logger.info("既存の環境変数のためスキップしました: %s", skipped)
    except Exception as e:
        logger.warning("Secrets Manager からの読み込みに失敗しました: %s", e)


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

    # Cloudflare AI Gateway
    cloudflare_account_id: str | None = None
    cloudflare_gateway_id: str | None = None
    cloudflare_aig_token: str | None = None

    # Application
    max_input_tokens: int = 200000
    min_input_tokens: int = 100
    max_token_threshold: int = 100000
    prompt_management: bool = True
    app_type: str = "default"
    selected_ai_model: str = ModelType.CLAUDE.value

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
    _load_aws_secrets()
    s = Settings()
    return s
