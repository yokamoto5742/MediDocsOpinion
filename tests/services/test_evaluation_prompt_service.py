from unittest.mock import MagicMock

from app.core.constants import MESSAGES
from app.services.evaluation_prompt_service import (
    create_or_update_evaluation_prompt,
    delete_evaluation_prompt,
    get_all_evaluation_prompts,
    get_evaluation_prompt,
)


class TestGetEvaluationPrompt:
    """get_evaluation_prompt 関数のテスト"""

    def test_get_evaluation_prompt_exists(self):
        """評価プロンプト取得 - 存在する場合"""
        mock_db = MagicMock()
        mock_prompt = MagicMock()
        mock_prompt.document_type = "他院への紹介"
        mock_prompt.content = "評価プロンプト内容"
        mock_prompt.is_active = True

        mock_db.query.return_value.filter.return_value.first.return_value = mock_prompt

        result = get_evaluation_prompt(mock_db, "他院への紹介")

        assert result is mock_prompt
        assert result.document_type == "他院への紹介"

    def test_get_evaluation_prompt_not_exists(self):
        """評価プロンプト取得 - 存在しない場合"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = get_evaluation_prompt(mock_db, "返書")

        assert result is None


class TestGetAllEvaluationPrompts:
    """get_all_evaluation_prompts 関数のテスト"""

    def test_get_all_evaluation_prompts(self):
        """全評価プロンプト取得 - 正常系"""
        mock_db = MagicMock()
        mock_prompts = [
            MagicMock(document_type="他院への紹介"),
            MagicMock(document_type="返書"),
        ]

        mock_db.query.return_value.order_by.return_value.all.return_value = mock_prompts

        result = get_all_evaluation_prompts(mock_db)

        assert len(result) == 2
        assert result[0].document_type == "他院への紹介"
        assert result[1].document_type == "返書"

    def test_get_all_evaluation_prompts_empty(self):
        """全評価プロンプト取得 - 空リスト"""
        mock_db = MagicMock()
        mock_db.query.return_value.order_by.return_value.all.return_value = []

        result = get_all_evaluation_prompts(mock_db)

        assert len(result) == 0


class TestCreateOrUpdateEvaluationPrompt:
    """create_or_update_evaluation_prompt 関数のテスト"""

    def test_create_evaluation_prompt_new(self):
        """評価プロンプト作成 - 新規作成"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        success, message = create_or_update_evaluation_prompt(
            mock_db, "他院への紹介", "新しい評価プロンプト"
        )

        assert success is True
        assert message == MESSAGES["SUCCESS"]["EVALUATION_PROMPT_CREATED"]
        mock_db.add.assert_called_once()

        # 追加されたプロンプトを検証
        added_prompt = mock_db.add.call_args[0][0]
        assert added_prompt.document_type == "他院への紹介"
        assert added_prompt.content == "新しい評価プロンプト"
        assert added_prompt.is_active is True

    def test_create_evaluation_prompt_update(self):
        """評価プロンプト作成 - 更新"""
        mock_db = MagicMock()
        mock_existing = MagicMock()
        mock_existing.content = "古いプロンプト"
        mock_existing.is_active = False

        mock_db.query.return_value.filter.return_value.first.return_value = mock_existing

        success, message = create_or_update_evaluation_prompt(
            mock_db, "他院への紹介", "更新されたプロンプト"
        )

        assert success is True
        assert message == MESSAGES["SUCCESS"]["EVALUATION_PROMPT_UPDATED"]
        assert mock_existing.content == "更新されたプロンプト"
        assert mock_existing.is_active is True
        mock_db.add.assert_not_called()

    def test_create_evaluation_prompt_empty_content(self):
        """評価プロンプト作成 - 空の内容"""
        mock_db = MagicMock()

        success, message = create_or_update_evaluation_prompt(
            mock_db, "他院への紹介", ""
        )

        assert success is False
        assert message == "評価プロンプトの内容を入力してください"
        mock_db.add.assert_not_called()


class TestDeleteEvaluationPrompt:
    """delete_evaluation_prompt 関数のテスト"""

    def test_delete_evaluation_prompt_success(self):
        """評価プロンプト削除 - 正常系"""
        mock_db = MagicMock()
        mock_prompt = MagicMock()
        mock_prompt.document_type = "他院への紹介"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_prompt

        success, message = delete_evaluation_prompt(mock_db, "他院への紹介")

        assert success is True
        assert message == MESSAGES["SUCCESS"]["EVALUATION_PROMPT_DELETED"]
        mock_db.delete.assert_called_once_with(mock_prompt)

    def test_delete_evaluation_prompt_not_found(self):
        """評価プロンプト削除 - 存在しない場合"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        success, message = delete_evaluation_prompt(mock_db, "返書")

        assert success is False
        assert message == "返書の評価プロンプトが見つかりません"
        mock_db.delete.assert_not_called()
