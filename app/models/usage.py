from sqlalchemy import Column, DateTime, Float, Index, Integer, String
from sqlalchemy.sql import func

from .base import Base


class SummaryUsage(Base):
    __tablename__ = "summary_usage"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    app_type = Column(String(100))
    document_type = Column("document_types", String(100))
    model = Column("model_detail", String(100))
    department = Column(String(100))
    doctor = Column(String(100))
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    processing_time = Column(Float)

    __table_args__ = (
        Index("ix_summary_usage_aggregation", "document_types", "department", "doctor"),
        Index("ix_summary_usage_date_document_type", "date", "document_types"),
    )
