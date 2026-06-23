"""データベース層のテスト（インメモリ SQLite 使用、本番DBは触らない）"""

import json
from collections.abc import Generator
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base


@pytest.fixture(scope="module")
def sqlite_session_factory():
    """インメモリ SQLite 用の SessionFactory を返す"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.drop_all(bind=engine)


class TestGetDb:
    """`get_db` ジェネレータのテスト"""

    def test_get_db_yields_session(self, sqlite_session_factory):
        """`get_db` はセッションを yield すること"""
        with patch("app.core.database.SessionLocal", sqlite_session_factory):
            from app.core.database import get_db

            gen = get_db()
            session = next(gen)
            assert session is not None
            # セッションが利用可能であること
            result = session.execute(text("SELECT 1"))
            assert result is not None
            try:
                next(gen)
            except StopIteration:
                pass

    def test_get_db_closes_session_on_completion(self, sqlite_session_factory):
        """`get_db` は完了後にセッションを close すること"""
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.core.database.SessionLocal", mock_factory):
            from app.core.database import get_db

            gen = get_db()
            next(gen)
            try:
                next(gen)
            except StopIteration:
                pass

        mock_session.close.assert_called_once()

    def test_get_db_closes_session_on_exception(self, sqlite_session_factory):
        """`get_db` は例外発生時もセッションを close すること"""
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.core.database.SessionLocal", mock_factory):
            from app.core.database import get_db

            gen = cast(Generator, get_db())
            next(gen)
            try:
                gen.throw(RuntimeError("テストエラー"))
            except RuntimeError:
                pass

        mock_session.close.assert_called_once()


class TestGetDbSession:
    """`get_db_session` コンテキストマネージャのテスト"""

    def test_get_db_session_yields_session(self, sqlite_session_factory):
        """`get_db_session` はセッションを yield すること"""
        with patch("app.core.database.SessionLocal", sqlite_session_factory):
            from app.core.database import get_db_session

            with get_db_session() as session:
                assert session is not None
                result = session.execute(text("SELECT 1"))
                assert result is not None

    def test_get_db_session_commits_on_success(self):
        """`get_db_session` は正常終了時に commit すること"""
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.core.database.SessionLocal", mock_factory):
            from app.core.database import get_db_session

            with get_db_session():
                pass

        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()
        mock_session.close.assert_called_once()

    def test_get_db_session_rollback_on_exception(self):
        """`get_db_session` は例外発生時に rollback すること"""
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.core.database.SessionLocal", mock_factory):
            from app.core.database import get_db_session

            with pytest.raises(ValueError, match="テストエラー"):
                with get_db_session():
                    raise ValueError("テストエラー")

    def test_get_db_session_always_closes(self):
        """`get_db_session` は成功・失敗に関わらず close すること"""
        for raise_error in [False, True]:
            mock_session = MagicMock()
            mock_factory = MagicMock(return_value=mock_session)

            with patch("app.core.database.SessionLocal", mock_factory):
                from app.core.database import get_db_session

                try:
                    with get_db_session():
                        if raise_error:
                            raise RuntimeError("エラー")
                except RuntimeError:
                    pass

            mock_session.close.assert_called_once()

    def test_get_db_session_reraises_exception(self):
        """`get_db_session` は例外を再 raise すること"""
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.core.database.SessionLocal", mock_factory):
            from app.core.database import get_db_session

            with pytest.raises(ValueError, match="DB書き込みエラー"):
                with get_db_session():
                    raise ValueError("DB書き込みエラー")

    def test_get_db_session_does_not_commit_after_rollback(self):
        """`get_db_session` は例外後に commit しないこと"""
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.core.database.SessionLocal", mock_factory):
            from app.core.database import get_db_session

            try:
                with get_db_session():
                    raise Exception("エラー")
            except Exception:
                pass

        # commit が rollback より後に呼ばれていないこと
        assert mock_session.commit.call_count == 0
        assert mock_session.rollback.call_count == 1

    def test_get_db_session_data_persistence(self, sqlite_session_factory):
        """正常系: コミット後にデータが永続化されること"""
        from app.models.prompt import Prompt

        with patch("app.core.database.SessionLocal", sqlite_session_factory):
            from app.core.database import get_db_session

            # データ書き込み
            with get_db_session() as session:
                prompt = Prompt(
                    department="テスト科",
                    doctor="default",
                    document_type="退院時サマリ",
                    content="テストコンテンツ",
                )
                session.add(prompt)

            # 別セッションで読み込み確認
            verify_session = sqlite_session_factory()
            try:
                fetched = (
                    verify_session.query(Prompt)
                    .filter_by(department="テスト科")
                    .first()
                )
                assert fetched is not None
                assert fetched.content == "テストコンテンツ"
            finally:
                verify_session.close()

    def test_get_db_session_rollback_reverts_data(self, sqlite_session_factory):
        """異常系: ロールバック後にデータが残らないこと"""
        from app.models.prompt import Prompt

        with patch("app.core.database.SessionLocal", sqlite_session_factory):
            from app.core.database import get_db_session

            try:
                with get_db_session() as session:
                    prompt = Prompt(
                        department="ロールバック科",
                        doctor="default",
                        document_type="退院時サマリ",
                        content="ロールバックされるはず",
                    )
                    session.add(prompt)
                    raise RuntimeError("強制エラー")
            except RuntimeError:
                pass

            # データが存在しないこと
            verify_session = sqlite_session_factory()
            try:
                fetched = (
                    verify_session.query(Prompt)
                    .filter_by(department="ロールバック科")
                    .first()
                )
                assert fetched is None
            finally:
                verify_session.close()


class TestRotatingCredentials:
    """`_RotatingCredentials` のキャッシュ/再取得のテスト（boto3 はモック）"""

    @staticmethod
    def _build(ttl_seconds: int, password: str = "pw1"):
        """get_secret_value をモックした認証情報キャッシュとモッククライアントを返す"""
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            "SecretString": json.dumps({"username": "dbuser", "password": password})
        }
        with patch("app.core.database.boto3.client", return_value=mock_client):
            from app.core.database import _RotatingCredentials

            credentials = _RotatingCredentials(
                "rds-secret", "ap-northeast-1", ttl_seconds
            )
        return credentials, mock_client

    def test_maps_username_and_password(self):
        """シークレットの username/password を user/password に変換すること"""
        credentials, _ = self._build(ttl_seconds=300)
        assert credentials.get() == {"user": "dbuser", "password": "pw1"}

    def test_caches_within_ttl(self):
        """TTL 内では Secrets Manager を再呼び出ししないこと"""
        credentials, mock_client = self._build(ttl_seconds=300)
        credentials.get()
        credentials.get()
        assert mock_client.get_secret_value.call_count == 1

    def test_force_refresh_refetches(self):
        """force_refresh=True で再取得すること"""
        credentials, mock_client = self._build(ttl_seconds=300)
        credentials.get()
        credentials.get(force_refresh=True)
        assert mock_client.get_secret_value.call_count == 2

    def test_refetches_after_ttl_expiry(self):
        """TTL 切れ（ttl=0）では毎回再取得すること"""
        credentials, mock_client = self._build(ttl_seconds=0)
        credentials.get()
        credentials.get()
        assert mock_client.get_secret_value.call_count == 2
