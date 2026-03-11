from typing import List
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ....database import get_db
from ....models.client import Client
from ....models.ping_history import PingHistory
from ....api.deps import get_current_user
from ....models.user import User
from ....core.ping_worker import get_status, get_all_statuses

router = APIRouter()


class PingStatusItem(BaseModel):
    client_id: int
    client_name: str
    ip: str
    online: bool
    ms: int | None
    checked_at: str | None


class PingStatusResponse(BaseModel):
    total: int
    online: int
    offline: int
    clients: List[PingStatusItem]


class PingHistoryItem(BaseModel):
    id: int
    checked_at: str
    is_online: bool
    response_ms: int | None

    class Config:
        from_attributes = True


@router.get("/status", response_model=PingStatusResponse)
def get_all_ping_status(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    clients = db.query(Client).filter(Client.is_active == True).all()
    cache = get_all_statuses()

    items = []
    for client in clients:
        s = cache.get(client.id)
        items.append(PingStatusItem(
            client_id=client.id,
            client_name=client.company,
            ip=client.ip_address or "",
            online=s["online"] if s else False,
            ms=s["ms"] if s else None,
            checked_at=s["checked_at"] if s else None,
        ))

    online_count = sum(1 for i in items if i.online)
    return PingStatusResponse(
        total=len(items),
        online=online_count,
        offline=len(items) - online_count,
        clients=items,
    )


@router.get("/status/{client_id}", response_model=PingStatusItem)
def get_client_ping_status(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id, Client.is_active == True).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    s = get_status(client_id)
    return PingStatusItem(
        client_id=client.id,
        client_name=client.company,
        ip=client.ip_address or "",
        online=s["online"] if s else False,
        ms=s["ms"] if s else None,
        checked_at=s["checked_at"] if s else None,
    )


@router.get("/history/{client_id}", response_model=List[PingHistoryItem])
def get_ping_history(
    client_id: int,
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id, Client.is_active == True).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(PingHistory)
        .filter(PingHistory.client_id == client_id, PingHistory.checked_at >= since)
        .order_by(PingHistory.checked_at.desc())
        .limit(1000)
        .all()
    )

    return [
        PingHistoryItem(
            id=r.id,
            checked_at=r.checked_at.isoformat() if r.checked_at else "",
            is_online=r.is_online,
            response_ms=r.response_ms,
        )
        for r in rows
    ]
