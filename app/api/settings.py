from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constants import DEFAULT_DEPARTMENT, DEPARTMENT_DOCTORS_MAPPING, DOCUMENT_TYPES
from app.core.database import get_db
from app.services import prompt_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/departments")
def get_departments():
    """診療科一覧を取得"""
    return {"departments": DEFAULT_DEPARTMENT}


@router.get("/doctors/{department}")
def get_doctors(department: str):
    """診療科の医師一覧を取得"""
    doctors = DEPARTMENT_DOCTORS_MAPPING.get(department, ["default"])
    return {"doctors": doctors}


@router.get("/document-types")
def get_document_types():
    """文書タイプ一覧を取得"""
    return {"document_types": DOCUMENT_TYPES}


@router.get("/selected-model")
def get_selected_model(
    department: str,
    document_type: str,
    doctor: str,
    db: Session = Depends(get_db)
):
    """プロンプトから選択されたモデルを取得"""
    selected_model = prompt_service.get_selected_model(db, department, document_type, doctor)
    return {"selected_model": selected_model}
