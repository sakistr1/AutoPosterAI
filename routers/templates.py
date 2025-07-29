from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Template, User
from schemas import TemplateCreate, TemplateOut
from token_module import get_current_user

router = APIRouter(
    prefix="/templates",
    tags=["templates"],
    responses={404: {"description": "Not found"}},
)

@router.get("/test")
def test():
    return {"message": "Templates router is active"}

@router.post("/", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(
    template_in: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Αν δεν δίνει owner_id, το βάζουμε αυτόματα από τον τρέχοντα χρήστη
    owner_id = template_in.owner_id or current_user.id

    db_template = Template(
        name=template_in.name,
        type=template_in.type,
        file_path=template_in.file_path,
        owner_id=owner_id,
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


@router.get("/", response_model=List[TemplateOut])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Επιστρέφει μόνο τα templates του χρήστη
    templates = db.query(Template).filter(Template.owner_id == current_user.id).all()
    return templates


@router.get("/{template_id}", response_model=TemplateOut)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = db.query(Template).filter(
        Template.id == template_id, Template.owner_id == current_user.id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = db.query(Template).filter(
        Template.id == template_id, Template.owner_id == current_user.id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(template)
    db.commit()
    return None
