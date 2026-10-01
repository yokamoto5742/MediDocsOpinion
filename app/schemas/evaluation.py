from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EvaluationRequest(BaseModel):
    document_type: str
    input_text: str
    previous_text: str = ""
    additional_info: str = ""
    output_summary: str


class EvaluationPromptRequest(BaseModel):
    document_type: str
    content: str


class EvaluationPromptResponse(BaseModel):
    id: int | None = None
    document_type: str
    content: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class EvaluationPromptListResponse(BaseModel):
    prompts: list[EvaluationPromptResponse]


class EvaluationPromptSaveResponse(BaseModel):
    success: bool
    message: str
    document_type: str
