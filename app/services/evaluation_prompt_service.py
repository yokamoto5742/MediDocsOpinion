from sqlalchemy.orm import Session

from app.core.constants import MESSAGES
from app.models.evaluation_prompt import EvaluationPrompt


def get_evaluation_prompt(db: Session, document_type: str) -> EvaluationPrompt | None:
    """評価プロンプトを取得"""
    return db.query(EvaluationPrompt).filter(
        EvaluationPrompt.document_type == document_type,
        EvaluationPrompt.is_active == True
    ).first()


def get_all_evaluation_prompts(db: Session) -> list[EvaluationPrompt]:
    """全ての評価プロンプトを取得"""
    return db.query(EvaluationPrompt).order_by(EvaluationPrompt.document_type).all()


def create_or_update_evaluation_prompt(
    db: Session,
    document_type: str,
    content: str
) -> tuple[bool, str]:
    """評価プロンプトを作成または更新"""
    if not content:
        return False, MESSAGES["VALIDATION"]["EVALUATION_PROMPT_CONTENT_REQUIRED"]

    existing = db.query(EvaluationPrompt).filter(
        EvaluationPrompt.document_type == document_type
    ).first()

    if existing:
        setattr(existing, 'content', content)
        setattr(existing, 'is_active', True)
        message = MESSAGES["SUCCESS"]["EVALUATION_PROMPT_UPDATED"]
    else:
        new_prompt = EvaluationPrompt(
            document_type=document_type,
            content=content,
            is_active=True
        )
        db.add(new_prompt)
        message = MESSAGES["SUCCESS"]["EVALUATION_PROMPT_CREATED"]

    return True, message


def delete_evaluation_prompt(db: Session, document_type: str) -> tuple[bool, str]:
    """評価プロンプトを削除"""
    prompt = db.query(EvaluationPrompt).filter(
        EvaluationPrompt.document_type == document_type
    ).first()

    if not prompt:
        return False, MESSAGES["ERROR"]["EVALUATION_PROMPT_NOT_FOUND"].format(
            document_type=document_type
        )

    db.delete(prompt)
    return True, MESSAGES["SUCCESS"]["EVALUATION_PROMPT_DELETED"]
