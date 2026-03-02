from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_csrf_token():
    return "test-csrf-token"


def test_generate_summary_stream_success(client, mock_csrf_token):
    """SSEストリーミング文書生成API - 正常系"""

    def mock_stream():
        yield 'event: progress\ndata: {"status": "generating", "message": "文書を生成中..."}\n\n'
        yield 'event: complete\ndata: {"success": true, "output_summary": "生成された文書", "parsed_summary": {}, "input_tokens": 100, "output_tokens": 200, "processing_time": 1.5, "model_used": "Claude", "model_switched": false}\n\n'

    with patch("app.api.summary.execute_summary_generation_stream", return_value=mock_stream()):
        with patch("app.core.security.verify_csrf_token", return_value=True):
            response = client.post(
                "/api/summary/generate-stream",
                json={
                    "medical_text": "患者は60歳男性",
                    "additional_info": "",
                    "referral_purpose": "",
                    "current_prescription": "",
                    "department": "default",
                    "doctor": "default",
                    "document_type": "他院への紹介",
                    "model": "Claude",
                    "model_explicitly_selected": True
                },
                headers={"X-CSRF-Token": mock_csrf_token}
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


def test_generate_summary_stream_csrf_required(client):
    """SSEストリーミングAPI - CSRF認証必須"""
    response = client.post(
        "/api/summary/generate-stream",
        json={
            "medical_text": "患者は60歳男性",
            "model": "Claude"
        }
    )

    # CSRF認証がないため401が返る
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
