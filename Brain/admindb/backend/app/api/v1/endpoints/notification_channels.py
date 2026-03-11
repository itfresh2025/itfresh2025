from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ....database import get_db
from ....models.notification_channels import NotificationChannel
from ....models.user import User, UserRole
from ....api.deps import get_current_user
from ....schemas.notification_channels import (
    NotificationChannelCreate,
    NotificationChannelUpdate,
    NotificationChannelOut,
)

router = APIRouter()


@router.get("/", response_model=List[NotificationChannelOut])
def list_channels(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(NotificationChannel).order_by(NotificationChannel.id).all()


@router.get("/{channel_id}", response_model=NotificationChannelOut)
def get_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    return channel


@router.post("/", response_model=NotificationChannelOut)
def create_channel(
    data: NotificationChannelCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    channel = NotificationChannel(
        name=data.name,
        chat_id=data.chat_id,
        description=data.description,
        is_active=data.is_active,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


@router.patch("/{channel_id}", response_model=NotificationChannelOut)
def update_channel(
    channel_id: int,
    data: NotificationChannelUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)

    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/{channel_id}")
def delete_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.admin, UserRole.superadmin):
        raise HTTPException(status_code=403, detail="Admin access required")

    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")

    db.delete(channel)
    db.commit()
    return {"ok": True}
