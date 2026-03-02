"""CSRF認証のデバッグテスト"""
from fastapi.testclient import TestClient


def test_csrf_check(client: TestClient):
    """CSRF認証が動作しているか確認"""
    response = client.post(
        "/api/summary/generate",
        json={
            "medical_text": "test",
            "department": "内科",
            "document_type": "診療情報提供書",
        },
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print(f"Headers: {response.headers}")
