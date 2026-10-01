import json
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock, patch

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import generate_csrf_token
from app.main import app
from app.models.base import Base

INTEGRATION_CSRF_SECRET = "integration-test-csrf-secret-key"


def make_test_settings(**overrides) -> Settings:
    """統合テスト用設定を生成（オーバーライド可能なデフォルト値付き）"""
    return Settings(
        csrf_secret_key=INTEGRATION_CSRF_SECRET,
        anthropic_model="claude-test-model",
        gemini_model="gemini-test-model",
        evaluation_model="Gemini",
        min_input_tokens=overrides.get("min_input_tokens", 10),
        max_input_tokens=overrides.get("max_input_tokens", 300_000),
        max_token_threshold=overrides.get("max_token_threshold", 150_000),
        daily_request_limit=overrides.get("daily_request_limit", 100),
        daily_input_token_limit=overrides.get("daily_input_token_limit", 5_000_000),
        daily_output_token_limit=overrides.get("daily_output_token_limit", 100_000),
        csrf_token_expire_minutes=overrides.get("csrf_token_expire_minutes", 60),
    )


@pytest.fixture(scope="function")
def integration_db():
    """統合テスト用インメモリSQLite DB"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(integration_db):
    """テストデータの挿入・検証用DBセッション"""
    db = integration_db()
    yield db
    db.close()


@pytest.fixture(scope="function")
def integration_client(integration_db, monkeypatch):
    """統合テスト用TestClient（外部AI APIのみモック、DB/Serviceは実動作）"""
    monkeypatch.setenv("CSRF_SECRET_KEY", INTEGRATION_CSRF_SECRET)
    test_settings = make_test_settings()

    def override_get_db():
        db = integration_db()
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def override_get_db_session():
        db = integration_db()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: test_settings

    with (
        patch("app.services.summary_service.settings", test_settings),
        patch("app.services.model_selector.settings", test_settings),
        patch("app.services.evaluation_service.settings", test_settings),
        patch("app.services.usage_service.get_db_session", override_get_db_session),
        patch("app.services.model_selector.get_db_session", override_get_db_session),
        patch(
            "app.services.evaluation_service.get_db_session", override_get_db_session
        ),
        patch("app.services.usage_service.settings", test_settings),
    ):
        yield TestClient(app)

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_settings, None)


@pytest.fixture
def csrf_headers(monkeypatch):
    """CSRFトークン付きヘッダーを生成"""
    monkeypatch.setenv("CSRF_SECRET_KEY", INTEGRATION_CSRF_SECRET)
    token = generate_csrf_token(make_test_settings())
    return {"X-CSRF-Token": token}


def patch_summary_client(result: tuple[str, int, int] = ("生成テキスト", 100, 50)):
    """文書生成で使うAI APIクライアントの生成を差し替える（with 文で使用し、生成関数のモックを受け取る）"""
    mock_create = MagicMock()
    mock_create.return_value.generate_summary.return_value = result
    return patch("app.services.summary_service.create_client", mock_create)


def last_event(response) -> dict:
    """SSEレスポンスの最後のイベント（complete または error）を返す"""
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    return parse_sse_events(response.text)[-1]


def parse_sse_events(response_text: str) -> list[dict]:
    """SSEレスポンステキストをイベントリストにパース"""
    events = []
    for block in response_text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event_type = None
        data = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
        if event_type and data is not None:
            events.append({"type": event_type, "data": data})
    return events
