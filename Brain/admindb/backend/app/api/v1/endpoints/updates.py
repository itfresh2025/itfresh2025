import json
import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class UpdateInfo(BaseModel):
    version: str
    releaseDate: str
    notes: str
    mandatory: bool
    url: Optional[str] = None


@router.get("/latest", response_model=UpdateInfo)
def get_latest_update():
    version_file = "/opt/admindb/version.json"
    if os.path.exists(version_file):
        with open(version_file) as f:
            data = json.load(f)
        return UpdateInfo(**data)
    return UpdateInfo(
        version="1.0.0",
        releaseDate="2026-03-03",
        notes="Первый релиз",
        mandatory=False,
    )
