"""統合テスト: プロンプト管理（CRUD + 階層的解決）"""
from unittest.mock import patch

from fastapi import status

from app.models.prompt import Prompt

_BASE_PROMPT = {
    "department": "内科",
    "document_type": "退院時サマリ",
    "doctor": "田中一郎",
    "content": "内科用退院時サマリプロンプト",
    "selected_model": "Claude",
}

_VALID_MEDICAL_TEXT = (
    "患者は67歳男性。2型糖尿病、高血圧症の既往あり。"
    "今回は血糖コントロール不良にて入院加療後、状態改善し退院となった。"
)


class TestPromptCRUD:
    def test_create_and_retrieve(
        self, integration_client, db_session, csrf_headers
    ):
        """プロンプト作成後に取得できる"""
        create_res = integration_client.post(
            "/api/prompts/", json=_BASE_PROMPT, headers=csrf_headers
        )
        assert create_res.status_code == status.HTTP_200_OK
        prompt_id = create_res.json()["id"]

        get_res = integration_client.get(f"/api/prompts/{prompt_id}")
        assert get_res.status_code == status.HTTP_200_OK
        data = get_res.json()
        assert data["department"] == "内科"
        assert data["content"] == "内科用退院時サマリプロンプト"
        assert data["selected_model"] == "Claude"

    def test_update_via_re_post(
        self, integration_client, db_session, csrf_headers
    ):
        """同一キーで再POSTすると内容が更新される（重複作成されない）"""
        create_res = integration_client.post(
            "/api/prompts/", json=_BASE_PROMPT, headers=csrf_headers
        )
        prompt_id = create_res.json()["id"]

        updated = {**_BASE_PROMPT, "content": "更新後のプロンプト内容"}
        integration_client.post("/api/prompts/", json=updated, headers=csrf_headers)

        # 一覧は重複なし（PromptListItemにcontentなし）
        list_res = integration_client.get("/api/prompts/")
        assert len(list_res.json()) == 1

        # 内容はIDで個別取得して確認
        get_res = integration_client.get(f"/api/prompts/{prompt_id}")
        assert get_res.json()["content"] == "更新後のプロンプト内容"

    def test_delete_makes_404(
        self, integration_client, db_session, csrf_headers
    ):
        """削除後は404が返る"""
        create_res = integration_client.post(
            "/api/prompts/", json=_BASE_PROMPT, headers=csrf_headers
        )
        prompt_id = create_res.json()["id"]

        del_res = integration_client.delete(f"/api/prompts/{prompt_id}", headers=csrf_headers)
        assert del_res.status_code == status.HTTP_200_OK

        get_res = integration_client.get(f"/api/prompts/{prompt_id}")
        assert get_res.status_code == status.HTTP_404_NOT_FOUND

    def test_list_returns_all_prompts(
        self, integration_client, db_session, csrf_headers
    ):
        """複数プロンプトが一覧で取得できる"""
        for i in range(3):
            integration_client.post(
                "/api/prompts/",
                json={**_BASE_PROMPT, "department": f"科{i}", "doctor": f"医師{i}"},
                headers=csrf_headers,
            )

        list_res = integration_client.get("/api/prompts/")
        assert list_res.status_code == status.HTTP_200_OK
        assert len(list_res.json()) == 3


class TestHierarchicalPromptResolution:
    def test_specific_prompt_beats_department_default(
        self, integration_client, db_session, csrf_headers
    ):
        """診療科+医師固有プロンプトが診療科デフォルトより優先される"""
        # 診療科デフォルト（Gemini）
        db_session.add(Prompt(
            department="内科", doctor="default",
            document_type="退院時サマリ", content="内科デフォルト",
            selected_model="Gemini_Pro",
        ))
        # 医師固有（Claude）
        db_session.add(Prompt(
            department="内科", doctor="田中一郎",
            document_type="退院時サマリ", content="田中医師固有",
            selected_model="Claude",
        ))
        db_session.commit()

        res = integration_client.get(
            "/api/settings/selected-model",
            params={"department": "内科", "document_type": "退院時サマリ", "doctor": "田中一郎"},
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["selected_model"] == "Claude"

    def test_department_default_fallback(
        self, integration_client, db_session, csrf_headers
    ):
        """医師固有プロンプト未設定時は診療科デフォルトにフォールバック"""
        db_session.add(Prompt(
            department="内科", doctor="default",
            document_type="退院時サマリ", content="内科デフォルト",
            selected_model="Gemini_Pro",
        ))
        db_session.commit()

        res = integration_client.get(
            "/api/settings/selected-model",
            params={"department": "内科", "document_type": "退院時サマリ", "doctor": "山田二郎"},
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["selected_model"] == "Gemini_Pro"

    def test_global_default_fallback(
        self, integration_client, db_session, csrf_headers
    ):
        """診療科プロンプト未設定時はグローバルデフォルトにフォールバック"""
        db_session.add(Prompt(
            department="default", doctor="default",
            document_type="退院時サマリ", content="グローバル",
            selected_model="Claude",
        ))
        db_session.commit()

        res = integration_client.get(
            "/api/settings/selected-model",
            params={"department": "整形外科", "document_type": "退院時サマリ", "doctor": "鈴木三郎"},
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["selected_model"] == "Claude"

    def test_no_prompt_returns_null_model(
        self, integration_client, db_session, csrf_headers
    ):
        """プロンプト未設定時はselected_modelがnullを返す"""
        res = integration_client.get(
            "/api/settings/selected-model",
            params={"department": "眼科", "document_type": "退院時サマリ", "doctor": "default"},
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["selected_model"] is None

    def test_prompt_model_used_in_generation(
        self, integration_client, db_session, csrf_headers
    ):
        """プロンプトに設定されたモデルがサマリ生成で使用される"""
        db_session.add(Prompt(
            department="内科", doctor="default",
            document_type="退院時サマリ", content="内科プロンプト",
            selected_model="Gemini_Pro",
        ))
        db_session.commit()

        captured: dict = {}

        def capture_generate(**kwargs):
            captured["provider"] = kwargs.get("provider", "")
            return "生成テキスト", 100, 50

        with patch(
            "app.services.summary_service.generate_summary_with_provider",
            side_effect=capture_generate,
        ):
            response = integration_client.post(
                "/api/summary/generate",
                json={
                    "medical_text": _VALID_MEDICAL_TEXT,
                    "department": "内科",
                    "doctor": "default",
                    "document_type": "退院時サマリ",
                    "model": "Claude",
                    "model_explicitly_selected": False,
                },
                headers=csrf_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["model_used"] == "Gemini_Pro"


class TestEvaluationPromptCRUD:
    def test_full_crud_flow(
        self, integration_client, db_session, csrf_headers
    ):
        """評価プロンプトの作成・取得・更新・削除の一連フロー"""
        # 作成
        create_res = integration_client.post(
            "/api/evaluation/prompts",
            json={"document_type": "退院時サマリ", "content": "初期評価プロンプト"},
            headers=csrf_headers,
        )
        assert create_res.status_code == status.HTTP_200_OK
        assert create_res.json()["success"] is True

        # 取得
        get_res = integration_client.get("/api/evaluation/prompts/退院時サマリ")
        assert get_res.status_code == status.HTTP_200_OK
        assert get_res.json()["content"] == "初期評価プロンプト"

        # 更新（同一document_typeで再POST）
        update_res = integration_client.post(
            "/api/evaluation/prompts",
            json={"document_type": "退院時サマリ", "content": "更新後の評価プロンプト"},
            headers=csrf_headers,
        )
        assert update_res.status_code == status.HTTP_200_OK

        updated_get = integration_client.get("/api/evaluation/prompts/退院時サマリ")
        assert updated_get.json()["content"] == "更新後の評価プロンプト"

        # 削除
        del_res = integration_client.delete(
            "/api/evaluation/prompts/退院時サマリ", headers=csrf_headers
        )
        assert del_res.status_code == status.HTTP_200_OK
        assert del_res.json()["success"] is True

        # 削除後はcontent=None（APIは200を返すが内容なし）
        after_del = integration_client.get("/api/evaluation/prompts/退院時サマリ")
        assert after_del.status_code == status.HTTP_200_OK
        assert after_del.json()["content"] is None

    def test_list_all_evaluation_prompts(
        self, integration_client, db_session, csrf_headers
    ):
        """複数評価プロンプトが一覧取得できる（レスポンスは{"prompts": [...]}形式）"""
        for doc_type in ["退院時サマリ", "現病歴"]:
            integration_client.post(
                "/api/evaluation/prompts",
                json={"document_type": doc_type, "content": f"{doc_type}用評価プロンプト"},
                headers=csrf_headers,
            )

        list_res = integration_client.get("/api/evaluation/prompts")
        assert list_res.status_code == status.HTTP_200_OK
        prompts = list_res.json()["prompts"]
        assert len(prompts) == 2
        doc_types = {p["document_type"] for p in prompts}
        assert "退院時サマリ" in doc_types
        assert "現病歴" in doc_types
