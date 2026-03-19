import json
from unittest.mock import patch

from app.utils.audit_logger import log_audit_event


class TestLogAuditEvent:
    """log_audit_event 関数のテスト"""

    def test_required_fields_always_present(self):
        """timestamp, event_type, success は常に記録される"""
        with patch("app.utils.audit_logger.audit_logger") as mock_logger:
            log_audit_event(event_type="test_event")

            mock_logger.info.assert_called_once()
            logged = json.loads(mock_logger.info.call_args[0][0])

        assert "timestamp" in logged
        assert logged["event_type"] == "test_event"
        assert logged["success"] is True

    def test_success_false_is_recorded(self):
        """success=False が正しく記録される"""
        with patch("app.utils.audit_logger.audit_logger") as mock_logger:
            log_audit_event(event_type="error_event", success=False)
            logged = json.loads(mock_logger.info.call_args[0][0])

        assert logged["success"] is False

    def test_optional_fields_excluded_when_none(self):
        """user_ip, document_type, model, error_message は None の場合に含まれない"""
        with patch("app.utils.audit_logger.audit_logger") as mock_logger:
            log_audit_event(event_type="test_event")
            logged = json.loads(mock_logger.info.call_args[0][0])

        assert "user_ip" not in logged
        assert "document_type" not in logged
        assert "model" not in logged
        assert "error_message" not in logged

    def test_user_ip_included_when_provided(self):
        """user_ip が指定された場合に含まれる"""
        with patch("app.utils.audit_logger.audit_logger") as mock_logger:
            log_audit_event(event_type="test_event", user_ip="192.168.1.1")
            logged = json.loads(mock_logger.info.call_args[0][0])

        assert logged["user_ip"] == "192.168.1.1"

    def test_document_type_included_when_provided(self):
        """document_type が指定された場合に含まれる"""
        with patch("app.utils.audit_logger.audit_logger") as mock_logger:
            log_audit_event(event_type="test_event", document_type="他院への紹介")
            logged = json.loads(mock_logger.info.call_args[0][0])

        assert logged["document_type"] == "他院への紹介"

    def test_model_included_when_provided(self):
        """model が指定された場合に含まれる"""
        with patch("app.utils.audit_logger.audit_logger") as mock_logger:
            log_audit_event(event_type="test_event", model="Claude")
            logged = json.loads(mock_logger.info.call_args[0][0])

        assert logged["model"] == "Claude"

    def test_error_message_included_when_provided(self):
        """error_message が指定された場合に含まれる"""
        with patch("app.utils.audit_logger.audit_logger") as mock_logger:
            log_audit_event(event_type="test_event", error_message="何らかのエラー")
            logged = json.loads(mock_logger.info.call_args[0][0])

        assert logged["error_message"] == "何らかのエラー"

    def test_kwargs_are_added_to_log(self):
        """**kwargs の追加フィールドが記録される"""
        with patch("app.utils.audit_logger.audit_logger") as mock_logger:
            log_audit_event(
                event_type="test_event",
                input_tokens=1000,
                output_tokens=500,
                processing_time=1.23,
            )
            logged = json.loads(mock_logger.info.call_args[0][0])

        assert logged["input_tokens"] == 1000
        assert logged["output_tokens"] == 500
        assert logged["processing_time"] == 1.23

    def test_log_level_is_info(self):
        """audit_logger.info が呼ばれること（WARNING でも ERROR でもない）"""
        with patch("app.utils.audit_logger.audit_logger") as mock_logger:
            log_audit_event(event_type="test_event")

        mock_logger.info.assert_called_once()
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

    def test_json_is_valid(self):
        """出力が有効なJSONであること"""
        with patch("app.utils.audit_logger.audit_logger") as mock_logger:
            log_audit_event(event_type="test_event", user_ip="10.0.0.1", model="Claude")
            raw = mock_logger.info.call_args[0][0]

        # 例外が出なければ有効なJSON
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)
