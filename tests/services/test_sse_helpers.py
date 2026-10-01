import asyncio
import json
import time

import pytest

from app.services.sse_helpers import (
    heartbeat_until_done,
    sse_error,
    sse_event,
    sse_response,
)


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

    def test_sse_error(self):
        """SSEエラーイベント生成"""
        result = sse_error("エラーが発生しました")

        assert result.startswith("event: error\n")
        parsed = json.loads(result.split("data: ")[1].strip())
        assert parsed == {"success": False, "error_message": "エラーが発生しました"}


class TestSseResponse:
    """sse_response 関数のテスト"""

    def test_sse_response_headers(self):
        """SSEレスポンス - メディアタイプとバッファリング無効化ヘッダー"""

        async def events():
            yield sse_event("progress", {"status": "starting"})

        response = sse_response(events())

        assert response.media_type == "text/event-stream"
        assert response.headers["Cache-Control"] == "no-cache"
        assert response.headers["X-Accel-Buffering"] == "no"


class TestHeartbeatUntilDone:
    """heartbeat_until_done 関数のテスト"""

    async def _collect(self, task: asyncio.Task, heartbeat_interval: float = 5) -> list[dict]:
        """タスク完了までのイベントを収集し、データ部分を返す"""
        events = []
        async for event in heartbeat_until_done(
            task,
            start_message="開始",
            running_status="processing",
            running_message="処理中",
            elapsed_message_template="処理中... {elapsed}秒",
            heartbeat_interval=heartbeat_interval,  # type: ignore[arg-type]
        ):
            assert event.startswith("event: progress\n")
            events.append(json.loads(event.split("data: ")[1].strip()))
        return events

    @pytest.mark.asyncio
    async def test_yields_progress_until_task_completes(self):
        """正常系: 開始と実行中の progress を送り、結果はタスクから取得する"""
        task = asyncio.create_task(asyncio.to_thread(lambda: ("結果", 100, 50)))

        events = await self._collect(task)

        assert events == [
            {"status": "starting", "message": "開始"},
            {"status": "processing", "message": "処理中"},
        ]
        assert task.result() == ("結果", 100, 50)

    @pytest.mark.asyncio
    async def test_yields_heartbeat_while_task_is_running(self):
        """タスクが長引く場合は経過時間つきのハートビートを送る"""
        task = asyncio.create_task(asyncio.to_thread(time.sleep, 0.2))

        events = await self._collect(task, heartbeat_interval=0.05)

        assert len(events) >= 3
        assert events[2] == {"status": "processing", "message": "処理中... 0秒"}
        assert task.done()

    @pytest.mark.asyncio
    async def test_task_exception_is_left_to_caller(self):
        """タスクの例外はイベントにせず、呼び出し側が task.result() で受け取る"""

        def failing_task() -> None:
            raise ValueError("テストエラー")

        task = asyncio.create_task(asyncio.to_thread(failing_task))

        events = await self._collect(task)

        assert [event["status"] for event in events] == ["starting", "processing"]
        with pytest.raises(ValueError, match="テストエラー"):
            task.result()
