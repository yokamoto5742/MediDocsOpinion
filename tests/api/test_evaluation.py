from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status


@pytest.fixture
def mock_evaluation_prompt():
    """モックEvaluationPrompt"""
    prompt = MagicMock()
    prompt.id = 1
    prompt.document_type = "他院への紹介"
    prompt.content = "評価プロンプト内容"
    prompt.is_active = True
    prompt.created_at = datetime(2025, 1, 1, 12)
    prompt.updated_at = datetime(2025, 1, 2, 12)
    return prompt


def test_get_all_evaluation_prompts(client, test_db, mock_evaluation_prompt):
    """全プロンプト取得API - 正常系"""
    with patch(
        "app.api.evaluation.evaluation_prompt_service.get_all_evaluation_prompts"
    ) as mock_get_all:
        mock_get_all.return_value = [mock_evaluation_prompt]

        response = client.get("/api/evaluation/prompts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["prompts"]) == 1
        assert data["prompts"][0]["id"] == 1
        assert data["prompts"][0]["document_type"] == "他院への紹介"
        assert data["prompts"][0]["content"] == "評価プロンプト内容"
        assert data["prompts"][0]["is_active"] is True


def test_get_all_evaluation_prompts_empty(client, test_db):
    """全プロンプト取得API - 空リスト"""
    with patch(
        "app.api.evaluation.evaluation_prompt_service.get_all_evaluation_prompts"
    ) as mock_get_all:
        mock_get_all.return_value = []

        response = client.get("/api/evaluation/prompts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["prompts"]) == 0


def test_get_evaluation_prompt_exists(client, test_db, mock_evaluation_prompt):
    """特定プロンプト取得API - 存在する場合"""
    with patch(
        "app.api.evaluation.evaluation_prompt_service.get_evaluation_prompt"
    ) as mock_get:
        mock_get.return_value = mock_evaluation_prompt

        response = client.get("/api/evaluation/prompts/他院への紹介")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert data["document_type"] == "他院への紹介"
        assert data["content"] == "評価プロンプト内容"
        assert data["is_active"] is True


def test_get_evaluation_prompt_not_exists(client, test_db):
    """特定プロンプト取得API - 存在しない場合"""
    with patch(
        "app.api.evaluation.evaluation_prompt_service.get_evaluation_prompt"
    ) as mock_get:
        mock_get.return_value = None

        response = client.get("/api/evaluation/prompts/返書")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] is None
        assert data["document_type"] == "返書"
        assert data["content"] is None
        assert data["is_active"] is False


def test_save_evaluation_prompt_new(client, test_db, csrf_headers):
    """プロンプト保存API - 新規作成"""
    with patch(
        "app.api.evaluation.evaluation_prompt_service.create_or_update_evaluation_prompt"
    ) as mock_save:
        mock_save.return_value = (True, "評価プロンプトを新規作成しました")

        payload = {
            "document_type": "他院への紹介",
            "content": "新しい評価プロンプト",
        }

        response = client.post(
            "/api/evaluation/prompts", json=payload, headers=csrf_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "評価プロンプトを新規作成しました"
        assert data["document_type"] == "他院への紹介"


def test_save_evaluation_prompt_update(client, test_db, csrf_headers):
    """プロンプト保存API - 更新"""
    with patch(
        "app.api.evaluation.evaluation_prompt_service.create_or_update_evaluation_prompt"
    ) as mock_save:
        mock_save.return_value = (True, "評価プロンプトを更新しました")

        payload = {
            "document_type": "他院への紹介",
            "content": "更新された評価プロンプト",
        }

        response = client.post(
            "/api/evaluation/prompts", json=payload, headers=csrf_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "評価プロンプトを更新しました"
        assert data["document_type"] == "他院への紹介"


def test_save_evaluation_prompt_empty_content(client, test_db, csrf_headers):
    """プロンプト保存API - 空の内容"""
    with patch(
        "app.api.evaluation.evaluation_prompt_service.create_or_update_evaluation_prompt"
    ) as mock_save:
        mock_save.return_value = (False, "評価プロンプトの内容を入力してください")

        payload = {
            "document_type": "他院への紹介",
            "content": "",
        }

        response = client.post(
            "/api/evaluation/prompts", json=payload, headers=csrf_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "評価プロンプトの内容を入力してください"


def test_delete_evaluation_prompt_success(client, test_db, csrf_headers):
    """プロンプト削除API - 正常系"""
    with patch(
        "app.api.evaluation.evaluation_prompt_service.delete_evaluation_prompt"
    ) as mock_delete:
        mock_delete.return_value = (True, "評価プロンプトを削除しました")

        response = client.delete(
            "/api/evaluation/prompts/他院への紹介", headers=csrf_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "評価プロンプトを削除しました"
        assert data["document_type"] == "他院への紹介"


def test_delete_evaluation_prompt_not_found(client, test_db, csrf_headers):
    """プロンプト削除API - 存在しない場合"""
    with patch(
        "app.api.evaluation.evaluation_prompt_service.delete_evaluation_prompt"
    ) as mock_delete:
        mock_delete.return_value = (False, "返書の評価プロンプトが見つかりません")

        response = client.delete("/api/evaluation/prompts/返書", headers=csrf_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert "見つかりません" in data["message"]


def test_evaluate_output_missing_required_field(client, test_db, csrf_headers):
    """評価実行API - 必須フィールド不足"""
    payload = {
        "document_type": "他院への紹介",
        # input_text が欠落
        "output_summary": "出力内容",
    }

    response = client.post(
        "/api/evaluation/evaluate-stream", json=payload, headers=csrf_headers
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # 検証に失敗したフィールド名はクライアントに返さない
    assert "input_text" not in response.text


def test_save_evaluation_prompt_missing_required_field(client, test_db, csrf_headers):
    """プロンプト保存API - 必須フィールド不足"""
    payload = {
        "document_type": "他院への紹介",
        # content が欠落
    }

    response = client.post(
        "/api/evaluation/prompts", json=payload, headers=csrf_headers
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # 検証に失敗したフィールド名はクライアントに返さない
    assert "content" not in response.text


def test_evaluate_output_stream_success(client, test_db, csrf_headers):
    """SSEストリーミング評価API - 正常系"""

    def mock_stream():
        yield 'event: progress\ndata: {"status": "evaluating", "message": "評価中..."}\n\n'
        yield 'event: complete\ndata: {"success": true, "evaluation_result": "評価結果: 良好です", "input_tokens": 1000, "output_tokens": 500, "processing_time": 2.5}\n\n'

    with patch(
        "app.api.evaluation.execute_evaluation_stream", return_value=mock_stream()
    ):
        payload = {
            "document_type": "他院への紹介",
            "input_text": "患者は60歳男性。2型糖尿病にて加療中。",
            "current_prescription": "メトホルミン500mg",
            "additional_info": "HbA1c 7.5%",
            "output_summary": "主病名: 糖尿病\n治療経過: インスリン治療中",
        }

        response = client.post(
            "/api/evaluation/evaluate-stream", json=payload, headers=csrf_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


def test_evaluate_output_stream_error(client, test_db, csrf_headers):
    """SSEストリーミング評価API - エラー"""

    def mock_stream():
        yield 'event: error\ndata: {"success": false, "error_message": "評価対象の出力がありません"}\n\n'

    with patch(
        "app.api.evaluation.execute_evaluation_stream", return_value=mock_stream()
    ):
        payload = {
            "document_type": "他院への紹介",
            "input_text": "患者情報",
            "current_prescription": "",
            "additional_info": "",
            "output_summary": "",
        }

        response = client.post(
            "/api/evaluation/evaluate-stream", json=payload, headers=csrf_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


def test_non_streaming_endpoint_is_removed(client, test_db, csrf_headers):
    """非ストリーミングの評価APIは廃止済み"""
    payload = {
        "document_type": "主治医意見書",
        "input_text": "患者情報",
        "output_summary": "出力内容",
    }

    response = client.post("/api/evaluation/evaluate", json=payload, headers=csrf_headers)

    assert response.status_code in (
        status.HTTP_404_NOT_FOUND,
        status.HTTP_405_METHOD_NOT_ALLOWED,
    )
