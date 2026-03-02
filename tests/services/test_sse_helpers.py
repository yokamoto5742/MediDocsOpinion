import json

import pytest

from app.services.sse_helpers import sse_event, stream_with_heartbeat


class TestSseEvent:
    """sse_event 関数のテスト"""

    def test_sse_event_basic(self):
        """SSEイベント生成 - 基本"""
        result = sse_event("progress", {"status": "starting"})

        assert result.startswith("event: progress\n")
        assert "data: " in result
        assert result.endswith("\n\n")

        data_line = result.split("data: ")[1].strip()
        parsed = json.loads(data_line)
        assert parsed["status"] == "starting"

    def test_sse_event_japanese(self):
        """SSEイベント生成 - 日本語"""
        result = sse_event("error", {"message": "エラーが発生しました"})

        data_line = result.split("data: ")[1].strip()
        parsed = json.loads(data_line)
        assert parsed["message"] == "エラーが発生しました"

    def test_sse_event_complete(self):
        """SSEイベント生成 - 完了イベント"""
        data = {
            "success": True,
            "input_tokens": 1000,
            "output_tokens": 500,
        }
        result = sse_event("complete", data)

        assert "event: complete\n" in result
        data_line = result.split("data: ")[1].strip()
        parsed = json.loads(data_line)
        assert parsed["success"] is True
        assert parsed["input_tokens"] == 1000


class TestStreamWithHeartbeat:
    """stream_with_heartbeat 関数のテスト"""

    @pytest.mark.asyncio
    async def test_stream_with_heartbeat_success(self):
        """ハートビート付きストリーミング - 正常系"""
        def sync_task(a: int, b: int) -> tuple[str, int, int]:
            return "結果", a, b

        items = []
        async for item in stream_with_heartbeat(
            sync_func=sync_task,
            sync_func_args=(100, 50),
            start_message="開始",
            running_status="processing",
            running_message="処理中",
            elapsed_message_template="処理中... {elapsed}秒",
        ):
            items.append(item)

        # progress(starting) + progress(processing) + result
        assert len(items) >= 3
        assert "event: progress" in items[0]
        assert "開始" in items[0]
        assert "event: progress" in items[1]
        assert "処理中" in items[1]
        # 最後はresultタプル
        assert items[-1] == ("結果", 100, 50)

    @pytest.mark.asyncio
    async def test_stream_with_heartbeat_error(self):
        """ハートビート付きストリーミング - エラー"""
        def sync_task() -> tuple[str, int, int]:
            raise ValueError("テストエラー")

        items = []
        async for item in stream_with_heartbeat(
            sync_func=sync_task,
            sync_func_args=(),
            start_message="開始",
            running_status="processing",
            running_message="処理中",
            elapsed_message_template="処理中... {elapsed}秒",
        ):
            items.append(item)

        # progressイベントとerrorイベント
        assert any("event: error" in str(i) for i in items)
        error_items = [i for i in items if isinstance(i, str) and "event: error" in i]
        assert len(error_items) >= 1
        assert "テストエラー" in error_items[0]
