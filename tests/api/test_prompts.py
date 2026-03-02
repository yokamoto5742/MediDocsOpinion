from fastapi import status


def test_list_prompts_empty(client, test_db):
    """プロンプト一覧取得 - 空の場合"""
    response = client.get("/api/prompts/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_prompts(client, sample_prompts):
    """プロンプト一覧取得 - データありの場合"""
    response = client.get("/api/prompts/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    assert data[0]["department"] == "default"
    assert data[1]["department"] == "眼科"


def test_create_prompt_success(client, test_db, csrf_headers):
    """プロンプト作成 - 成功"""
    payload = {
        "department": "内科",
        "doctor": "田中医師",
        "document_type": "他院への紹介",
        "content": "新規プロンプト内容",
        "selected_model": "Claude",
    }
    response = client.post("/api/prompts/", json=payload, headers=csrf_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["department"] == "内科"
    assert data["doctor"] == "田中医師"
    assert data["content"] == "新規プロンプト内容"
    assert data["selected_model"] == "Claude"
    assert "id" in data


def test_create_prompt_updates_existing(client, sample_prompts, csrf_headers):
    """プロンプト作成 - 既存のプロンプトを更新"""
    payload = {
        "department": "眼科",
        "doctor": "橋本義弘",
        "document_type": "他院への紹介",
        "content": "更新されたプロンプト",
        "selected_model": "Gemini_Pro",
    }
    response = client.post("/api/prompts/", json=payload, headers=csrf_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["content"] == "更新されたプロンプト"
    assert data["selected_model"] == "Gemini_Pro"

    response = client.get("/api/prompts/")
    prompts = response.json()
    assert len(prompts) == 2


def test_delete_prompt_success(client, sample_prompts, csrf_headers):
    """プロンプト削除 - 成功"""
    prompt_id = sample_prompts[1].id
    response = client.delete(f"/api/prompts/{prompt_id}", headers=csrf_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "deleted"}

    response = client.get("/api/prompts/")
    prompts = response.json()
    assert len(prompts) == 1


def test_delete_prompt_not_found(client, test_db, csrf_headers):
    """プロンプト削除 - 存在しないID"""
    response = client.delete("/api/prompts/9999", headers=csrf_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()
