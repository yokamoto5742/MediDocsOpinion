from fastapi import status


def test_get_departments(client, test_db):
    """診療科一覧取得 - 正常系"""
    response = client.get("/api/settings/departments")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "departments" in data
    assert isinstance(data["departments"], list)
    assert "default" in data["departments"]
    assert "眼科" in data["departments"]


def test_get_departments_returns_expected_structure(client, test_db):
    """診療科一覧取得 - レスポンス構造確認"""
    response = client.get("/api/settings/departments")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert list(data.keys()) == ["departments"]


def test_get_doctors_default_department(client, test_db):
    """医師一覧取得 - default診療科"""
    response = client.get("/api/settings/doctors/default")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "doctors" in data
    assert isinstance(data["doctors"], list)
    assert "default" in data["doctors"]
    # constants.pyのDEPARTMENT_DOCTORS_MAPPING["default"]に合わせる
    assert data["doctors"] == ["default"]


def test_get_doctors_specific_department(client, test_db):
    """医師一覧取得 - 眼科"""
    response = client.get("/api/settings/doctors/眼科")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "doctors" in data
    assert "default" in data["doctors"]
    assert "橋本義弘" in data["doctors"]


def test_get_doctors_unknown_department(client, test_db):
    """医師一覧取得 - 存在しない診療科"""
    response = client.get("/api/settings/doctors/存在しない診療科")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "doctors" in data
    # 存在しない診療科の場合、デフォルト値が返される
    assert data["doctors"] == ["default"]


def test_get_doctors_empty_department_name(client, test_db):
    """医師一覧取得 - 空の診療科名"""
    response = client.get("/api/settings/doctors/")

    # FastAPIがパスパラメータ不足でエラーを返す
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_doctors_special_characters(client, test_db):
    """医師一覧取得 - 特殊文字を含む診療科名"""
    # %2F はスラッシュとして解釈されパスが分割されるため404になる
    response = client.get("/api/settings/doctors/内科-外科")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # マッピングにない場合はデフォルトが返される
    assert data["doctors"] == ["default"]


def test_get_document_types(client, test_db):
    """文書タイプ一覧取得 - 正常系"""
    response = client.get("/api/settings/document-types")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "document_types" in data
    assert isinstance(data["document_types"], list)
    assert "他院への紹介" in data["document_types"]
    assert "紹介元への逆紹介" in data["document_types"]
    assert "返書" in data["document_types"]
    assert "最終返書" in data["document_types"]


def test_get_document_types_length(client, test_db):
    """文書タイプ一覧取得 - 件数確認"""
    response = client.get("/api/settings/document-types")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["document_types"]) == 4


def test_get_document_types_returns_expected_structure(client, test_db):
    """文書タイプ一覧取得 - レスポンス構造確認"""
    response = client.get("/api/settings/document-types")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert list(data.keys()) == ["document_types"]


def test_multiple_doctors_requests(client, test_db):
    """医師一覧取得 - 複数リクエスト"""
    # 複数の診療科について順次問い合わせ
    departments = ["default", "眼科"]

    for dept in departments:
        response = client.get(f"/api/settings/doctors/{dept}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "doctors" in data
        assert isinstance(data["doctors"], list)
        assert len(data["doctors"]) > 0


def test_all_endpoints_accessible(client, test_db):
    """すべてのエンドポイントにアクセス可能"""
    endpoints = [
        "/api/settings/departments",
        "/api/settings/doctors/default",
        "/api/settings/document-types",
    ]

    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK


def test_get_doctors_url_encoding(client, test_db):
    """医師一覧取得 - URLエンコーディング"""
    # 日本語をURLエンコードした場合
    response = client.get("/api/settings/doctors/%E7%9C%BC%E7%A7%91")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "doctors" in data
    assert "橋本義弘" in data["doctors"]


def test_settings_endpoints_no_authentication(client, test_db):
    """設定エンドポイントは認証不要"""
    # 認証なしでアクセス可能であることを確認
    response = client.get("/api/settings/departments")
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/api/settings/doctors/default")
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/api/settings/document-types")
    assert response.status_code == status.HTTP_200_OK


def test_get_selected_model_with_no_prompt(client, test_db):
    """選択モデル取得 - プロンプトが存在しない場合"""
    response = client.get(
        "/api/settings/selected-model",
        params={
            "department": "default",
            "document_type": "他院への紹介",
            "doctor": "default"
        }
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "selected_model" in data
    assert data["selected_model"] is None


def test_get_selected_model_with_prompt(client, test_db, sample_prompts):
    """選択モデル取得 - プロンプトが存在する場合"""
    test_prompt = sample_prompts[1]  # 眼科の橋本義弘のプロンプト
    response = client.get(
        "/api/settings/selected-model",
        params={
            "department": test_prompt.department,
            "document_type": test_prompt.document_type,
            "doctor": test_prompt.doctor
        }
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "selected_model" in data
    assert data["selected_model"] == test_prompt.selected_model


def test_get_selected_model_hierarchical_lookup(client, test_db):
    """選択モデル取得 - 階層的検索の確認"""
    from app.models.prompt import Prompt

    # 診療科レベルのプロンプトを作成
    dept_prompt = Prompt(
        department="眼科",
        document_type="他院への紹介",
        doctor="default",
        content="診療科レベルのプロンプト",
        selected_model="Gemini_Pro"
    )
    test_db.add(dept_prompt)
    test_db.commit()

    # 医師レベルのプロンプトがない場合、診療科レベルのモデルが返される
    response = client.get(
        "/api/settings/selected-model",
        params={
            "department": "眼科",
            "document_type": "他院への紹介",
            "doctor": "橋本義弘"
        }
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["selected_model"] == "Gemini_Pro"


def test_get_selected_model_missing_parameters(client, test_db):
    """選択モデル取得 - パラメータ不足"""
    response = client.get("/api/settings/selected-model")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
