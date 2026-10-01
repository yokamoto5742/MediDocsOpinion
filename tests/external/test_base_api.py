from unittest.mock import MagicMock, patch

import pytest

from app.core.constants import (
    DEFAULT_DOCUMENT_TYPE,
    GROUNDING_INSTRUCTION,
    KARTE_JSON_INSTRUCTION,
    REFINEMENT_INSTRUCTION,
)
from app.external.base_api import BaseAPIClient, _is_json_text
from app.schemas.summary import SummaryRequest
from app.utils.exceptions import APIError


class MockAPIClient(BaseAPIClient):
    """テスト用のモックAPIクライアント（呼び出し内容を記録する）"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def generate_content(
        self, prompt: str, model_name: str, system_prompt: str = ""
    ) -> tuple[str, int, int]:
        self.calls.append((prompt, model_name, system_prompt))
        return "生成されたテキスト", 1000, 500


@pytest.fixture
def mock_get_prompt():
    """DBのプロンプト取得をモックに差し替える（既定はプロンプト未登録）"""
    with (
        patch("app.external.base_api.get_db_session") as mock_db_session,
        patch("app.external.base_api.get_prompt") as mock,
    ):
        mock_db_session.return_value.__enter__.return_value = MagicMock()
        mock.return_value = None
        mock.db_session = mock_db_session
        yield mock


class TestCreateSummaryPrompt:
    """create_summary_prompt メソッドのテスト"""

    def test_create_summary_prompt_minimal(self, mock_get_prompt):
        """プロンプト生成 - 最小パラメータ"""
        system_prompt, user_message = MockAPIClient().create_summary_prompt(
            SummaryRequest(medical_text="患者情報")
        )

        assert "以下のカルテ情報を要約してください" in system_prompt
        assert GROUNDING_INSTRUCTION in system_prompt
        assert "<カルテ情報>" in user_message
        assert "患者情報" in user_message
        # 空のオプションフィールドのタグは追加されない
        assert "<前回の記載>" not in user_message
        assert "<追加情報>" not in user_message

    def test_create_summary_prompt_all_params(self, mock_get_prompt):
        """プロンプト生成 - 全パラメータ"""
        _, user_message = MockAPIClient().create_summary_prompt(
            SummaryRequest(
                medical_text="カルテデータ",
                additional_info="追加情報",
                previous_text="処方内容",
                department="眼科",
                document_type="他院への紹介",
                doctor="橋本義弘",
            )
        )

        assert "<カルテ情報>" in user_message
        assert "カルテデータ" in user_message
        assert "<前回の記載>" in user_message
        assert "処方内容" in user_message
        assert "<追加情報>" in user_message
        assert "追加情報" in user_message

    def test_create_summary_prompt_whitespace_optional_fields(self, mock_get_prompt):
        """プロンプト生成 - 空白のみのオプションフィールドはタグを追加しない"""
        _, user_message = MockAPIClient().create_summary_prompt(
            SummaryRequest(medical_text="データ", additional_info="   ", previous_text="\t")
        )

        assert "<前回の記載>" not in user_message
        assert "<追加情報>" not in user_message

    def test_create_summary_prompt_with_custom_prompt(self, mock_get_prompt):
        """プロンプト生成 - DBのカスタムプロンプトを使用"""
        mock_get_prompt.return_value = MagicMock(content="カスタムプロンプトテンプレート")

        system_prompt, user_message = MockAPIClient().create_summary_prompt(
            SummaryRequest(
                medical_text="データ",
                department="眼科",
                document_type="他院への紹介",
                doctor="橋本義弘",
            )
        )

        assert "カスタムプロンプトテンプレート" in system_prompt
        assert "データ" in user_message
        # 第1引数はdbセッション、第2-4引数はdepartment, document_type, doctor
        assert mock_get_prompt.call_args[0][1:] == ("眼科", "他院への紹介", "橋本義弘")

    def test_create_summary_prompt_default_lookup_keys(self, mock_get_prompt):
        """プロンプト生成 - 未指定の場合は既定の診療科・文書タイプ・医師で検索"""
        MockAPIClient().create_summary_prompt(SummaryRequest(medical_text="データ"))

        assert mock_get_prompt.call_args[0][1:] == ("default", DEFAULT_DOCUMENT_TYPE, "default")

    def test_create_summary_prompt_db_error_falls_back_to_default(self, mock_get_prompt):
        """プロンプト生成 - DBエラー時は既定のプロンプトで続行"""
        mock_get_prompt.db_session.side_effect = RuntimeError("DB接続エラー")

        system_prompt, user_message = MockAPIClient().create_summary_prompt(
            SummaryRequest(medical_text="テスト")
        )

        assert "以下のカルテ情報を要約してください" in system_prompt
        assert "テスト" in user_message

    def test_create_summary_prompt_json_karte(self, mock_get_prompt):
        """プロンプト生成 - JSON形式カルテはsystem promptに指示を追加"""
        json_text = '{"記載日": "2026-01-01", "経過": "良好"}'

        system_prompt, user_message = MockAPIClient().create_summary_prompt(
            SummaryRequest(medical_text=json_text)
        )

        assert KARTE_JSON_INSTRUCTION in system_prompt
        assert json_text in user_message

    def test_create_summary_prompt_non_json_karte(self, mock_get_prompt):
        """プロンプト生成 - 非JSONカルテにはJSON指示を追加しない"""
        system_prompt, _ = MockAPIClient().create_summary_prompt(
            SummaryRequest(medical_text="通常のカルテ記載")
        )

        assert KARTE_JSON_INSTRUCTION not in system_prompt

    def test_create_summary_prompt_refinement(self, mock_get_prompt):
        """プロンプト生成 - 前回の生成結果と評価結果を反映した再生成"""
        system_prompt, user_message = MockAPIClient().create_summary_prompt(
            SummaryRequest(
                medical_text="データ",
                previous_summary="前回の文書",
                evaluation_feedback="日付が誤っています",
            )
        )

        assert REFINEMENT_INSTRUCTION in system_prompt
        assert "<前回の生成結果>" in user_message
        assert "前回の文書" in user_message
        assert "<評価結果>" in user_message
        assert "日付が誤っています" in user_message

    def test_create_summary_prompt_refinement_requires_both(self, mock_get_prompt):
        """プロンプト生成 - 再生成は前回結果と評価結果の両方指定時のみ有効"""
        system_prompt, user_message = MockAPIClient().create_summary_prompt(
            SummaryRequest(medical_text="データ", previous_summary="前回の文書")
        )

        assert REFINEMENT_INSTRUCTION not in system_prompt
        assert "<前回の生成結果>" not in user_message

    def test_create_summary_prompt_very_long_medical_text(self, mock_get_prompt):
        """プロンプト生成 - 非常に長いカルテ情報"""
        long_text = "あ" * 100000

        _, user_message = MockAPIClient().create_summary_prompt(
            SummaryRequest(medical_text=long_text)
        )

        assert long_text in user_message

    def test_create_summary_prompt_special_characters(self, mock_get_prompt):
        """プロンプト生成 - 特殊文字を含むテキスト"""
        special_text = "特殊文字: \n\t\r\n!@#$%^&*(){}[]<>?/\\|`~"

        _, user_message = MockAPIClient().create_summary_prompt(
            SummaryRequest(medical_text=special_text)
        )

        assert special_text in user_message


class TestIsJsonText:
    """_is_json_text 関数のテスト"""

    def test_json_object(self):
        assert _is_json_text('{"key": "value"}') is True

    def test_json_array(self):
        assert _is_json_text('[{"key": "value"}]') is True

    def test_plain_text(self):
        assert _is_json_text("通常のカルテ記載") is False

    def test_json_scalar_not_treated_as_json(self):
        # 数値や文字列単体はJSONカルテとして扱わない
        assert _is_json_text("123") is False

    def test_empty_string(self):
        assert _is_json_text("") is False


class TestGenerateSummary:
    """generate_summary メソッドのテスト"""

    def test_generate_summary_passes_prompt_and_model(self, mock_get_prompt):
        """文書生成 - 組み立てたプロンプトとモデル名で generate_content を呼ぶ"""
        client = MockAPIClient()
        request = SummaryRequest(medical_text="患者情報", additional_info="追加情報")

        result = client.generate_summary(request, "custom-model")

        assert result == ("生成されたテキスト", 1000, 500)
        system_prompt, user_message = client.create_summary_prompt(request)
        assert client.calls == [(user_message, "custom-model", system_prompt)]

    def test_generate_summary_error_propagates(self, mock_get_prompt):
        """文書生成 - generate_content の例外はラップせずに伝播する"""
        client = MockAPIClient()

        with patch.object(client, "generate_content", side_effect=APIError("API呼び出し失敗")):
            with pytest.raises(APIError) as exc_info:
                client.generate_summary(SummaryRequest(medical_text="データ"), "test-model")

        assert str(exc_info.value) == "API呼び出し失敗"


class TestBaseAPIClientAbstractMethods:
    """BaseAPIClient 抽象メソッドのテスト"""

    def test_cannot_instantiate_base_class(self):
        """基底クラスは直接インスタンス化できない"""
        with pytest.raises(TypeError):
            BaseAPIClient()  # type: ignore[abstract]

    def test_subclass_must_implement_generate_content(self):
        """サブクラスは generate_content を実装する必要がある"""

        class IncompleteClient(BaseAPIClient):
            pass

        with pytest.raises(TypeError):
            IncompleteClient()  # type: ignore[abstract]
