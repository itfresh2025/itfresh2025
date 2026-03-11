from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NotificationChannelBase(BaseModel):
    name: str
    chat_id: str = ''
    description: Optional[str] = None
    is_active: bool = True

class NotificationChannelCreate(NotificationChannelBase):
    pass

class NotificationChannelUpdate(BaseModel):
    name: Optional[str] = None
    chat_id: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class NotificationChannelOut(NotificationChannelBase):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}
