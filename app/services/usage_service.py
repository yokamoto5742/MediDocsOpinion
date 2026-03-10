import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func

from app.core.config import get_settings
from app.core.constants import get_message
from app.core.database import get_db_session
from app.models.usage import SummaryUsage

JST = ZoneInfo("Asia/Tokyo")


@dataclass
class DailyUsageSummary:
    """当日の使用量サマリ"""
    request_count: int
    total_input_tokens: int
    total_output_tokens: int


def get_daily_usage() -> DailyUsageSummary:
    """当日の使用量をDBから取得"""
    today_start = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)
    with get_db_session() as db:
        result = db.query(
            func.count(SummaryUsage.id),
            func.coalesce(func.sum(SummaryUsage.input_tokens), 0),
            func.coalesce(func.sum(SummaryUsage.output_tokens), 0),
        ).filter(
            SummaryUsage.date >= today_start,
        ).first()
    return DailyUsageSummary(
        request_count=result[0],
        total_input_tokens=result[1],
        total_output_tokens=result[2],
    )


def check_daily_limit() -> str | None:
    """日次制限を確認し、超過していればエラーメッセージを返す。問題なければNone"""
    try:
        s = get_settings()
        usage = get_daily_usage()
        if usage.request_count >= s.daily_request_limit:
            return get_message("ERROR", "DAILY_REQUEST_LIMIT_EXCEEDED", limit=str(s.daily_request_limit))
        if usage.total_input_tokens >= s.daily_input_token_limit:
            return get_message("ERROR", "DAILY_INPUT_TOKEN_LIMIT_EXCEEDED", limit=str(s.daily_input_token_limit))
        if usage.total_output_tokens >= s.daily_output_token_limit:
            return get_message("ERROR", "DAILY_OUTPUT_TOKEN_LIMIT_EXCEEDED", limit=str(s.daily_output_token_limit))
        return None
    except Exception as e:
        logging.error("日次利用制限チェックに失敗しました: %s", str(e), exc_info=True)
        return None  # フェイルオープン: エラー時は実行を許可


def save_usage(
    department: str,
    doctor: str,
    document_type: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    processing_time: float,
) -> None:
    """使用統計を保存"""
    try:
        with get_db_session() as db:
            usage = SummaryUsage(
                date=datetime.now(JST),
                department=department,
                doctor=doctor,
                document_type=document_type,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                app_type="dischargesummary",
                processing_time=processing_time,
            )
            db.add(usage)
    except Exception as e:
        # ログに記録するがエラーは無視
        logging.error(get_message("ERROR", "USAGE_SAVE_FAILED", error=str(e)), exc_info=True)
