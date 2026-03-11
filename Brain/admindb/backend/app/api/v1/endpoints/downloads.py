from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter()

DOWNLOADS_DIR = "/opt/admindb/downloads"

@router.get("/client")
async def download_client():
    """Download desktop client installer. No auth required."""
    file_path = os.path.join(DOWNLOADS_DIR, "AdminDB-Local-Client.exe")
    if not os.path.exists(file_path):
        # Try zip
        zip_path = os.path.join(DOWNLOADS_DIR, "AdminDB-Local-Client.zip")
        if os.path.exists(zip_path):
            return FileResponse(zip_path, filename="AdminDB-Local-Client.zip",
                              media_type="application/zip")
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Installer not available")
    return FileResponse(file_path, filename="AdminDB Setup.exe",
                       media_type="application/octet-stream")
