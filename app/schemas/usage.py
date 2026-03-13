from pydantic import BaseModel


class DailyUsageSummary(BaseModel):
    """当日の使用量サマリ"""
    request_count: int
    total_input_tokens: int
    total_output_tokens: int
