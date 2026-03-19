"""統合テスト: セキュリティ（CSRF保護・セキュリティヘッダー・XSSサニタイゼーション）"""
import hashlib
import hmac
import time
from unittest.mock import patch

from fastapi import status

from tests.integration.conftest import INTEGRATION_CSRF_SECRET

_VALID_MEDICAL_TEXT = (
    "患者は60歳男性。2型糖尿病にて長期加療中。"
    "血糖コントロール不良にて入院し、インスリン調整後に退院となった。"
)

_STATE_CHANGING_POSTS = [
    ("/api/summary/generate", {
        "medical_text": _VALID_MEDICAL_TEXT,
        "model": "Claude",
        "model_explicitly_selected": True,
    }),
    ("/api/prompts/", {
        "department": "内科",
        "document_type": "退院時サマリ",
        "doctor": "default",
        "content": "テストプロンプト",
    }),
    ("/api/evaluation/prompts", {
        "document_type": "退院時サマリ",
        "content": "テスト評価プロンプト",
    }),
]


class TestCSRFProtection:
    def test_missing_token_returns_401(
        self, integration_client, db_session
    ):
        """CSRFトークンなしのPOSTは401を返す"""
        response = integration_client.post(
            "/api/summary/generate",
            json={"medical_text": _VALID_MEDICAL_TEXT},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_token_returns_403(
        self, integration_client, db_session
    ):
        """不正なCSRFトークンは403を返す"""
        response = integration_client.post(
            "/api/summary/generate",
            json={"medical_text": _VALID_MEDICAL_TEXT},
            headers={"X-CSRF-Token": "totally-invalid-token"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_all_state_changing_endpoints_require_csrf(
        self, integration_client, db_session
    ):
        """すべての状態変更エンドポイントにCSRF保護が適用される"""
        for path, payload in _STATE_CHANGING_POSTS:
            res = integration_client.post(path, json=payload)
            assert res.status_code in (
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ), f"POST {path} should require CSRF token, got {res.status_code}"

    def test_expired_token_returns_403(
        self, integration_client, db_session
    ):
        """期限切れCSRFトークンは403を返す（タイムスタンプを2時間前に設定）"""
        # integration_clientのデフォルト設定はcsrf_token_expire_minutes=60
        # 2時間前のタイムスタンプで署名したトークンを作成すると有効期限超過になる
        old_timestamp = int(time.time()) - 7200  # 2時間前
        secret_key = INTEGRATION_CSRF_SECRET.encode()
        signature = hmac.new(
            secret_key, str(old_timestamp).encode(), hashlib.sha256
        ).hexdigest()
        expired_token = f"{old_timestamp}.{signature}"

        response = integration_client.post(
            "/api/summary/generate",
            json={"medical_text": _VALID_MEDICAL_TEXT},
            headers={"X-CSRF-Token": expired_token},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_endpoint_requires_csrf(
        self, integration_client, db_session, csrf_headers
    ):
        """DELETEエンドポイントもCSRFトークンが必要"""
        # プロンプトを作成
        create_res = integration_client.post(
            "/api/prompts/",
            json={
                "department": "内科",
                "document_type": "退院時サマリ",
                "doctor": "default",
                "content": "テスト",
            },
            headers=csrf_headers,
        )
        prompt_id = create_res.json()["id"]

        # CSRFトークンなしで削除 → 401
        del_res = integration_client.delete(f"/api/prompts/{prompt_id}")
        assert del_res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_valid_token_allows_request(
        self, integration_client, db_session, csrf_headers
    ):
        """有効なCSRFトークンを持つリクエストは許可される"""
        with patch(
            "app.services.summary_service.generate_summary_with_provider",
            return_value=("生成テキスト", 100, 50),
        ):
            response = integration_client.post(
                "/api/summary/generate",
                json={
                    "medical_text": _VALID_MEDICAL_TEXT,
                    "model": "Claude",
                    "model_explicitly_selected": True,
                },
                headers=csrf_headers,
            )
        assert response.status_code == status.HTTP_200_OK


class TestSecurityHeaders:
    def test_get_response_has_security_headers(
        self, integration_client, db_session
    ):
        """GETレスポンスにセキュリティヘッダーが付与される"""
        response = integration_client.get("/api/statistics/summary")
        assert response.status_code == status.HTTP_200_OK

        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("x-xss-protection") == "1; mode=block"
        assert "content-security-policy" in response.headers

    def test_post_response_has_security_headers(
        self, integration_client, db_session, csrf_headers
    ):
        """POSTレスポンスにもセキュリティヘッダーが付与される"""
        with patch(
            "app.services.summary_service.generate_summary_with_provider",
            return_value=("テキスト", 100, 50),
        ):
            response = integration_client.post(
                "/api/summary/generate",
                json={
                    "medical_text": _VALID_MEDICAL_TEXT,
                    "model": "Claude",
                    "model_explicitly_selected": True,
                },
                headers=csrf_headers,
            )

        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"

    def test_csp_header_denies_framing(
        self, integration_client, db_session
    ):
        """Content-Security-PolicyにフレームへのアクセスなしのDirectiveが含まれる"""
        response = integration_client.get("/api/settings/departments")
        csp = response.headers.get("content-security-policy", "")
        assert "frame-ancestors 'none'" in csp


class TestXSSProtection:
    def test_script_tags_sanitized_before_ai_call(
        self, integration_client, db_session, csrf_headers
    ):
        """XSSタグを含む入力がAIに渡される前にサニタイズされる"""
        text_with_xss = (
            "患者は60歳男性。"
            "<script>alert('xss')</script>"
            "糖尿病にて長期加療中。血糖値コントロール不良の状態が続いている。"
        )
        captured: dict = {}

        def capture_generate(**kwargs):
            captured["medical_text"] = kwargs.get("medical_text", "")
            return "生成テキスト", 100, 50

        with patch(
            "app.services.summary_service.generate_summary_with_provider",
            side_effect=capture_generate,
        ):
            response = integration_client.post(
                "/api/summary/generate",
                json={
                    "medical_text": text_with_xss,
                    "model": "Claude",
                    "model_explicitly_selected": True,
                },
                headers=csrf_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True
        assert "<script>" not in captured.get("medical_text", "")

    def test_iframe_tags_sanitized(
        self, integration_client, db_session, csrf_headers
    ):
        """iframeタグを含む入力がサニタイズされる"""
        text_with_iframe = (
            "患者情報テキスト。"
            "<iframe src='http://evil.com'></iframe>"
            "詳細な病歴情報が続く。入院加療後に状態が改善した。"
        )
        captured: dict = {}

        def capture_generate(**kwargs):
            captured["medical_text"] = kwargs.get("medical_text", "")
            return "生成テキスト", 100, 50

        with patch(
            "app.services.summary_service.generate_summary_with_provider",
            side_effect=capture_generate,
        ):
            integration_client.post(
                "/api/summary/generate",
                json={
                    "medical_text": text_with_iframe,
                    "model": "Claude",
                    "model_explicitly_selected": True,
                },
                headers=csrf_headers,
            )

        assert "<iframe" not in captured.get("medical_text", "")
