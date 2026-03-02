from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PromptBase(BaseModel):
    department: str
    document_type: str
    doctor: str
    content: str
    selected_model: str | None = None


class PromptCreate(PromptBase):
    pass


class PromptUpdate(BaseModel):
    content: str | None = None
    selected_model: str | None = None


class PromptResponse(PromptBase):
    id: int
    is_default: bool
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class PromptListItem(BaseModel):
    """contentを除外した一覧用"""
    id: int
    department: str
    document_type: str
    doctor: str
    selected_model: str | None
    is_default: bool
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
