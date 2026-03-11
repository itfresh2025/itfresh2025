from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from ..models.client import ColorMark


class ClientBase(BaseModel):
    company: str
    ip_address: Optional[str] = None
    mask: Optional[str] = None
    gate: Optional[str] = None
    login: Optional[str] = None
    password: Optional[str] = None   # plaintext in -> encrypted in DB
    teamviewer_id: Optional[str] = None
    date: Optional[date] = None
    color_mark: ColorMark = ColorMark.none
    info_link: Optional[str] = None
    notes: Optional[str] = None
    anydesk_id: Optional[str] = None
    rudesktop_id: Optional[str] = None
    preferred_vnc: Optional[str] = None
    owner: Optional[str] = None
    address: Optional[str] = None
    provider: Optional[str] = None
    contact_person: Optional[str] = None
    access_groups: Optional[str] = None  # JSON string


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    company: Optional[str] = None
    ip_address: Optional[str] = None
    mask: Optional[str] = None
    gate: Optional[str] = None
    login: Optional[str] = None
    password: Optional[str] = None
    teamviewer_id: Optional[str] = None
    date: Optional[date] = None
    color_mark: Optional[ColorMark] = None
    info_link: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    anydesk_id: Optional[str] = None
    rudesktop_id: Optional[str] = None
    preferred_vnc: Optional[str] = None
    owner: Optional[str] = None
    address: Optional[str] = None
    provider: Optional[str] = None
    contact_person: Optional[str] = None
    access_groups: Optional[str] = None  # JSON string


class ClientOut(ClientBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None

    class Config:
        from_attributes = True


class ClientListItem(BaseModel):
    id: int
    company: str
    ip_address: Optional[str] = None
    mask: Optional[str] = None
    gate: Optional[str] = None
    login: Optional[str] = None
    teamviewer_id: Optional[str] = None
    date: Optional[date] = None
    color_mark: ColorMark
    is_active: bool

    class Config:
        from_attributes = True
