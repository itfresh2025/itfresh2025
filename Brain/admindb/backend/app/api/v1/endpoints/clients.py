from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ....database import get_db
from ....models.client import Client, ColorMark
from ....models.history import ClientHistory
from ....models.user import User
from ....schemas.client import ClientCreate, ClientUpdate, ClientOut, ClientListItem
from ....schemas.history import HistoryOut
from ....api.deps import get_current_user
from ....core.encryption import encrypt_password, decrypt_password

router = APIRouter()


def _record(db: Session, client_id: int, user_id: int, action: str,
            field: str = None, old: str = None, new: str = None):
    db.add(ClientHistory(
        client_id=client_id,
        changed_by_id=user_id,
        action=action,
        field_name=field,
        old_value=old,
        new_value=new,
    ))


@router.get("/", response_model=List[ClientListItem])
def list_clients(
    search: Optional[str] = Query(None, description="Search in company, IP, login, TV ID"),
    color_mark: Optional[ColorMark] = Query(None),
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Client).filter(Client.is_active == True)

    if search:
        like = f"%{search}%"
        q = q.filter(or_(
            Client.company.ilike(like),
            Client.ip_address.ilike(like),
            Client.login.ilike(like),
            Client.teamviewer_id.ilike(like),
            Client.gate.ilike(like),
        ))

    if color_mark:
        q = q.filter(Client.color_mark == color_mark)

    return q.order_by(Client.company).offset(skip).limit(limit).all()


@router.post("/", response_model=ClientOut)
def create_client(
    client_in: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = client_in.model_dump()
    password = data.pop("password", None)

    client = Client(**data, created_by_id=current_user.id)
    if password:
        client.password_encrypted = encrypt_password(password)

    db.add(client)
    db.flush()
    _record(db, client.id, current_user.id, "create")
    db.commit()
    db.refresh(client)

    result = ClientOut.model_validate(client)
    result.password = decrypt_password(client.password_encrypted) if client.password_encrypted else None
    return result


@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id, Client.is_active == True).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    result = ClientOut.model_validate(client)
    result.password = decrypt_password(client.password_encrypted) if client.password_encrypted else None
    return result


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    client_in: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id, Client.is_active == True).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    update_data = client_in.model_dump(exclude_unset=True)

    for field, new_val in update_data.items():
        if field == "password":
            old_dec = decrypt_password(client.password_encrypted) if client.password_encrypted else ""
            if new_val != old_dec:
                _record(db, client.id, current_user.id, "update", "password", "***", "***")
                client.password_encrypted = encrypt_password(new_val) if new_val else ""
        else:
            old_val = str(getattr(client, field, "") or "")
            new_str = str(new_val) if new_val is not None else ""
            if new_str != old_val:
                _record(db, client.id, current_user.id, "update", field, old_val, new_str)
            setattr(client, field, new_val)

    db.commit()
    db.refresh(client)

    result = ClientOut.model_validate(client)
    result.password = decrypt_password(client.password_encrypted) if client.password_encrypted else None
    return result


@router.delete("/{client_id}")
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    _record(db, client.id, current_user.id, "delete")
    client.is_active = False
    db.commit()
    return {"ok": True}


@router.get("/{client_id}/history", response_model=List[HistoryOut])
def get_history(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = (
        db.query(ClientHistory)
        .filter(ClientHistory.client_id == client_id)
        .order_by(ClientHistory.changed_at.desc())
        .all()
    )

    result = []
    for h in rows:
        item = HistoryOut.model_validate(h)
        if h.changed_by:
            item.changed_by_username = h.changed_by.username
        result.append(item)
    return result
