from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ....database import get_db
from ....models.field_options import FieldOption
from ....api.deps import get_current_user
from ....models.user import User

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class FieldOptionOut(BaseModel):
    id: int
    field_name: str
    value: str
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True


class FieldOptionCreate(BaseModel):
    field_name: str
    value: str
    sort_order: int = 0


class FieldOptionUpdate(BaseModel):
    value: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ReorderItem(BaseModel):
    id: int
    sort_order: int


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[FieldOptionOut])
def list_field_options(
    field_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Список активных опций. Фильтр по field_name если передан."""
    q = db.query(FieldOption).filter(FieldOption.is_active == True)
    if field_name:
        q = q.filter(FieldOption.field_name == field_name)
    return q.order_by(FieldOption.field_name, FieldOption.sort_order, FieldOption.id).all()


@router.get("/all", response_model=Dict[str, List[FieldOptionOut]])
def get_all_field_options(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Все справочники одним запросом: {"server_type": [...], "os_type": [...], ...}"""
    options = (
        db.query(FieldOption)
        .filter(FieldOption.is_active == True)
        .order_by(FieldOption.field_name, FieldOption.sort_order, FieldOption.id)
        .all()
    )
    result: Dict[str, List[FieldOptionOut]] = {}
    for opt in options:
        result.setdefault(opt.field_name, []).append(FieldOptionOut.model_validate(opt))
    return result


@router.post("/", response_model=FieldOptionOut)
def create_field_option(
    data: FieldOptionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    option = FieldOption(
        field_name=data.field_name,
        value=data.value,
        sort_order=data.sort_order,
    )
    db.add(option)
    db.commit()
    db.refresh(option)
    return option


@router.patch("/{option_id}", response_model=FieldOptionOut)
def update_field_option(
    option_id: int,
    data: FieldOptionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    option = db.query(FieldOption).filter(FieldOption.id == option_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="FieldOption not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(option, field, value)

    db.commit()
    db.refresh(option)
    return option


@router.delete("/{option_id}")
def delete_field_option(
    option_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Мягкое удаление — is_active=False."""
    option = db.query(FieldOption).filter(FieldOption.id == option_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="FieldOption not found")
    option.is_active = False
    db.commit()
    return {"ok": True}


@router.post("/reorder")
def reorder_field_options(
    items: List[ReorderItem],
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Массовое обновление sort_order: [{id: int, sort_order: int}, ...]"""
    for item in items:
        option = db.query(FieldOption).filter(FieldOption.id == item.id).first()
        if option:
            option.sort_order = item.sort_order
    db.commit()
    return {"ok": True}
