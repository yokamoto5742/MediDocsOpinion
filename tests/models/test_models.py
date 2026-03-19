"""ORM モデル層のテスト（インメモリ SQLite 使用）"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.evaluation_prompt import EvaluationPrompt
from app.models.prompt import Prompt
from app.models.usage import SummaryUsage


@pytest.fixture(scope="module")
def db_engine():
    """モジュール共通のインメモリ SQLite エンジン"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(db_engine):
    """各テスト用セッション（テスト後にロールバック）"""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


class TestBase:
    """Base クラスのテスト"""

    def test_base_is_declarative(self):
        """`Base` が SQLAlchemy の DeclarativeBase を継承していること"""
        from sqlalchemy.orm import DeclarativeBase
        assert issubclass(Base, DeclarativeBase)

    def test_all_models_share_same_metadata(self):
        """全モデルが同一 metadata を持つこと"""
        assert Prompt.metadata is EvaluationPrompt.metadata
        assert EvaluationPrompt.metadata is SummaryUsage.metadata


class TestPromptModel:
    """Prompt モデルのテスト"""

    def test_table_name(self):
        assert Prompt.__tablename__ == "prompts"

    def test_required_columns_exist(self, db_engine):
        """必須カラムが存在すること"""
        inspector = inspect(db_engine)
        columns = {c["name"] for c in inspector.get_columns("prompts")}
        assert "id" in columns
        assert "department" in columns
        assert "document_type" in columns
        assert "doctor" in columns
        assert "content" in columns
        assert "selected_model" in columns
        assert "is_default" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_index_exists(self, db_engine):
        """ix_prompts_lookup インデックスが存在すること"""
        inspector = inspect(db_engine)
        indexes = {i["name"] for i in inspector.get_indexes("prompts")}
        assert "ix_prompts_lookup" in indexes

    def test_index_columns(self, db_engine):
        """ix_prompts_lookup が正しいカラムを持つこと"""
        inspector = inspect(db_engine)
        indexes = inspector.get_indexes("prompts")
        lookup_index = next(i for i in indexes if i["name"] == "ix_prompts_lookup")
        assert set(lookup_index["column_names"]) == {"department", "document_type", "doctor"}

    def test_create_prompt(self, db):
        """Prompt の作成・取得"""
        prompt = Prompt(
            department="眼科",
            doctor="橋本義弘",
            document_type="他院への紹介",
            content="眼科用プロンプト",
            selected_model="Claude",
            is_default=False,
        )
        db.add(prompt)
        db.flush()

        fetched = db.query(Prompt).filter_by(department="眼科").first()
        assert fetched is not None
        assert fetched.doctor == "橋本義弘"
        assert fetched.document_type == "他院への紹介"
        assert fetched.content == "眼科用プロンプト"
        assert fetched.selected_model == "Claude"
        assert fetched.is_default is False

    def test_is_default_defaults_to_false(self, db):
        """is_default のデフォルト値は False"""
        prompt = Prompt(
            department="default",
            doctor="default",
            document_type="返書",
            content="デフォルトプロンプト",
        )
        db.add(prompt)
        db.flush()

        fetched = db.query(Prompt).filter_by(department="default", document_type="返書").first()
        assert fetched.is_default is False

    def test_selected_model_nullable(self, db):
        """selected_model は NULL 許容"""
        prompt = Prompt(department="内科", doctor="default", document_type="退院時サマリ", content="内科プロンプト")
        db.add(prompt)
        db.flush()

        fetched = db.query(Prompt).filter_by(department="内科").first()
        assert fetched.selected_model is None

    def test_content_nullable(self, db):
        """content は NULL 許容"""
        prompt = Prompt(
            department="外科",
            doctor="default",
            document_type="他院への紹介",
        )
        db.add(prompt)
        db.flush()

        fetched = db.query(Prompt).filter_by(department="外科").first()
        assert fetched.content is None

    def test_multiple_prompts_same_department(self, db):
        """同一診療科で複数プロンプト登録可能（異なる医師・文書タイプ）"""
        prompts = [
            Prompt(department="循環器内科", doctor="default", document_type="他院への紹介", content="A"),
            Prompt(department="循環器内科", doctor="山田太郎", document_type="他院への紹介", content="B"),
            Prompt(department="循環器内科", doctor="default", document_type="返書", content="C"),
        ]
        for p in prompts:
            db.add(p)
        db.flush()

        count = db.query(Prompt).filter_by(department="循環器内科").count()
        assert count == 3


class TestEvaluationPromptModel:
    """EvaluationPrompt モデルのテスト"""

    def test_table_name(self):
        assert EvaluationPrompt.__tablename__ == "evaluation_prompts"

    def test_required_columns_exist(self, db_engine):
        """必須カラムが存在すること"""
        inspector = inspect(db_engine)
        columns = {c["name"] for c in inspector.get_columns("evaluation_prompts")}
        assert "id" in columns
        assert "document_type" in columns
        assert "content" in columns
        assert "is_active" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_document_type_unique_constraint(self, db):
        """document_type は UNIQUE 制約"""
        ep1 = EvaluationPrompt(document_type="退院時サマリ", content="評価プロンプト1")
        db.add(ep1)
        db.flush()

        ep2 = EvaluationPrompt(document_type="退院時サマリ", content="評価プロンプト2")
        db.add(ep2)
        with pytest.raises(Exception):
            db.flush()

    def test_create_evaluation_prompt(self, db):
        """EvaluationPrompt の作成・取得"""
        ep = EvaluationPrompt(
            document_type="他院への紹介_評価",
            content="評価用プロンプト内容",
            is_active=True,
        )
        db.add(ep)
        db.flush()

        fetched = db.query(EvaluationPrompt).filter_by(document_type="他院への紹介_評価").first()
        assert fetched is not None
        assert fetched.content == "評価用プロンプト内容"
        assert fetched.is_active is True

    def test_is_active_defaults_to_true(self, db):
        """is_active のデフォルト値は True"""
        ep = EvaluationPrompt(
            document_type="返書_評価2",
            content="評価プロンプト",
        )
        db.add(ep)
        db.flush()

        fetched = db.query(EvaluationPrompt).filter_by(document_type="返書_評価2").first()
        assert fetched.is_active is True

    def test_inactive_evaluation_prompt(self, db):
        """is_active=False で登録可能"""
        ep = EvaluationPrompt(
            document_type="非アクティブ評価",
            content="非アクティブプロンプト",
            is_active=False,
        )
        db.add(ep)
        db.flush()

        fetched = db.query(EvaluationPrompt).filter_by(document_type="非アクティブ評価").first()
        assert fetched.is_active is False


class TestSummaryUsageModel:
    """SummaryUsage モデルのテスト"""

    def test_table_name(self):
        assert SummaryUsage.__tablename__ == "summary_usage"

    def test_required_columns_exist(self, db_engine):
        """必須カラムが存在すること"""
        inspector = inspect(db_engine)
        columns = {c["name"] for c in inspector.get_columns("summary_usage")}
        assert "id" in columns
        assert "date" in columns
        assert "app_type" in columns
        assert "document_types" in columns  # DBカラム名
        assert "model_detail" in columns    # DBカラム名
        assert "department" in columns
        assert "doctor" in columns
        assert "input_tokens" in columns
        assert "output_tokens" in columns
        assert "processing_time" in columns

    def test_column_name_mapping_document_type(self):
        """document_type プロパティが DBカラム 'document_types' にマッピングされること"""
        col = SummaryUsage.__table__.c["document_types"]
        assert col is not None

    def test_column_name_mapping_model(self):
        """model プロパティが DBカラム 'model_detail' にマッピングされること"""
        col = SummaryUsage.__table__.c["model_detail"]
        assert col is not None

    def test_indexes_exist(self, db_engine):
        """集計・日付用インデックスが存在すること"""
        inspector = inspect(db_engine)
        indexes = {i["name"] for i in inspector.get_indexes("summary_usage")}
        assert "ix_summary_usage_aggregation" in indexes
        assert "ix_summary_usage_date_document_type" in indexes

    def test_create_usage_record(self, db):
        """SummaryUsage の作成・取得"""
        jst = ZoneInfo("Asia/Tokyo")
        usage = SummaryUsage(
            date=datetime.now(jst),
            department="眼科",
            doctor="橋本義弘",
            document_type="他院への紹介",
            model="Claude",
            input_tokens=1000,
            output_tokens=500,
            processing_time=2.5,
            app_type="dischargesummary",
        )
        db.add(usage)
        db.flush()

        fetched = db.query(SummaryUsage).filter_by(department="眼科").first()
        assert fetched is not None
        assert fetched.doctor == "橋本義弘"
        assert fetched.document_type == "他院への紹介"
        assert fetched.model == "Claude"
        assert fetched.input_tokens == 1000
        assert fetched.output_tokens == 500
        assert fetched.processing_time == 2.5
        assert fetched.app_type == "dischargesummary"

    def test_all_fields_nullable(self, db):
        """数値フィールドは NULL 許容"""
        usage = SummaryUsage(
            department="default",
            doctor="default",
            document_type="返書",
            model="Gemini_Pro",
        )
        db.add(usage)
        db.flush()

        fetched = db.query(SummaryUsage).filter_by(department="default").first()
        assert fetched.input_tokens is None
        assert fetched.output_tokens is None
        assert fetched.processing_time is None
        assert fetched.app_type is None

    def test_multiple_usage_records(self, db):
        """複数レコード登録・取得"""
        jst = ZoneInfo("Asia/Tokyo")
        records = [
            SummaryUsage(
                date=datetime.now(jst),
                department="内科",
                doctor="default",
                document_type="退院時サマリ",
                model="Claude",
                input_tokens=i * 100,
                output_tokens=i * 50,
                processing_time=float(i),
            )
            for i in range(1, 4)
        ]
        for r in records:
            db.add(r)
        db.flush()

        count = db.query(SummaryUsage).filter_by(department="内科").count()
        assert count == 3
