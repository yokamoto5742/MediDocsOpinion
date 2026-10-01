from unittest.mock import patch

from fastapi import status

from app.core.constants import MESSAGES
from app.services.sse_helpers import sse_event

STREAM_URL = "/api/summary/generate-stream"


async def fake_stream(*_args, **_kwargs):
    """サービス層の代わりに complete イベントだけを返す"""
    yield sse_event("complete", {"success": True, "output_summary": "生成された文書"})


def test_generate_stream_passes_request_to_service(client, test_db, csrf_headers):
    """文書生成API - リクエストをそのままサービス層に渡し、SSEで返す"""
    payload = {
        "medical_text": "患者データ",
        "additional_info": "追加情報",
        "previous_text": "前回の記載",
        "department": "眼科",
        "doctor": "橋本義弘",
        "document_type": "訪問看護指示書",
        "model": "Gemini",
        "model_explicitly_selected": True,
        "previous_summary": "前回の文書",
        "evaluation_feedback": "指摘",
    }

    with patch(
        "app.api.summary.execute_summary_generation_stream", side_effect=fake_stream
    ) as mock_execute:
        response = client.post(STREAM_URL, json=payload, headers=csrf_headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert response.headers["x-accel-buffering"] == "no"
    assert "event: complete" in response.text

    request, user_ip = mock_execute.call_args[0]
    assert request.model_dump() == payload
    assert user_ip == "testclient"


def test_generate_stream_applies_defaults(client, test_db, csrf_headers):
    """文書生成API - 省略した項目には既定値が入る"""
    with patch(
        "app.api.summary.execute_summary_generation_stream", side_effect=fake_stream
    ) as mock_execute:
        response = client.post(
            STREAM_URL, json={"medical_text": "患者データ"}, headers=csrf_headers
        )

    assert response.status_code == status.HTTP_200_OK
    request = mock_execute.call_args[0][0]
    assert request.additional_info == ""
    assert request.department == "default"
    assert request.doctor == "default"
    assert request.document_type == "主治医意見書"
    assert request.model == "Claude"
    assert request.model_explicitly_selected is False


def test_generate_stream_missing_required_field(client, test_db, csrf_headers):
    """文書生成API - 必須フィールド欠落は 422 と定型メッセージ"""
    response = client.post(STREAM_URL, json={"department": "眼科"}, headers=csrf_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json() == {
        "success": False,
        "error_message": MESSAGES["ERROR"]["INPUT_ERROR"],
    }


def test_generate_stream_empty_medical_text(client, test_db, csrf_headers):
    """文書生成API - 空のカルテ情報は 422"""
    response = client.post(STREAM_URL, json={"medical_text": ""}, headers=csrf_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_generate_stream_requires_csrf_token(client, test_db):
    """文書生成API - CSRFトークンなしは 401"""
    response = client.post(STREAM_URL, json={"medical_text": "患者データ"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == MESSAGES["ERROR"]["CSRF_TOKEN_REQUIRED"]


def test_non_streaming_endpoint_is_removed(client, test_db, csrf_headers):
    """非ストリーミングの文書生成APIは廃止済み"""
    response = client.post(
        "/api/summary/generate", json={"medical_text": "患者データ"}, headers=csrf_headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_available_models_claude_only(client, test_db):
    """利用可能モデル取得 - Claude のみ"""
    with patch("app.services.model_selector.settings") as mock_settings:
        mock_settings.anthropic_model = "claude-3-5-sonnet-20241022"
        mock_settings.gemini_model = None

        response = client.get("/api/summary/models")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["available_models"] == ["Claude"]
        assert data["default_model"] == "Claude"


def test_get_available_models_gemini_only(client, test_db):
    """利用可能モデル取得 - Gemini のみ"""
    with patch("app.services.model_selector.settings") as mock_settings:
        mock_settings.anthropic_model = None
        mock_settings.gemini_model = "gemini-1.5-pro-002"

        response = client.get("/api/summary/models")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["available_models"] == ["Gemini"]
        assert data["default_model"] == "Gemini"


def test_get_available_models_both(client, test_db):
    """利用可能モデル取得 - 両方"""
    with patch("app.services.model_selector.settings") as mock_settings:
        mock_settings.anthropic_model = "claude-3-5-sonnet-20241022"
        mock_settings.gemini_model = "gemini-1.5-pro-002"

        response = client.get("/api/summary/models")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["available_models"] == ["Claude", "Gemini"]
        assert data["default_model"] == "Claude"


def test_get_available_models_none(client, test_db):
    """利用可能モデル取得 - なし"""
    with patch("app.services.model_selector.settings") as mock_settings:
        mock_settings.anthropic_model = None
        mock_settings.gemini_model = None

        response = client.get("/api/summary/models")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["available_models"] == []
        assert data["default_model"] is None
