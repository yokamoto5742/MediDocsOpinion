from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class SummaryUsage(Base):
    __tablename__ = "summary_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    app_type: Mapped[str | None] = mapped_column(String(100))
    # 属性名とDBのカラム名が異なる
    document_type: Mapped[str | None] = mapped_column("document_types", String(100))
    model: Mapped[str | None] = mapped_column("model_detail", String(100))
    department: Mapped[str | None] = mapped_column(String(100))
    doctor: Mapped[str | None] = mapped_column(String(100))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    processing_time: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (
        Index("ix_summary_usage_aggregation", "document_types", "department", "doctor"),
        Index("ix_summary_usage_date_document_type", "date", "document_types"),
    )
