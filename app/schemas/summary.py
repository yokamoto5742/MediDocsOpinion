from pydantic import BaseModel, Field

from app.core.constants import DEFAULT_DOCUMENT_TYPE,ModelType


class SummaryRequest(BaseModel):
    previous_text: str = ""
    medical_text: str = Field(..., min_length=1)
    additional_info: str = ""
    department: str = "default"
    doctor: str = "default"
    document_type: str = DEFAULT_DOCUMENT_TYPE
    model: str = ModelType.CLAUDE.value
    model_explicitly_selected: bool = False
    # 評価の指摘を反映した再生成用（両方指定時のみ有効）
    previous_summary: str = ""
    evaluation_feedback: str = ""
