from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class HistoryOut(BaseModel):
    id: int
    client_id: int
    changed_by_id: Optional[int] = None
    changed_by_username: Optional[str] = None
    changed_at: datetime
    action: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None

    class Config:
        from_attributes = True
