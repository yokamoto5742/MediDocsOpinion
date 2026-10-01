from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import desc, func
from sqlalchemy.orm import Query, Session

from app.core.constants import DEFAULT_STATISTICS_PERIOD_DAYS, MESSAGES
from app.models.usage import SummaryUsage

JST = ZoneInfo("Asia/Tokyo")


def _apply_default_period(
    start_date: datetime | None,
    end_date: datetime | None,
) -> tuple[datetime, datetime]:
    """期間未指定時にデフォルト期間を適用"""
    now = datetime.now(JST)
    if end_date is None:
        end_date = now
    if start_date is None:
        start_date = now - timedelta(days=DEFAULT_STATISTICS_PERIOD_DAYS)
    return start_date, end_date


def _apply_filters(
    query: Query,
    start_date: datetime | None,
    end_date: datetime | None,
    model: str | None = None,
    document_type: str | None = None,
) -> Query:
    """期間（未指定時はデフォルト期間）とモデル・文書タイプで絞り込む"""
    start_date, end_date = _apply_default_period(start_date, end_date)
    query = query.filter(SummaryUsage.date >= start_date, SummaryUsage.date <= end_date)
    if model:
        query = query.filter(SummaryUsage.model == model)
    if document_type:
        query = query.filter(SummaryUsage.document_type == document_type)
    return query


def _label(value: str | None, default_label: str) -> str:
    """値が default または未設定の場合は共通ラベルに読み替える"""
    return default_label if value in (None, "", "default") else value


def get_usage_summary(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    model: str | None = None,
) -> dict:
    """使用統計サマリを取得"""
    query = db.query(
        func.count(SummaryUsage.id),
        func.sum(SummaryUsage.input_tokens),
        func.sum(SummaryUsage.output_tokens),
        func.avg(SummaryUsage.processing_time),
    )
    stats = _apply_filters(query, start_date, end_date, model).first()

    if stats is None:
        return {
            "total_count": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "average_processing_time": 0.0,
        }

    return {
        "total_count": int(stats[0]) if stats[0] is not None else 0,
        "total_input_tokens": int(stats[1]) if stats[1] is not None else 0,
        "total_output_tokens": int(stats[2]) if stats[2] is not None else 0,
        "average_processing_time": round(float(stats[3]), 2) if stats[3] is not None else 0.0,
    }


def get_aggregated_records(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    model: str | None = None,
    document_type: str | None = None,
) -> list[dict]:
    """文書別集計統計データを取得"""
    query = db.query(
        SummaryUsage.document_type,
        SummaryUsage.department,
        SummaryUsage.doctor,
        func.count(SummaryUsage.id).label("count"),
        func.sum(SummaryUsage.input_tokens).label("input_tokens"),
        func.sum(SummaryUsage.output_tokens).label("output_tokens"),
    )
    results = (
        _apply_filters(query, start_date, end_date, model, document_type)
        .group_by(
            SummaryUsage.document_type, SummaryUsage.department, SummaryUsage.doctor
        )
        .order_by(desc("count"))
        .all()
    )

    return [
        {
            "document_type": r.document_type or "-",
            "department": _label(r.department, MESSAGES["INFO"]["DEFAULT_DEPARTMENT_LABEL"]),
            "doctor": _label(r.doctor, MESSAGES["INFO"]["DEFAULT_DOCTOR_LABEL"]),
            "count": r.count,
            "input_tokens": r.input_tokens or 0,
            "output_tokens": r.output_tokens or 0,
        }
        for r in results
    ]


def get_usage_records(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    model: str | None = None,
    document_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[SummaryUsage]:
    """使用統計レコードを取得"""
    query = _apply_filters(
        db.query(SummaryUsage), start_date, end_date, model, document_type
    )
    return query.order_by(SummaryUsage.date.desc()).offset(offset).limit(limit).all()
