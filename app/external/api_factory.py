import logging

from app.core.constants import MESSAGES, ModelType
from app.external.base_api import BaseAPIClient
from app.external.claude_api import ClaudeAPIClient
from app.external.gemini_api import GeminiAPIClient

logger = logging.getLogger(__name__)


def create_client(model_type: ModelType) -> BaseAPIClient:
    """モデル種別に応じたAPIクライアントを生成"""
    if model_type == ModelType.GEMINI:
        logger.info(MESSAGES["LOG"]["CLIENT_DIRECT_GEMINI"])
        return GeminiAPIClient()

    logger.info(MESSAGES["LOG"]["CLIENT_DIRECT_CLAUDE"])
    return ClaudeAPIClient()
