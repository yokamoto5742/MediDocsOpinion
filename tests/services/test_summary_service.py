from unittest.mock import MagicMock, patch

import pytest

from app.core.constants import MESSAGES
from app.services.model_selector import determine_model, get_provider_and_model
from app.services.summary_service import execute_summary_generation, validate_input
from app.services.usage_service import save_usage


class TestValidateInput:
    """validate_input 関数のテスト"""

    def test_validate_input_valid(self):
        """入力検証 - 正常系"""
        is_valid, error = validate_input("これは有効なカルテ情報です" * 10)
        assert is_valid is True
        assert error is None

    def test_validate_input_empty(self):
        """入力検証 - 空文字列"""
        is_valid, error = validate_input("")
        assert is_valid is False
        assert error == "カルテ情報を入力してください"

    def test_validate_input_whitespace_only(self):
        """入力検証 - 空白のみ"""
        is_valid, error = validate_input("   \n\t   ")
        assert is_valid is False
        assert error == "カルテ情報を入力してください"

    def test_validate_input_none(self):
        """入力検証 - None"""
        is_valid, error = validate_input(None)
        assert is_valid is False
        assert error == "カルテ情報を入力してください"

    @patch("app.services.summary_service.settings")
    def test_validate_input_too_short(self, mock_settings):
        """入力検証 - 短すぎる入力"""
        mock_settings.min_input_tokens = 100
        mock_settings.max_input_tokens = 100000

        is_valid, error = validate_input("短い")
        assert is_valid is False
        assert error == "入力文字数が少なすぎます"

    @patch("app.services.summary_service.settings")
    def test_validate_input_too_long(self, mock_settings):
        """入力検証 - 長すぎる入力"""
        mock_settings.min_input_tokens = 10
        mock_settings.max_input_tokens = 100

        is_valid, error = validate_input("あ" * 200)
        assert is_valid is False
        assert error == MESSAGES["VALIDATION"]["INPUT_TOO_LONG"]


class TestDetermineModel:
    """determine_model 関数のテスト"""

    @patch("app.services.model_selector.settings")
    def test_determine_model_below_threshold(self, mock_settings):
        """モデル決定 - 閾値以下"""
        mock_settings.max_token_threshold = 40000

        model, switched = determine_model(
            requested_model="Claude",
            input_length=10000,
            department="default",
            document_type="他院への紹介",
            doctor="default",
            model_explicitly_selected=True,
        )

        assert model == "Claude"
        assert switched is False

    @patch("app.services.model_selector.settings")
    def test_determine_model_above_threshold_with_gemini(self, mock_settings):
        """モデル決定 - 閾値超過、Gemini利用可能"""
        mock_settings.max_token_threshold = 40000
        mock_settings.gemini_model = "gemini-1.5-pro-002"

        model, switched = determine_model(
            requested_model="Claude",
            input_length=50000,
            department="default",
            document_type="他院への紹介",
            doctor="default",
            model_explicitly_selected=True,
        )

        assert model == "Gemini_Pro"
        assert switched is True

    @patch("app.services.model_selector.settings")
    def test_determine_model_above_threshold_no_gemini(self, mock_settings):
        """モデル決定 - 閾値超過、Gemini利用不可"""
        mock_settings.max_token_threshold = 40000
        mock_settings.gemini_model = None

        with pytest.raises(ValueError) as exc_info:
            determine_model(
                requested_model="Claude",
                input_length=50000,
                department="default",
                document_type="他院への紹介",
                doctor="default",
                model_explicitly_selected=True,
            )

        assert "入力が長すぎますが" in str(exc_info.value)
        assert "Geminiモデルが設定されていません" in str(exc_info.value)

    @patch("app.services.model_selector.settings")
    def test_determine_model_gemini_requested(self, mock_settings):
        """モデル決定 - Geminiが明示的に選択された"""
        mock_settings.max_token_threshold = 40000

        model, switched = determine_model(
            requested_model="Gemini_Pro",
            input_length=10000,
            department="default",
            document_type="他院への紹介",
            doctor="default",
            model_explicitly_selected=True,
        )

        assert model == "Gemini_Pro"
        assert switched is False

    @patch("app.services.prompt_service.get_prompt")
    @patch("app.core.database.get_db_session")
    @patch("app.services.model_selector.settings")
    def test_determine_model_from_prompt(self, mock_settings, mock_db_session, mock_get_prompt):
        """モデル決定 - プロンプトから取得"""
        from unittest.mock import MagicMock

        mock_settings.max_token_threshold = 40000

        # モックDBセッション
        mock_db = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_db

        # モックプロンプト
        mock_prompt = MagicMock()
        mock_prompt.selected_model = "Gemini_Pro"
        mock_get_prompt.return_value = mock_prompt

        model, switched = determine_model(requested_model="Claude", input_length=10000, department="眼科",
                                          document_type="他院への紹介", doctor="橋本義弘")

        # プロンプトで設定されたモデルが使用される
        assert model == "Gemini_Pro"
        assert switched is False


class TestGetProviderAndModel:
    """get_provider_and_model 関数のテスト"""

    @patch("app.services.model_selector.settings")
    def test_get_provider_and_model_claude(self, mock_settings):
        """プロバイダーとモデル取得 - Claude"""
        mock_settings.claude_model = "claude-3-5-sonnet-20241022"
        mock_settings.anthropic_model = None

        provider, model = get_provider_and_model("Claude")

        assert provider == "claude"
        assert model == "claude-3-5-sonnet-20241022"

    @patch("app.services.model_selector.settings")
    def test_get_provider_and_model_claude_anthropic_fallback(self, mock_settings):
        """プロバイダーとモデル取得 - Claude（anthropic_modelフォールバック）"""
        mock_settings.claude_model = None
        mock_settings.anthropic_model = "claude-3-opus-20240229"

        provider, model = get_provider_and_model("Claude")

        assert provider == "claude"
        assert model == "claude-3-opus-20240229"

    @patch("app.services.model_selector.settings")
    def test_get_provider_and_model_gemini(self, mock_settings):
        """プロバイダーとモデル取得 - Gemini"""
        mock_settings.gemini_model = "gemini-1.5-pro-002"

        provider, model = get_provider_and_model("Gemini_Pro")

        assert provider == "gemini"
        assert model == "gemini-1.5-pro-002"

    def test_get_provider_and_model_unsupported(self):
        """プロバイダーとモデル取得 - サポート外モデル"""
        with pytest.raises(ValueError) as exc_info:
            get_provider_and_model("GPT-4")

        assert "サポートされていないモデル" in str(exc_info.value)


class TestSaveUsage:
    """save_usage 関数のテスト"""

    @patch("app.services.usage_service.get_db_session")
    def test_save_usage_success(self, mock_get_db_session):
        """使用統計保存 - 正常系"""
        mock_db = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db

        save_usage(
            department="眼科",
            doctor="橋本義弘",
            document_type="他院への紹介",
            model="Claude",
            input_tokens=1000,
            output_tokens=500,
            processing_time=2.5,
        )

        # DBへの追加が呼ばれたことを確認
        mock_db.add.assert_called_once()

        # 追加されたUsageオブジェクトを検証
        added_usage = mock_db.add.call_args[0][0]
        assert added_usage.department == "眼科"
        assert added_usage.doctor == "橋本義弘"
        assert added_usage.document_type == "他院への紹介"
        assert added_usage.model == "Claude"
        assert added_usage.input_tokens == 1000
        assert added_usage.output_tokens == 500
        assert added_usage.app_type == "referral_letter"
        assert added_usage.processing_time == 2.5

    @patch("app.services.usage_service.get_db_session")
    @patch("logging.error")
    def test_save_usage_failure_silent(self, mock_logging_error, mock_get_db_session):
        """使用統計保存 - 失敗時にエラーを無視"""
        mock_db = MagicMock()
        mock_db.add.side_effect = Exception("DB接続エラー")
        mock_get_db_session.return_value.__enter__.return_value = mock_db

        # エラーが発生しても例外は投げられない
        save_usage(
            department="default",
            doctor="default",
            document_type="返書",
            model="Gemini_Pro",
            input_tokens=2000,
            output_tokens=800,
            processing_time=3.0,
        )

        # 警告メッセージが出力されることを確認
        mock_logging_error.assert_called_once()
        assert "使用統計の保存に失敗しました" in str(mock_logging_error.call_args)


class TestExecuteSummaryGeneration:
    """execute_summary_generation 関数のテスト"""

    @patch("app.services.summary_service.get_provider_and_model")
    @patch("app.services.summary_service.determine_model")
    @patch("app.services.summary_service.save_usage")
    @patch("app.services.summary_service.generate_summary_with_provider")
    @patch("app.services.summary_service.settings")
    def test_execute_summary_generation_success(
        self, mock_settings, mock_generate_summary_with_provider, mock_save_usage,
        mock_determine_model, mock_get_provider_and_model
    ):
        """文書生成実行 - 正常系"""
        mock_settings.min_input_tokens = 10
        mock_settings.max_input_tokens = 100000

        mock_determine_model.return_value = ("Claude", False)
        mock_get_provider_and_model.return_value = ("claude", "claude-3-5-sonnet-20241022")
        mock_generate_summary_with_provider.return_value = (
            "主病名: 糖尿病\n治療経過: インスリン治療中",
            1000,
            500,
        )

        result = execute_summary_generation(
            medical_text="患者は60歳男性。2型糖尿病にて加療中。",
            additional_info="HbA1c 7.5%",
            referral_purpose="血糖コントロール",
            current_prescription="メトホルミン500mg",
            department="default",
            doctor="default",
            document_type="他院への紹介",
            model="Claude",
            model_explicitly_selected=True,
        )

        assert result.success is True
        assert result.input_tokens == 1000
        assert result.output_tokens == 500
        assert result.model_used == "Claude"
        assert result.model_switched is False
        assert result.error_message is None
        assert result.processing_time >= 0  # モック時は非常に短い時間になる可能性がある

        # 使用統計が保存されたことを確認
        mock_save_usage.assert_called_once()

    @patch("app.services.summary_service.settings")
    def test_execute_summary_generation_validation_error(self, mock_settings):
        """文書生成実行 - 検証エラー"""
        mock_settings.min_input_tokens = 10
        mock_settings.max_input_tokens = 100000

        result = execute_summary_generation(
            medical_text="",  # 空文字列
            additional_info="",
            referral_purpose="",
            current_prescription="",
            department="default",
            doctor="default",
            document_type="他院への紹介",
            model="Claude",
            model_explicitly_selected=True,
        )

        assert result.success is False
        assert result.error_message == "カルテ情報を入力してください"
        assert result.input_tokens == 0
        assert result.output_tokens == 0
        assert result.processing_time == 0

    @patch("app.services.summary_service.determine_model")
    @patch("app.services.summary_service.settings")
    def test_execute_summary_generation_model_switch_error(self, mock_settings, mock_determine_model):
        """文書生成実行 - モデル切り替えエラー"""
        mock_settings.min_input_tokens = 10
        mock_settings.max_input_tokens = 100000

        mock_determine_model.side_effect = ValueError("入力が長すぎますがGeminiモデルが設定されていません")

        # 繰り返しパターンではない長いテキストを生成（各文を微妙に変化させる）
        long_text = "患者は" + "".join([
            f"{i}日前から咳と発熱を訴えており、血圧は{140+i}/{90+i}、脈拍は{88+i}回、体温は{37.8+i*0.1:.1f}度です。"
            for i in range(50)
        ])

        result = execute_summary_generation(
            medical_text=long_text,
            additional_info="",
            referral_purpose="",
            current_prescription="",
            department="default",
            doctor="default",
            document_type="他院への紹介",
            model="Claude",
            model_explicitly_selected=True,
        )

        assert result.success is False
        assert "入力が長すぎますが" in result.error_message
        assert "Geminiモデルが設定されていません" in result.error_message

    @patch("app.services.summary_service.settings")
    def test_execute_summary_generation_unsupported_model(self, mock_settings):
        """文書生成実行 - サポート外モデル"""
        mock_settings.min_input_tokens = 10
        mock_settings.max_input_tokens = 100000
        mock_settings.max_token_threshold = 40000

        result = execute_summary_generation(
            medical_text="テストデータ" * 10,
            additional_info="",
            referral_purpose="",
            current_prescription="",
            department="default",
            doctor="default",
            document_type="他院への紹介",
            model="GPT-4",  # サポート外
            model_explicitly_selected=True,
        )

        assert result.success is False
        assert "サポートされていないモデル" in result.error_message

    @patch("app.services.summary_service.get_provider_and_model")
    @patch("app.services.summary_service.determine_model")
    @patch("app.services.summary_service.save_usage")
    @patch("app.services.summary_service.generate_summary_with_provider")
    @patch("app.services.summary_service.settings")
    def test_execute_summary_generation_api_error(
        self, mock_settings, mock_generate_summary_with_provider, mock_save_usage,
        mock_determine_model, mock_get_provider_and_model
    ):
        """文書生成実行 - API呼び出しエラー"""
        mock_settings.min_input_tokens = 10
        mock_settings.max_input_tokens = 100000

        mock_determine_model.return_value = ("Claude", False)
        mock_get_provider_and_model.return_value = ("claude", "claude-3-5-sonnet-20241022")
        mock_generate_summary_with_provider.side_effect = Exception("API接続エラー")

        result = execute_summary_generation(
            medical_text="テストデータ" * 10,
            additional_info="",
            referral_purpose="",
            current_prescription="",
            department="default",
            doctor="default",
            document_type="他院への紹介",
            model="Claude",
            model_explicitly_selected=True,
        )

        assert result.success is False
        assert result.error_message == "API接続エラー"
        assert result.input_tokens == 0
        assert result.output_tokens == 0

        # エラー時は使用統計を保存しない
        mock_save_usage.assert_not_called()

    @patch("app.services.summary_service.get_provider_and_model")
    @patch("app.services.summary_service.determine_model")
    @patch("app.services.summary_service.save_usage")
    @patch("app.services.summary_service.generate_summary_with_provider")
    @patch("app.services.summary_service.settings")
    def test_execute_summary_generation_with_model_switch(
        self, mock_settings, mock_generate_summary_with_provider, mock_save_usage,
        mock_determine_model, mock_get_provider_and_model
    ):
        """文書生成実行 - モデル自動切り替え"""
        mock_settings.min_input_tokens = 10
        mock_settings.max_input_tokens = 100000

        mock_determine_model.return_value = ("Gemini_Pro", True)
        mock_get_provider_and_model.return_value = ("gemini", "gemini-1.5-pro-002")
        mock_generate_summary_with_provider.return_value = (
            "主病名: 高血圧症",
            50000,
            1000,
        )

        # 繰り返しパターンではない長いテキストを生成（各文を微妙に変化させる）
        long_text = "患者は" + "".join([
            f"{i}日前から咳と発熱を訴えており、血圧は{140+i}/{90+i}、脈拍は{88+i}回、体温は{37.8+i*0.1:.1f}度です。"
            for i in range(50)
        ])

        result = execute_summary_generation(
            medical_text=long_text,
            additional_info="",
            referral_purpose="",
            current_prescription="",
            department="default",
            doctor="default",
            document_type="他院への紹介",
            model="Claude",
            model_explicitly_selected=True,
        )

        assert result.success is True
        assert result.model_used == "Gemini_Pro"
        assert result.model_switched is True

    @patch("app.services.summary_service.get_provider_and_model")
    @patch("app.services.summary_service.determine_model")
    @patch("app.services.summary_service.save_usage")
    @patch("app.services.summary_service.generate_summary_with_provider")
    @patch("app.services.summary_service.settings")
    def test_execute_summary_generation_with_additional_info(
        self, mock_settings, mock_generate_summary_with_provider, mock_save_usage,
        mock_determine_model, mock_get_provider_and_model
    ):
        """文書生成実行 - 追加情報あり"""
        mock_settings.min_input_tokens = 10
        mock_settings.max_input_tokens = 100000

        mock_determine_model.return_value = ("Claude", False)
        mock_get_provider_and_model.return_value = ("claude", "claude-3-5-sonnet-20241022")
        mock_generate_summary_with_provider.return_value = (
            "主病名: 糖尿病",
            1500,
            600,
        )

        result = execute_summary_generation(
            medical_text="患者データ" * 10,
            additional_info="追加情報" * 10,
            referral_purpose="精査依頼",
            current_prescription="処方内容",
            department="眼科",
            doctor="橋本義弘",
            document_type="他院への紹介",
            model="Claude",
            model_explicitly_selected=True,
        )

        assert result.success is True
        # generate_summary が正しい引数で呼ばれることを確認
        call_args = mock_generate_summary_with_provider.call_args[1]
        assert call_args["additional_info"] == "追加情報" * 10
        assert call_args["referral_purpose"] == "精査依頼"
        assert call_args["current_prescription"] == "処方内容"
        assert call_args["department"] == "眼科"
        assert call_args["doctor"] == "橋本義弘"

    @patch("app.services.summary_service.get_provider_and_model")
    @patch("app.services.summary_service.determine_model")
    @patch("app.services.summary_service.save_usage")
    @patch("app.services.summary_service.generate_summary_with_provider")
    @patch("app.services.summary_service.parse_output_summary")
    @patch("app.services.summary_service.format_output_summary")
    @patch("app.services.summary_service.settings")
    def test_execute_summary_generation_output_formatting(
        self,
        mock_settings,
        mock_format,
        mock_parse,
        mock_generate_summary_with_provider,
        mock_save_usage,
        mock_determine_model,
        mock_get_provider_and_model,
    ):
        """文書生成実行 - 出力フォーマット処理"""
        mock_settings.min_input_tokens = 10
        mock_settings.max_input_tokens = 100000

        mock_determine_model.return_value = ("Claude", False)
        mock_get_provider_and_model.return_value = ("claude", "claude-3-5-sonnet-20241022")
        mock_generate_summary_with_provider.return_value = (
            "# 主病名: 糖尿病",
            1000,
            500,
        )
        mock_format.return_value = "主病名: 糖尿病"
        mock_parse.return_value = {"主病名": "糖尿病"}

        result = execute_summary_generation(
            medical_text="テストデータ" * 10,
            additional_info="",
            referral_purpose="",
            current_prescription="",
            department="default",
            doctor="default",
            document_type="他院への紹介",
            model="Claude",
            model_explicitly_selected=True,
        )

        assert result.success is True
        assert result.output_summary == "主病名: 糖尿病"
        assert result.parsed_summary == {"主病名": "糖尿病"}

        # フォーマット処理が呼ばれたことを確認
        mock_format.assert_called_once_with("# 主病名: 糖尿病")
        mock_parse.assert_called_once_with("主病名: 糖尿病")
