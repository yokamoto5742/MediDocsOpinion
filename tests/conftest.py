from datetime import datetime
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# プロジェクトのルートディレクトリをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import generate_csrf_token
from app.main import app
from app.models.base import Base
from app.models.prompt import Prompt
from app.models.usage import SummaryUsage

# テスト共通の医療テキスト（実際の入力に近いサンプル）
VALID_MEDICAL_TEXT = (
    "患者は60歳男性。主訴は胸痛。"
    "既往歴：高血圧、糖尿病。"
    "現病歴：3日前から安静時にも胸痛あり。"
    "身体所見：血圧150/90mmHg、脈拍80回/分。"
    "検査：心電図でST上昇あり。トロポニンT陽性。"
    "診断：急性心筋梗塞。治療：PCI施行。経過良好にて退院。"
) * 5


@pytest.fixture(scope="function", autouse=True)
def override_settings(monkeypatch):
    """テスト環境用の設定をオーバーライド"""
    monkeypatch.setenv("CSRF_SECRET_KEY", "test-csrf-secret-key")

    def get_test_settings():
        return Settings()

    app.dependency_overrides[get_settings] = get_test_settings
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_db():
    """テスト用のインメモリSQLiteデータベース"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestingSessionLocal()

    Base.metadata.drop_all(bind=engine)
    # get_settingsのオーバーライドは維持（autouse fixtureで管理）
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(test_db):
    """FastAPIテストクライアント"""
    return TestClient(app)


@pytest.fixture
def sample_prompts(test_db):
    """テスト用のサンプルプロンプト"""
    prompts = [
        Prompt(department="default", doctor="default", document_type="他院への紹介", content="デフォルトプロンプト",
               is_default=True),
        Prompt(
            department="眼科",
            doctor="橋本義弘",
            document_type="他院への紹介",
            content="眼科用プロンプト",
            selected_model="Claude",
            is_default=False,
        ),
    ]
    for prompt in prompts:
        test_db.add(prompt)
    test_db.commit()
    for prompt in prompts:
        test_db.refresh(prompt)
    return prompts


@pytest.fixture
def sample_usage_records(test_db):
    """テスト用のサンプル使用統計"""
    jst = ZoneInfo("Asia/Tokyo")
    records = [
        SummaryUsage(
            date=datetime.now(jst),
            department="眼科",
            doctor="橋本義弘",
            document_type="他院への紹介",
            model="Claude",
            input_tokens=1000,
            output_tokens=500,
            processing_time=2.5,
        ),
        SummaryUsage(
            date=datetime.now(jst),
            department="default",
            doctor="default",
            document_type="返書",
            model="Gemini_Pro",
            input_tokens=2000,
            output_tokens=800,
            processing_time=3.2,
        ),
    ]
    for record in records:
        test_db.add(record)
    test_db.commit()
    for record in records:
        test_db.refresh(record)
    return records


@pytest.fixture
def csrf_headers():
    """CSRFトークン付きヘッダーを生成（override_settings が先に CSRF_SECRET_KEY を設定済み）"""
    settings = Settings()
    token = generate_csrf_token(settings)
    return {"X-CSRF-Token": token}
