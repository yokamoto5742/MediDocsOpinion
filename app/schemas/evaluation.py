from datetime import datetime

from pydantic import BaseModel


class EvaluationRequest(BaseModel):
    document_type: str
    input_text: str
    current_prescription: str = ""
    additional_info: str = ""
    output_summary: str


class EvaluationResponse(BaseModel):
    success: bool
    evaluation_result: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    processing_time: float = 0.0
    error_message: str | None = None


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


class EvaluationPromptListResponse(BaseModel):
    prompts: list[EvaluationPromptResponse]


class EvaluationPromptSaveResponse(BaseModel):
    success: bool
    message: str
    document_type: str
