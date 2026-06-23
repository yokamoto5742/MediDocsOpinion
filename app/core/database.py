import json
import logging
import threading
import time
from contextlib import contextmanager
from typing import Any, Iterator

import boto3
import psycopg2
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

engine = create_engine(
    settings.get_database_url(),
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=False,
)


class _RotatingCredentials:
    """Secrets Manager から取得したDB認証情報を短時間キャッシュする"""

    def __init__(self, secret_name: str, region: str, ttl_seconds: int) -> None:
        self._secret_name = secret_name
        self._ttl_seconds = ttl_seconds
        self._client = boto3.client("secretsmanager", region_name=region)
        self._lock = threading.Lock()
        self._cached: dict[str, str] | None = None
        self._fetched_at = 0.0

    def get(self, force_refresh: bool = False) -> dict[str, str]:
        with self._lock:
            expired = (time.monotonic() - self._fetched_at) >= self._ttl_seconds
            if force_refresh or self._cached is None or expired:
                self._cached = self._fetch()
                self._fetched_at = time.monotonic()
            return self._cached

    def _fetch(self) -> dict[str, str]:
        response = self._client.get_secret_value(SecretId=self._secret_name)
        data = json.loads(response["SecretString"])
        return {"user": data["username"], "password": data["password"]}


def _register_credential_rotation(
    secret_name: str, region: str, ttl_seconds: int
) -> None:
    """接続確立時に最新の認証情報を注入し、認証失敗時は再取得して再接続する"""
    credentials = _RotatingCredentials(secret_name, region, ttl_seconds)

    @event.listens_for(engine, "do_connect")
    def _provide_credentials(
        dialect: Any, conn_rec: Any, cargs: tuple[Any, ...], cparams: dict[str, Any]
    ) -> Any:
        creds = credentials.get()
        cparams["user"] = creds["user"]
        cparams["password"] = creds["password"]
        try:
            return psycopg2.connect(*cargs, **cparams)
        except psycopg2.OperationalError:
            # ローテーション直後の古いパスワードを想定し、再取得して1回だけ再接続
            logger.warning("DB認証に失敗したため認証情報を再取得して再接続します")
            creds = credentials.get(force_refresh=True)
            cparams["user"] = creds["user"]
            cparams["password"] = creds["password"]
            return psycopg2.connect(*cargs, **cparams)


if settings.db_secret_name:
    _register_credential_rotation(
        settings.db_secret_name, settings.aws_region, settings.db_secret_ttl_seconds
    )


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI Depends 用"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Iterator[Session]:
    """サービス層用コンテキストマネージャ"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
