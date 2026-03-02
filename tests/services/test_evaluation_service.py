import pytest
from unittest.mock import MagicMock, patch

from app.core.constants import MESSAGES
from app.services.evaluation_service import (
    build_evaluation_prompt,
    execute_evaluation,
    execute_evaluation_stream,
)


class TestBuildEvaluationPrompt:
    """build_evaluation_prompt 関数のテスト"""

    def test_build_evaluation_prompt(self):
        """評価プロンプト構築 - 正常系"""
        prompt_template = "以下の出力を評価してください。"
        input_text = "患者は60歳男性。"
        current_prescription = "メトホルミン500mg"
        additional_info = "HbA1c 7.5%"
        output_summary = "主病名: 糖尿病"

        result = build_evaluation_prompt(
            prompt_template,
            input_text,
            current_prescription,
            additional_info,
            output_summary
        )

        assert prompt_template in result
        assert "【カルテ記載】" in result
        assert input_text in result
        assert "【現在の処方】" in result
        assert current_prescription in result
        assert "【追加情報】" in result
        assert additional_info in result
        assert "【生成された出力】" in result
        assert output_summary in result

    def test_build_evaluation_prompt_empty_fields(self):
        """評価プロンプト構築 - 空のフィールド"""
        prompt_template = "評価してください"
        result = build_evaluation_prompt(
            prompt_template, "", "", "", "出力内容"
        )

        assert prompt_template in result
        assert "【カルテ記載】" in result
        assert "【生成された出力】" in result
        assert "出力内容" in result


class TestExecuteEvaluation:
    """execute_evaluation 関数のテスト"""

    @patch("app.services.evaluation_service.GeminiAPIClient")
    @patch("app.services.evaluation_service.get_db_session")
    @patch("app.services.evaluation_service.settings")
    def test_execute_evaluation_success(
        self, mock_settings, mock_get_db_session, mock_client_class
    ):
        """評価実行 - 正常系"""
        mock_settings.gemini_evaluation_model = "gemini-2.0-flash-thinking-exp-01-21"
        mock_settings.max_input_tokens = 100000

        # モックDB
        mock_db = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db

        # モックプロンプト
        mock_prompt = MagicMock()
        mock_prompt.content = "評価プロンプト"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_prompt

        # モッククライアント
        mock_client = MagicMock()
        mock_client._generate_content.return_value = (
            "評価結果: 良好です",
            1000,
            500
        )
        mock_client_class.return_value = mock_client

        result = execute_evaluation(
            document_type="他院への紹介",
            input_text="患者情報",
            current_prescription="処方内容",
            additional_info="追加情報",
            output_summary="出力内容"
        )

        assert result.success is True
        assert result.evaluation_result == "評価結果: 良好です"
        assert result.input_tokens == 1000
        assert result.output_tokens == 500
        assert result.processing_time >= 0
        assert result.error_message is None

        mock_client.initialize.assert_called_once()
        mock_client._generate_content.assert_called_once()

    @patch("app.services.evaluation_service.settings")
    def test_execute_evaluation_no_output(self, mock_settings):
        """評価実行 - 出力なしエラー"""
        result = execute_evaluation(
            document_type="他院への紹介",
            input_text="患者情報",
            current_prescription="",
            additional_info="",
            output_summary=""
        )

        assert result.success is False
        assert result.error_message == MESSAGES["VALIDATION"]["EVALUATION_NO_OUTPUT"]
        assert result.input_tokens == 0
        assert result.output_tokens == 0

    @patch("app.services.evaluation_service.settings")
    def test_execute_evaluation_model_missing(self, mock_settings):
        """評価実行 - モデル未設定エラー"""
        mock_settings.gemini_evaluation_model = None
        mock_settings.max_input_tokens = 100000

        result = execute_evaluation(
            document_type="他院への紹介",
            input_text="患者情報",
            current_prescription="",
            additional_info="",
            output_summary="出力内容"
        )

        assert result.success is False
        assert result.error_message == MESSAGES["CONFIG"]["EVALUATION_MODEL_MISSING"]
        assert result.input_tokens == 0
        assert result.output_tokens == 0

    @patch("app.services.evaluation_service.get_db_session")
    @patch("app.services.evaluation_service.settings")
    def test_execute_evaluation_prompt_not_set(
        self, mock_settings, mock_get_db_session
    ):
        """評価実行 - プロンプト未設定エラー"""
        mock_settings.gemini_evaluation_model = "gemini-2.0-flash-thinking-exp-01-21"
        mock_settings.max_input_tokens = 100000

        # モックDB
        mock_db = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = execute_evaluation(
            document_type="他院への紹介",
            input_text="患者情報",
            current_prescription="",
            additional_info="",
            output_summary="出力内容"
        )

        assert result.success is False
        assert "他院への紹介" in result.error_message
        assert "評価プロンプトが設定されていません" in result.error_message
        assert result.input_tokens == 0
        assert result.output_tokens == 0

    @patch("app.services.evaluation_service.GeminiAPIClient")
    @patch("app.services.evaluation_service.get_db_session")
    @patch("app.services.evaluation_service.settings")
    def test_execute_evaluation_api_error(
        self, mock_settings, mock_get_db_session, mock_client_class
    ):
        """評価実行 - API呼び出しエラー"""
        mock_settings.gemini_evaluation_model = "gemini-2.0-flash-thinking-exp-01-21"
        mock_settings.max_input_tokens = 100000

        # モックDB
        mock_db = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db

        # モックプロンプト
        mock_prompt = MagicMock()
        mock_prompt.content = "評価プロンプト"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_prompt

        # モッククライアントでエラー
        from app.utils.exceptions import APIError

        mock_client = MagicMock()
        mock_client._generate_content.side_effect = APIError("API接続エラー")
        mock_client_class.return_value = mock_client

        result = execute_evaluation(
            document_type="他院への紹介",
            input_text="患者情報",
            current_prescription="",
            additional_info="",
            output_summary="出力内容"
        )

        assert result.success is False
        assert "API接続エラー" in result.error_message
        assert result.input_tokens == 0
        assert result.output_tokens == 0

    @patch("app.services.evaluation_service.GeminiAPIClient")
    @patch("app.services.evaluation_service.get_db_session")
    @patch("app.services.evaluation_service.settings")
    def test_execute_evaluation_general_exception(
        self, mock_settings, mock_get_db_session, mock_client_class
    ):
        """評価実行 - 一般的な例外"""
        mock_settings.gemini_evaluation_model = "gemini-2.0-flash-thinking-exp-01-21"
        mock_settings.max_input_tokens = 100000

        # モックDB
        mock_db = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db

        # モックプロンプト
        mock_prompt = MagicMock()
        mock_prompt.content = "評価プロンプト"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_prompt

        # モッククライアントで例外
        mock_client = MagicMock()
        mock_client._generate_content.side_effect = Exception("予期しないエラー")
        mock_client_class.return_value = mock_client

        result = execute_evaluation(
            document_type="他院への紹介",
            input_text="患者情報",
            current_prescription="",
            additional_info="",
            output_summary="出力内容"
        )

        assert result.success is False
        assert "評価中にエラーが発生しました" in result.error_message
        assert "予期しないエラー" in result.error_message
        assert result.input_tokens == 0
        assert result.output_tokens == 0

    @patch("app.services.evaluation_service.GeminiAPIClient")
    @patch("app.services.evaluation_service.get_db_session")
    @patch("app.services.evaluation_service.settings")
    def test_execute_evaluation_with_all_fields(
        self, mock_settings, mock_get_db_session, mock_client_class
    ):
        """評価実行 - 全フィールド指定"""
        mock_settings.gemini_evaluation_model = "gemini-2.0-flash-thinking-exp-01-21"
        mock_settings.max_input_tokens = 100000

        # モックDB
        mock_db = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db

        # モックプロンプト
        mock_prompt = MagicMock()
        mock_prompt.content = "詳細な評価プロンプト"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_prompt

        # モッククライアント
        mock_client = MagicMock()
        mock_client._generate_content.return_value = (
            "詳細な評価結果",
            2000,
            1000
        )
        mock_client_class.return_value = mock_client

        # 繰り返しパターンではない長いテキストを生成
        long_input_text = "患者は" + "".join([
            f"{i}日前から症状{i}を訴えており、検査値{i}は{100+i}でした。"
            for i in range(50)
        ])

        result = execute_evaluation(
            document_type="他院への紹介",
            input_text=long_input_text,
            current_prescription="複数の処方薬",
            additional_info="詳細な追加情報",
            output_summary="詳細な出力内容"
        )

        assert result.success is True
        assert result.evaluation_result == "詳細な評価結果"
        assert result.input_tokens == 2000
        assert result.output_tokens == 1000

        # build_evaluation_prompt が正しく呼ばれたことを確認
        call_args = mock_client._generate_content.call_args[0][0]
        assert "詳細な評価プロンプト" in call_args
        assert "【カルテ記載】" in call_args
        assert "【現在の処方】" in call_args
        assert "【追加情報】" in call_args
        assert "【生成された出力】" in call_args


class TestExecuteEvaluationStream:
    """execute_evaluation_stream 関数のテスト"""

    @pytest.mark.asyncio
    @patch("app.services.evaluation_service._run_sync_evaluation")
    @patch("app.services.evaluation_service.get_db_session")
    @patch("app.services.evaluation_service.settings")
    async def test_execute_evaluation_stream_success(
        self, mock_settings, mock_get_db_session, mock_run_sync
    ):
        """評価ストリーミング実行 - 正常系"""
        mock_settings.gemini_evaluation_model = "gemini-2.0-flash-thinking-exp-01-21"
        mock_settings.max_input_tokens = 100000

        # モックDB
        mock_db = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db

        # モックプロンプト
        mock_prompt = MagicMock()
        mock_prompt.content = "評価プロンプト"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_prompt

        # モック評価結果
        mock_run_sync.return_value = ("評価結果: 良好です", 1000, 500)

        events = []
        async for event in execute_evaluation_stream(
            document_type="他院への紹介",
            input_text="患者情報",
            current_prescription="処方内容",
            additional_info="追加情報",
            output_summary="出力内容"
        ):
            events.append(event)

        # イベント検証
        assert len(events) >= 3  # progress, progress, complete
        assert "event: progress" in events[0]
        assert "event: complete" in events[-1]
        assert "評価結果: 良好です" in events[-1]
        assert '"input_tokens": 1000' in events[-1]
        assert '"output_tokens": 500' in events[-1]

    @pytest.mark.asyncio
    @patch("app.services.evaluation_service.settings")
    async def test_execute_evaluation_stream_no_output(self, mock_settings):
        """評価ストリーミング実行 - 出力なしエラー"""
        events = []
        async for event in execute_evaluation_stream(
            document_type="他院への紹介",
            input_text="患者情報",
            current_prescription="",
            additional_info="",
            output_summary=""
        ):
            events.append(event)

        assert len(events) == 1
        assert "event: error" in events[0]
        assert MESSAGES["VALIDATION"]["EVALUATION_NO_OUTPUT"] in events[0]

    @pytest.mark.asyncio
    @patch("app.services.evaluation_service.settings")
    async def test_execute_evaluation_stream_model_missing(self, mock_settings):
        """評価ストリーミング実行 - モデル未設定エラー"""
        mock_settings.gemini_evaluation_model = None
        mock_settings.max_input_tokens = 100000

        events = []
        async for event in execute_evaluation_stream(
            document_type="他院への紹介",
            input_text="患者情報",
            current_prescription="",
            additional_info="",
            output_summary="出力内容"
        ):
            events.append(event)

        assert len(events) == 1
        assert "event: error" in events[0]
        assert MESSAGES["CONFIG"]["EVALUATION_MODEL_MISSING"] in events[0]

    @pytest.mark.asyncio
    @patch("app.services.evaluation_service.get_db_session")
    @patch("app.services.evaluation_service.settings")
    async def test_execute_evaluation_stream_prompt_not_set(
        self, mock_settings, mock_get_db_session
    ):
        """評価ストリーミング実行 - プロンプト未設定エラー"""
        mock_settings.gemini_evaluation_model = "gemini-2.0-flash-thinking-exp-01-21"
        mock_settings.max_input_tokens = 100000

        # モックDB
        mock_db = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        events = []
        async for event in execute_evaluation_stream(
            document_type="他院への紹介",
            input_text="患者情報",
            current_prescription="",
            additional_info="",
            output_summary="出力内容"
        ):
            events.append(event)

        assert len(events) == 1
        assert "event: error" in events[0]
        assert "他院への紹介" in events[0]
        assert "評価プロンプトが設定されていません" in events[0]

    @pytest.mark.asyncio
    @patch("app.services.evaluation_service._run_sync_evaluation")
    @patch("app.services.evaluation_service.get_db_session")
    @patch("app.services.evaluation_service.settings")
    async def test_execute_evaluation_stream_api_error(
        self, mock_settings, mock_get_db_session, mock_run_sync
    ):
        """評価ストリーミング実行 - API呼び出しエラー"""
        mock_settings.gemini_evaluation_model = "gemini-2.0-flash-thinking-exp-01-21"
        mock_settings.max_input_tokens = 100000

        # モックDB
        mock_db = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db

        # モックプロンプト
        mock_prompt = MagicMock()
        mock_prompt.content = "評価プロンプト"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_prompt

        # モックでエラー
        mock_run_sync.side_effect = Exception("API接続エラー")

        events = []
        async for event in execute_evaluation_stream(
            document_type="他院への紹介",
            input_text="患者情報",
            current_prescription="",
            additional_info="",
            output_summary="出力内容"
        ):
            events.append(event)

        # progressイベントとerrorイベント
        assert any("event: error" in e for e in events)
        error_event = [e for e in events if "event: error" in e][0]
        assert "API接続エラー" in error_event
