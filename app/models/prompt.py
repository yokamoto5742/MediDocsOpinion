from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department: Mapped[str] = mapped_column(String(100))
    document_type: Mapped[str] = mapped_column(String(100))
    doctor: Mapped[str] = mapped_column(String(100))
    content: Mapped[str | None] = mapped_column(Text)
    selected_model: Mapped[str | None] = mapped_column(String(50))
    is_default: Mapped[bool | None] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_prompts_lookup", "department", "document_type", "doctor"),
    )
