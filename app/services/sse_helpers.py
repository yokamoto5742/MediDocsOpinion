import asyncio
import json
import logging
import time
from collections.abc import Callable
from typing import Any, AsyncGenerator


def sse_event(event_type: str, data: dict[str, Any]) -> str:
    """SSEイベント文字列を生成"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_with_heartbeat(
    sync_func: Callable[..., tuple[str, int, int]],
    sync_func_args: tuple[Any, ...],
    start_message: str,
    running_status: str,
    running_message: str,
    elapsed_message_template: str,
    heartbeat_interval: int = 5,
) -> AsyncGenerator[tuple[str, int, int] | str, None]:
    """ハートビート付きでスレッドプール上の同期処理を実行"""
    yield sse_event("progress", {
        "status": "starting",
        "message": start_message,
    })

    start_time = time.time()
    queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()

    async def _task() -> None:
        try:
            result = await asyncio.to_thread(sync_func, *sync_func_args)
            await queue.put(("result", result))
        except Exception as e:
            logging.error(f"Task error: {e}", exc_info=True)
            await queue.put(("error", str(e)))

    task = asyncio.create_task(_task())

    yield sse_event("progress", {
        "status": running_status,
        "message": running_message,
    })

    while not task.done():
        try:
            msg_type, msg_data = await asyncio.wait_for(
                queue.get(), timeout=heartbeat_interval
            )
            if msg_type == "error":
                yield sse_event("error", {
                    "success": False,
                    "error_message": msg_data,
                })
                return
            yield msg_data
            return
        except asyncio.TimeoutError:
            elapsed = int(time.time() - start_time)
            yield sse_event("progress", {
                "status": running_status,
                "message": elapsed_message_template.format(elapsed=elapsed),
            })
