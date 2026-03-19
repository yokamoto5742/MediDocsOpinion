from unittest.mock import patch

import pytest
from fastapi import status

from app.schemas.summary import SummaryResponse


@pytest.fixture
def mock_summary_result_success():
    """成功時のSummaryResponse"""
    return SummaryResponse(
        success=True,
        output_summary="主病名: 糖尿病\n治療経過: インスリン治療中",
        parsed_summary={
            "主病名": "糖尿病",
            "治療経過": "インスリン治療中"
        },
        input_tokens=1000,
        output_tokens=500,
        processing_time=2.5,
        model_used="Claude",
        model_switched=False,
    )


@pytest.fixture
def mock_summary_result_failure():
    """失敗時のSummaryResponse"""
    return SummaryResponse(
        success=False,
        output_summary="",
        parsed_summary={},
        input_tokens=0,
        output_tokens=0,
        processing_time=0,
        model_used="Claude",
        model_switched=False,
        error_message="カルテ情報を入力してください",
    )


@pytest.fixture
def mock_summary_result_model_switched():
    """モデル切り替え時のSummaryResponse"""
    return SummaryResponse(
        success=True,
        output_summary="主病名: 高血圧症",
        parsed_summary={"主病名": "高血圧症"},
        input_tokens=50000,
        output_tokens=1000,
        processing_time=5.0,
        model_used="Gemini_Pro",
        model_switched=True,
    )


def test_generate_summary_success(client, test_db, csrf_headers, mock_summary_result_success):
    """文書生成API - 正常系"""
    with patch("app.api.summary.execute_summary_generation") as mock_execute:
        mock_execute.return_value = mock_summary_result_success

        payload = {
            "medical_text": "患者は60歳男性。2型糖尿病にて加療中。",
            "additional_info": "HbA1c 7.5%",
            "current_prescription": "メトホルミン500mg",
            "department": "default",
            "doctor": "default",
            "document_type": "他院への紹介",
            "model": "Claude",
            "model_explicitly_selected": False,
        }

        response = client.post("/api/summary/generate", json=payload, headers=csrf_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["output_summary"] == "主病名: 糖尿病\n治療経過: インスリン治療中"
        assert data["parsed_summary"]["主病名"] == "糖尿病"
        assert data["input_tokens"] == 1000
        assert data["output_tokens"] == 500
        assert data["processing_time"] == 2.5
        assert data["model_used"] == "Claude"
        assert data["model_switched"] is False
        assert data["error_message"] is None

        mock_execute.assert_called_once()


def test_generate_summary_validation_error(client, test_db, csrf_headers, mock_summary_result_failure):
    """文書生成API - 検証エラー"""
    with patch("app.api.summary.execute_summary_generation") as mock_execute:
        mock_execute.return_value = mock_summary_result_failure

        # 空文字列はPydanticでバリデーションエラー（422）になるため、
        # サービス層でのバリデーションエラーをテストするには短い文字列を使用
        payload = {
            "medical_text": "短",  # 非常に短い入力
            "additional_info": "",
            "current_prescription": "",
            "department": "default",
            "doctor": "default",
            "document_type": "他院への紹介",
            "model": "Claude",
            "model_explicitly_selected": False,
        }

        response = client.post("/api/summary/generate", json=payload, headers=csrf_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert data["error_message"] is not None
        assert data["input_tokens"] == 0
        assert data["output_tokens"] == 0


def test_generate_summary_model_switched(client, test_db, csrf_headers, mock_summary_result_model_switched):
    """文書生成API - モデル自動切り替え"""
    with patch("app.api.summary.execute_summary_generation") as mock_execute:
        mock_execute.return_value = mock_summary_result_model_switched

        # 長い入力テキスト（40,000文字超を想定）
        long_text = "患者情報: " + "X" * 45000

        payload = {
            "medical_text": long_text,
            "additional_info": "",
            "current_prescription": "",
            "department": "default",
            "doctor": "default",
            "document_type": "他院への紹介",
            "model": "Claude",
            "model_explicitly_selected": False,
        }

        response = client.post("/api/summary/generate", json=payload, headers=csrf_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["model_used"] == "Gemini_Pro"
        assert data["model_switched"] is True


def test_generate_summary_missing_required_field(client, test_db, csrf_headers):
    """文書生成API - 必須フィールド不足"""
    payload = {
        "additional_info": "追加情報",
        # medical_text が欠落
    }

    response = client.post("/api/summary/generate", json=payload, headers=csrf_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "medical_text" in response.text.lower()


def test_generate_summary_all_optional_fields(client, test_db, csrf_headers, mock_summary_result_success):
    """文書生成API - オプションフィールドすべて省略"""
    with patch("app.api.summary.execute_summary_generation") as mock_execute:
        mock_execute.return_value = mock_summary_result_success

        payload = {
            "medical_text": "患者は40歳女性。",
        }

        response = client.post("/api/summary/generate", json=payload, headers=csrf_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

        # デフォルト値が使用されることを確認
        call_args = mock_execute.call_args[1]
        assert call_args["additional_info"] == ""
        assert call_args["department"] == "default"
        assert call_args["doctor"] == "default"
        assert call_args["document_type"] == "退院時サマリ"
        assert call_args["model"] == "Claude"


def test_get_available_models_claude_only(client, test_db):
    """利用可能モデル取得 - Claude のみ"""
    with patch("app.api.summary.settings") as mock_settings:
        mock_settings.anthropic_model = "claude-3-5-sonnet-20241022"
        mock_settings.claude_api_key = "test-key"
        mock_settings.gemini_model = None

        response = client.get("/api/summary/models")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["available_models"] == ["Claude"]
        assert data["default_model"] == "Claude"


def test_get_available_models_gemini_only(client, test_db):
    """利用可能モデル取得 - Gemini のみ"""
    with patch("app.api.summary.settings") as mock_settings:
        mock_settings.anthropic_model = None
        mock_settings.claude_api_key = None
        mock_settings.gemini_model = "gemini-1.5-pro-002"

        response = client.get("/api/summary/models")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["available_models"] == ["Gemini_Pro"]
        assert data["default_model"] == "Gemini_Pro"


def test_get_available_models_both(client, test_db):
    """利用可能モデル取得 - 両方"""
    with patch("app.api.summary.settings") as mock_settings:
        mock_settings.anthropic_model = "claude-3-5-sonnet-20241022"
        mock_settings.claude_api_key = "test-key"
        mock_settings.gemini_model = "gemini-1.5-pro-002"

        response = client.get("/api/summary/models")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "Claude" in data["available_models"]
        assert "Gemini_Pro" in data["available_models"]
        assert data["default_model"] == "Claude"


def test_get_available_models_none(client, test_db):
    """利用可能モデル取得 - なし"""
    with patch("app.api.summary.settings") as mock_settings:
        mock_settings.anthropic_model = None
        mock_settings.claude_api_key = None
        mock_settings.gemini_model = None

        response = client.get("/api/summary/models")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["available_models"] == []
        assert data["default_model"] is None


def test_generate_summary_with_exception(client, test_db, csrf_headers):
    """文書生成API - 例外処理"""
    with patch("app.api.summary.execute_summary_generation") as mock_execute:
        mock_execute.side_effect = Exception("予期しないエラー")

        payload = {
            "medical_text": "テストデータ",
        }

        # execute_summary_generation が例外を投げた場合、FastAPIが500エラーを返す
        with pytest.raises(Exception):
            client.post("/api/summary/generate", json=payload, headers=csrf_headers)


def test_generate_summary_model_explicitly_selected(client, test_db, csrf_headers, mock_summary_result_success):
    """文書生成API - モデルが明示的に選択された場合"""
    with patch("app.api.summary.execute_summary_generation") as mock_execute:
        mock_execute.return_value = mock_summary_result_success

        payload = {
            "medical_text": "患者データ",
            "model": "Gemini_Pro",
            "model_explicitly_selected": True,
        }

        response = client.post("/api/summary/generate", json=payload, headers=csrf_headers)

        assert response.status_code == status.HTTP_200_OK

        call_args = mock_execute.call_args[1]
        assert call_args["model"] == "Gemini_Pro"
        assert call_args["model_explicitly_selected"] is True
