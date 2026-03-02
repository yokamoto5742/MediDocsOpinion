from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.sql import func

from .base import Base


class Prompt(Base):
    __tablename__ = "prompts"

    id: Any = Column(Integer, primary_key=True)
    department: Any = Column(String(100), nullable=False)
    document_type: Any = Column(String(100), nullable=False)
    doctor: Any = Column(String(100), nullable=False)
    content: Any = Column(Text)
    selected_model: Any = Column(String(50))
    is_default: Any = Column(Boolean, default=False)
    created_at: Any = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: Any = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_prompts_lookup", "department", "document_type", "doctor"),
    )
