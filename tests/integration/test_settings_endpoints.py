"""統合テスト: 設定エンドポイント"""
from fastapi import status

from app.core.constants import DEFAULT_DEPARTMENT, DOCUMENT_TYPES
from app.models.prompt import Prompt


class TestSettingsEndpoints:
    def test_departments_returns_constant_list(
        self, integration_client, db_session
    ):
        """診療科一覧が定数値から返される"""
        response = integration_client.get("/api/settings/departments")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "departments" in data
        assert data["departments"] == DEFAULT_DEPARTMENT

    def test_document_types_returns_constant_list(
        self, integration_client, db_session
    ):
        """文書タイプ一覧が定数値から返される"""
        response = integration_client.get("/api/settings/document-types")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "document_types" in data
        assert data["document_types"] == DOCUMENT_TYPES

    def test_doctors_for_default_department(
        self, integration_client, db_session
    ):
        """defaultの医師一覧が返される"""
        response = integration_client.get("/api/settings/doctors/default")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "doctors" in data
        assert "default" in data["doctors"]

    def test_doctors_for_unknown_department_returns_default(
        self, integration_client, db_session
    ):
        """未知の診療科は["default"]を返す"""
        response = integration_client.get("/api/settings/doctors/存在しない科")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["doctors"] == ["default"]

    def test_selected_model_with_matching_prompt(
        self, integration_client, db_session
    ):
        """DBのプロンプトにモデルが設定されている場合にそのモデルが返される"""
        db_session.add(Prompt(
            department="消化器内科",
            doctor="default",
            document_type="退院時サマリ",
            content="消化器内科用プロンプト",
            selected_model="Gemini_Pro",
        ))
        db_session.commit()

        response = integration_client.get(
            "/api/settings/selected-model",
            params={
                "department": "消化器内科",
                "document_type": "退院時サマリ",
                "doctor": "default",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["selected_model"] == "Gemini_Pro"

    def test_selected_model_without_prompt_returns_null(
        self, integration_client, db_session
    ):
        """DBにプロンプトが存在しない場合はnullが返される"""
        response = integration_client.get(
            "/api/settings/selected-model",
            params={
                "department": "整形外科",
                "document_type": "退院時サマリ",
                "doctor": "default",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["selected_model"] is None

    def test_selected_model_without_model_set_returns_null(
        self, integration_client, db_session
    ):
        """プロンプトは存在するがselected_model未設定の場合はnullが返される"""
        db_session.add(Prompt(department="眼科", doctor="default", document_type="退院時サマリ",
                              content="眼科プロンプト（モデル未設定）"))
        db_session.commit()

        response = integration_client.get(
            "/api/settings/selected-model",
            params={
                "department": "眼科",
                "document_type": "退院時サマリ",
                "doctor": "default",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["selected_model"] is None
