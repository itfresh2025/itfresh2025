from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from ..database import Base


class FieldOption(Base):
    __tablename__ = "field_options"

    id = Column(Integer, primary_key=True, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    value = Column(String(200), nullable=False)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
