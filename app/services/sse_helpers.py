import asyncio
import json
import time
from collections.abc import AsyncGenerator
from typing import Any

from fastapi.responses import StreamingResponse


def sse_event(event_type: str, data: dict[str, Any]) -> str:
    """SSEイベント文字列を生成"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def sse_error(error_message: str) -> str:
    """SSEのエラーイベント文字列を生成"""
    return sse_event("error", {"success": False, "error_message": error_message})


def sse_response(event_generator: AsyncGenerator[str]) -> StreamingResponse:
    """SSE配信用のレスポンスを生成"""
    return StreamingResponse(
        event_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # nginx等のリバースプロキシによるバッファリングを無効化
            "X-Accel-Buffering": "no",
        },
    )


async def heartbeat_until_done(
    task: asyncio.Task[Any],
    start_message: str,
    running_status: str,
    running_message: str,
    elapsed_message_template: str,
    heartbeat_interval: int = 5,
) -> AsyncGenerator[str]:
    """
    タスクが完了するまで progress イベントを送り続ける

    接続がタイムアウトしないようにするためのハートビート。
    タスクの結果と例外は、呼び出し側が task.result() で取得する。
    """
    yield sse_event("progress", {"status": "starting", "message": start_message})
    yield sse_event("progress", {"status": running_status, "message": running_message})

    start_time = time.time()
    while True:
        done, _ = await asyncio.wait({task}, timeout=heartbeat_interval)
        if done:
            return
        elapsed = int(time.time() - start_time)
        yield sse_event(
            "progress",
            {
                "status": running_status,
                "message": elapsed_message_template.format(elapsed=elapsed),
            },
        )
