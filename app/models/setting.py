from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from .base import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(String(500))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
