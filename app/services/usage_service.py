import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.constants import get_message
from app.core.database import get_db_session
from app.models.usage import SummaryUsage

JST = ZoneInfo("Asia/Tokyo")


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
                app_type="referral_letter",
                processing_time=processing_time,
            )
            db.add(usage)
    except Exception as e:
        # ログに記録するがエラーは無視
        logging.error(get_message("ERROR", "USAGE_SAVE_FAILED", error=str(e)), exc_info=True)
