from pydantic import BaseModel, Field

from app.core.constants import DEFAULT_DOCUMENT_TYPE,ModelType


class SummaryRequest(BaseModel):
    referral_purpose: str = ""
    current_prescription: str = ""
    medical_text: str = Field(..., min_length=1)
    additional_info: str = ""
    department: str = "default"
    doctor: str = "default"
    document_type: str = DEFAULT_DOCUMENT_TYPE
    model: str = ModelType.CLAUDE.value
    model_explicitly_selected: bool = False


class SummaryResponse(BaseModel):
    success: bool
    output_summary: str
    parsed_summary: dict[str, str]
    input_tokens: int
    output_tokens: int
    processing_time: float
    model_used: str
    model_switched: bool
    error_message: str | None = None
