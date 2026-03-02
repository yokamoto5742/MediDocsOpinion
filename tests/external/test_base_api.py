from unittest.mock import MagicMock, patch

import pytest

from app.core.constants import DEFAULT_DOCUMENT_TYPE
from app.external.base_api import BaseAPIClient
from app.utils.exceptions import APIError


class MockAPIClient(BaseAPIClient):
    """テスト用のモックAPIクライアント"""

    def __init__(self, api_key: str = "test_key", default_model: str = "test_model"):
        super().__init__(api_key, default_model)
        self.initialized = False

    def initialize(self) -> bool:
        """初期化をシミュレート"""
        self.initialized = True
        return True

    def _generate_content(self, prompt: str, model_name: str) -> tuple:
        """コンテンツ生成をシミュレート"""
        return "生成されたテキスト", 1000, 500


class TestBaseAPIClientInitialization:
    """BaseAPIClient 初期化のテスト"""

    def test_init_with_api_key_and_model(self):
        """初期化 - APIキーとデフォルトモデル指定"""
        client = MockAPIClient(api_key="test_api_key", default_model="test-model-v1")

        assert client.api_key == "test_api_key"
        assert client.default_model == "test-model-v1"

    def test_init_default_values(self):
        """初期化 - デフォルト値"""
        client = MockAPIClient()

        assert client.api_key == "test_key"
        assert client.default_model == "test_model"


class TestCreateSummaryPrompt:
    """create_summary_prompt メソッドのテスト"""

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_create_summary_prompt_minimal(self, mock_db_session, mock_get_prompt):
        """プロンプト生成 - 最小パラメータ"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_get_prompt.return_value = None

        client = MockAPIClient()
        prompt = client.create_summary_prompt(medical_text="患者情報")

        assert "以下のカルテ情報を要約してください" in prompt
        assert "【カルテ情報】" in prompt
        assert "患者情報" in prompt
        assert "【追加情報】" in prompt

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_create_summary_prompt_all_params(self, mock_db_session, mock_get_prompt):
        """プロンプト生成 - 全パラメータ"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_get_prompt.return_value = None

        client = MockAPIClient()
        prompt = client.create_summary_prompt(
            medical_text="カルテデータ",
            additional_info="追加情報",
            current_prescription="処方内容",
            department="眼科",
            document_type="他院への紹介",
            doctor="橋本義弘",
        )

        assert "【カルテ情報】" in prompt
        assert "カルテデータ" in prompt
        assert "【退院時処方(現在の処方)】" in prompt
        assert "処方内容" in prompt
        assert "【追加情報】追加情報" in prompt

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_create_summary_prompt_empty_optional_fields(
        self, mock_db_session, mock_get_prompt
    ):
        """プロンプト生成 - 空のオプションフィールド"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_get_prompt.return_value = None

        client = MockAPIClient()
        prompt = client.create_summary_prompt(medical_text="データ")

        assert "【カルテ情報】" in prompt
        assert "データ" in prompt
        assert "【退院時処方(現在の処方)】\n処方" not in prompt
        # 追加情報は空でも含まれる
        assert "【追加情報】" in prompt

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_create_summary_prompt_whitespace_optional_fields(
        self, mock_db_session, mock_get_prompt
    ):
        """プロンプト生成 - 空白のみのオプションフィールド"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_get_prompt.return_value = None

        client = MockAPIClient()
        prompt = client.create_summary_prompt(
            medical_text="データ",
            additional_info="   ",
            current_prescription="\t",
        )

        # 空白のみは strip() で空文字列になるため、ユーザーデータは追加されない
        assert "【退院時処方(現在の処方)】\n\t" not in prompt

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_create_summary_prompt_with_custom_prompt(self, mock_db_session, mock_get_prompt):
        """プロンプト生成 - カスタムプロンプト使用"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db

        mock_prompt = MagicMock()
        mock_prompt.content = "カスタムプロンプトテンプレート"
        mock_prompt.selected_model = "gemini-1.5-pro-002"
        mock_get_prompt.return_value = mock_prompt

        client = MockAPIClient()
        prompt = client.create_summary_prompt(
            medical_text="データ",
            department="眼科",
            document_type="他院への紹介",
            doctor="橋本義弘",
        )

        assert "カスタムプロンプトテンプレート" in prompt
        assert "【カルテ情報】" in prompt
        assert "データ" in prompt

        # get_prompt が呼ばれたことを確認
        assert mock_get_prompt.called
        call_args = mock_get_prompt.call_args[0]
        # 第1引数はdbセッション、第2-4引数はdepartment, document_type, doctor
        assert call_args[1] == "眼科"
        assert call_args[2] == "他院への紹介"
        assert call_args[3] == "橋本義弘"

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_create_summary_prompt_fallback_to_default(
        self, mock_db_session, mock_get_prompt
    ):
        """プロンプト生成 - デフォルトプロンプトへのフォールバック"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_get_prompt.return_value = None

        client = MockAPIClient()
        prompt = client.create_summary_prompt(medical_text="テスト", department="眼科", document_type="他院への紹介")

        # カスタムプロンプトがない場合はDEFAULT_SUMMARY_PROMPTを使用
        assert "以下のカルテ情報を要約してください" in prompt
        assert "【カルテ情報】" in prompt
        assert "テスト" in prompt

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_create_summary_prompt_default_document_type(
        self, mock_db_session, mock_get_prompt
    ):
        """プロンプト生成 - デフォルト文書タイプ使用"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_get_prompt.return_value = None

        client = MockAPIClient()
        prompt = client.create_summary_prompt(medical_text="データ")

        # get_promptが呼ばれ、DEFAULT_DOCUMENT_TYPEで呼ばれることを確認
        assert mock_get_prompt.called
        call_args = mock_get_prompt.call_args[0]
        assert call_args[1] == "default"
        assert call_args[2] == DEFAULT_DOCUMENT_TYPE
        assert call_args[3] == "default"
        # 生成されたプロンプトにカルテ情報が含まれることを確認
        assert "【カルテ情報】" in prompt
        assert "データ" in prompt


class TestGetModelName:
    """get_model_name メソッドのテスト"""

    @patch("app.external.base_api.get_selected_model")
    @patch("app.external.base_api.get_db_session")
    def test_get_model_name_from_prompt(self, mock_db_session, mock_get_selected_model):
        """モデル名取得 - プロンプトから"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db

        # get_selected_model がモデル名を返す
        mock_get_selected_model.return_value = "gemini-1.5-pro-002"

        client = MockAPIClient(default_model="claude-3-5-sonnet-20241022")
        model_name = client.get_model_name(
            department="眼科",
            document_type="他院への紹介",
            doctor="橋本義弘",
        )

        assert model_name == "gemini-1.5-pro-002"

    @patch("app.external.base_api.get_selected_model")
    @patch("app.external.base_api.get_db_session")
    def test_get_model_name_default_fallback(self, mock_db_session, mock_get_selected_model):
        """モデル名取得 - デフォルトへのフォールバック"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        # get_selected_model がNoneを返す（プロンプトが見つからない場合）
        mock_get_selected_model.return_value = None

        client = MockAPIClient(default_model="claude-3-5-sonnet-20241022")
        model_name = client.get_model_name(
            department="default",
            document_type="他院への紹介",
            doctor="default",
        )

        assert model_name == "claude-3-5-sonnet-20241022"

    @patch("app.external.base_api.get_selected_model")
    @patch("app.external.base_api.get_db_session")
    def test_get_model_name_no_selected_model_in_prompt(self, mock_db_session, mock_get_selected_model):
        """モデル名取得 - プロンプトにselected_modelがない"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db

        # get_selected_model がNoneを返す（selected_modelがない場合）
        mock_get_selected_model.return_value = None

        client = MockAPIClient(default_model="default-model")
        model_name = client.get_model_name(
            department="眼科",
            document_type="返書",
            doctor="default",
        )

        # selected_model がない場合はデフォルトを使用
        assert model_name == "default-model"

    @patch("app.external.base_api.get_selected_model")
    @patch("app.external.base_api.get_db_session")
    def test_get_model_name_empty_selected_model(self, mock_db_session, mock_get_selected_model):
        """モデル名取得 - selected_modelが空"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db

        # get_selected_model は空文字列の場合 None を返す（prompt_service.pyの実装）
        mock_get_selected_model.return_value = None

        client = MockAPIClient(default_model="default-model")
        model_name = client.get_model_name(
            department="default",
            document_type="他院への紹介",
            doctor="default",
        )

        # selected_model が空文字列の場合はget_selected_modelがNoneを返し、デフォルトモデルが使用される
        assert model_name == "default-model"


class TestGenerateSummary:
    """generate_summary メソッドのテスト"""

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_generate_summary_success(self, mock_db_session, mock_get_prompt):
        """文書生成 - 正常系"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_get_prompt.return_value = None

        client = MockAPIClient()
        result = client.generate_summary(medical_text="患者情報", additional_info="追加情報",
                                         current_prescription="処方",
                                         document_type="他院への紹介")

        assert result == ("生成されたテキスト", 1000, 500)
        assert client.initialized is True

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_generate_summary_with_model_name(self, mock_db_session, mock_get_prompt):
        """文書生成 - model_name 指定"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_get_prompt.return_value = None

        client = MockAPIClient()
        result = client.generate_summary(
            medical_text="データ",
            model_name="specified-model",
        )

        assert result == ("生成されたテキスト", 1000, 500)

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_generate_summary_without_model_name(self, mock_db_session, mock_get_prompt):
        """文書生成 - model_name なし（デフォルト使用）"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db

        mock_prompt = MagicMock()
        mock_prompt.content = "プロンプト"
        mock_prompt.selected_model = "gemini-1.5-pro-002"
        mock_get_prompt.return_value = mock_prompt

        client = MockAPIClient(default_model="default-model")
        result = client.generate_summary(
            medical_text="データ",
            department="眼科",
            document_type="他院への紹介",
            doctor="橋本義弘",
        )

        assert result == ("生成されたテキスト", 1000, 500)

    def test_generate_summary_initialize_failure(self):
        """文書生成 - 初期化失敗"""

        class FailingInitClient(MockAPIClient):
            def initialize(self) -> bool:
                raise APIError("初期化エラー")

        client = FailingInitClient()

        with pytest.raises(APIError) as exc_info:
            client.generate_summary(medical_text="データ")

        assert "初期化エラー" in str(exc_info.value)

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_generate_summary_generate_content_failure(
        self, mock_db_session, mock_get_prompt
    ):
        """文書生成 - コンテンツ生成失敗"""

        class FailingGenerateClient(MockAPIClient):
            def _generate_content(self, prompt: str, model_name: str) -> tuple:
                raise Exception("生成エラー")

        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_get_prompt.return_value = None

        client = FailingGenerateClient()

        with pytest.raises(APIError) as exc_info:
            client.generate_summary(medical_text="データ")

        assert "FailingGenerateClient" in str(exc_info.value)
        assert "生成エラー" in str(exc_info.value)

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_generate_summary_api_error_propagation(
        self, mock_db_session, mock_get_prompt
    ):
        """文書生成 - APIError の伝播"""

        class APIErrorClient(MockAPIClient):
            def _generate_content(self, prompt: str, model_name: str) -> tuple:
                raise APIError("API呼び出しエラー")

        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_get_prompt.return_value = None

        client = APIErrorClient()

        with pytest.raises(APIError) as exc_info:
            client.generate_summary(medical_text="データ")

        # APIError はそのまま伝播される
        assert "API呼び出しエラー" in str(exc_info.value)

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_generate_summary_minimal_params(self, mock_db_session, mock_get_prompt):
        """文書生成 - 最小パラメータ"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_get_prompt.return_value = None

        client = MockAPIClient()
        result = client.generate_summary(medical_text="最小データ")

        assert result == ("生成されたテキスト", 1000, 500)
        assert client.initialized is True


class TestBaseAPIClientAbstractMethods:
    """BaseAPIClient 抽象メソッドのテスト"""

    def test_cannot_instantiate_base_class(self):
        """BaseAPIClient を直接インスタンス化できない"""
        with pytest.raises(TypeError):
            BaseAPIClient(api_key="test", default_model="test")

    def test_subclass_must_implement_initialize(self):
        """サブクラスは initialize を実装する必要がある"""

        class IncompleteClient(BaseAPIClient):
            def _generate_content(self, prompt: str, model_name: str) -> tuple:
                return "text", 100, 50

        with pytest.raises(TypeError):
            IncompleteClient(api_key="test", default_model="test")

    def test_subclass_must_implement_generate_content(self):
        """サブクラスは _generate_content を実装する必要がある"""

        class IncompleteClient(BaseAPIClient):
            def initialize(self) -> bool:
                return True

        with pytest.raises(TypeError):
            IncompleteClient(api_key="test", default_model="test")


class TestBaseAPIClientEdgeCases:
    """BaseAPIClient のエッジケース"""

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_create_summary_prompt_very_long_medical_text(
        self, mock_db_session, mock_get_prompt
    ):
        """プロンプト生成 - 非常に長いカルテ情報"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_get_prompt.return_value = None

        long_text = "あ" * 100000
        client = MockAPIClient()
        prompt = client.create_summary_prompt(medical_text=long_text)

        assert "以下のカルテ情報を要約してください" in prompt
        assert long_text in prompt

    @patch("app.external.base_api.get_prompt")
    @patch("app.external.base_api.get_db_session")
    def test_create_summary_prompt_special_characters(
        self, mock_db_session, mock_get_prompt
    ):
        """プロンプト生成 - 特殊文字を含むテキスト"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_get_prompt.return_value = None

        special_text = "特殊文字: \n\t\r\n!@#$%^&*(){}[]<>?/\\|`~"
        client = MockAPIClient()
        prompt = client.create_summary_prompt(medical_text=special_text)

        assert special_text in prompt

    @patch("app.external.base_api.get_selected_model")
    @patch("app.external.base_api.get_db_session")
    def test_get_model_name_with_none_prompt(self, mock_db_session, mock_get_selected_model):
        """モデル名取得 - get_selected_model が None を返す"""
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        # get_selected_model がNoneを返す（プロンプトが見つからない場合）
        mock_get_selected_model.return_value = None

        client = MockAPIClient(default_model="fallback-model")
        model_name = client.get_model_name(
            department="default",
            document_type="他院への紹介",
            doctor="default",
        )

        assert model_name == "fallback-model"
