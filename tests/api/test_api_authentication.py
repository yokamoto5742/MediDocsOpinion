"""CSRF認証の統合テスト"""

import hashlib
import hmac
import time

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import generate_csrf_token, verify_csrf_token


class TestCsrfAuthentication:
    """APIエンドポイントのCSRF認証テスト"""

    def test_protected_endpoint_requires_csrf_token(self, client: TestClient):
        """保護されたエンドポイントはCSRFトークンなしで401エラー"""
        response = client.post(
            "/api/summary/generate",
            json={
                "medical_text": "test",
                "department": "内科",
                "document_type": "診療情報提供書",
            },
        )
        assert response.status_code == 401
        assert "CSRFトークンが必要です" in response.json()["detail"]

    def test_protected_endpoint_with_invalid_token(self, client: TestClient):
        """無効なCSRFトークンで403エラー"""
        response = client.post(
            "/api/summary/generate",
            json={
                "medical_text": "test",
                "department": "内科",
                "document_type": "診療情報提供書",
            },
            headers={"X-CSRF-Token": "invalid.token"},
        )
        assert response.status_code == 403
        assert "無効または期限切れのCSRFトークンです" in response.json()["detail"]

    def test_evaluation_endpoint_requires_csrf_token(self, client: TestClient):
        """評価エンドポイントもCSRFトークン必須"""
        response = client.post(
            "/api/evaluation/evaluate",
            json={
                "document_type": "診療情報提供書",
                "input_text": "test",
                "output_summary": "test",
            },
        )
        assert response.status_code == 401
        assert "CSRFトークンが必要です" in response.json()["detail"]

    def test_web_pages_do_not_require_csrf(self, client: TestClient):
        """WebページUIはCSRF認証不要"""
        response = client.get("/")
        assert response.status_code == 200

    def test_public_endpoints_no_csrf(self, client: TestClient):
        """公開エンドポイント(GET)はCSRF認証不要"""
        # 設定エンドポイント
        response = client.get("/api/settings/departments")
        assert response.status_code == 200
        assert "departments" in response.json()

        # モデル一覧エンドポイント
        response = client.get("/api/summary/models")
        assert response.status_code == 200

    def test_admin_endpoints_require_csrf(self, client: TestClient, csrf_headers):
        """管理用エンドポイント(POST/DELETE)はCSRF認証必須"""
        # プロンプト作成はCSRF トークン必須
        response = client.post(
            "/api/prompts/",
            json={
                "department": "内科",
                "doctor": "default",
                "document_type": "他院への紹介",
                "content": "test",
            },
        )
        assert response.status_code == 401

        # CSRF トークンありでは成功
        response = client.post(
            "/api/prompts/",
            json={
                "department": "内科",
                "doctor": "default",
                "document_type": "他院への紹介",
                "content": "test",
            },
            headers=csrf_headers,
        )
        assert response.status_code == 200

    def test_expired_csrf_token_returns_403(self, client: TestClient, monkeypatch):
        """期限切れCSRFトークンで403エラー"""
        monkeypatch.setenv("CSRF_SECRET_KEY", "test-csrf-secret-key")
        settings = Settings()
        old_timestamp = int(time.time()) - (settings.csrf_token_expire_minutes * 60 + 10)
        secret_key = settings.csrf_secret_key.encode()
        signature = hmac.new(secret_key, str(old_timestamp).encode(), hashlib.sha256).hexdigest()
        expired_token = f"{old_timestamp}.{signature}"

        response = client.post(
            "/api/summary/generate",
            json={"medical_text": "test", "department": "内科", "document_type": "退院時サマリ"},
            headers={"X-CSRF-Token": expired_token},
        )
        assert response.status_code == 403
        assert "無効または期限切れのCSRFトークンです" in response.json()["detail"]

    def test_delete_prompt_requires_csrf(self, client: TestClient):
        """プロンプト削除エンドポイントもCSRFトークン必須"""
        response = client.delete("/api/prompts/1")
        assert response.status_code == 401
        assert "CSRFトークンが必要です" in response.json()["detail"]

    def test_evaluation_save_requires_csrf(self, client: TestClient):
        """評価プロンプト保存エンドポイントもCSRFトークン必須"""
        response = client.post(
            "/api/evaluation/prompts",
            json={"document_type": "退院時サマリ", "content": "test"},
        )
        assert response.status_code == 401
        assert "CSRFトークンが必要です" in response.json()["detail"]

    def test_security_headers_present(self, client: TestClient):
        """レスポンスにセキュリティヘッダーが付与される"""
        response = client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Content-Security-Policy" in response.headers


class TestVerifyCsrfToken:
    """verify_csrf_token 関数の単体テスト"""

    def _make_settings(self, monkeypatch) -> Settings:
        monkeypatch.setenv("CSRF_SECRET_KEY", "test-csrf-secret-key")
        return Settings()

    def test_valid_token(self, monkeypatch):
        """正常なトークンはTrueを返す"""
        settings = self._make_settings(monkeypatch)
        token = generate_csrf_token(settings)
        assert verify_csrf_token(token, settings) is True

    def test_malformed_token_no_dot(self, monkeypatch):
        """ドットなしトークンはFalseを返す"""
        settings = self._make_settings(monkeypatch)
        assert verify_csrf_token("malformedtoken", settings) is False

    def test_malformed_token_bad_timestamp(self, monkeypatch):
        """タイムスタンプが数値でないトークンはFalseを返す"""
        settings = self._make_settings(monkeypatch)
        assert verify_csrf_token("notanumber.somesignature", settings) is False

    def test_wrong_signature(self, monkeypatch):
        """署名が不正なトークンはFalseを返す"""
        settings = self._make_settings(monkeypatch)
        token = f"{int(time.time())}.invalidsignature"
        assert verify_csrf_token(token, settings) is False

    def test_expired_token(self, monkeypatch):
        """期限切れトークンはFalseを返す"""
        settings = self._make_settings(monkeypatch)
        old_timestamp = int(time.time()) - (settings.csrf_token_expire_minutes * 60 + 10)
        secret_key = settings.csrf_secret_key.encode()
        signature = hmac.new(secret_key, str(old_timestamp).encode(), hashlib.sha256).hexdigest()
        expired_token = f"{old_timestamp}.{signature}"
        assert verify_csrf_token(expired_token, settings) is False
