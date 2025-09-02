from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from datetime import datetime
from app.config import settings

router = APIRouter(prefix="/photos", tags=["photos"])

@router.get("/{filename}")
async def download_photo(filename: str):
    filepath = os.path.join(settings.photos_dir, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Photo not found")

    return FileResponse(filepath, media_type="image/jpeg", filename=filename)

@router.get("/")
async def list_photos():
    photos = []

    if os.path.exists(settings.photos_dir):
        for filename in os.listdir(settings.photos_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                filepath = os.path.join(settings.photos_dir, filename)
                stat = os.stat(filepath)
                photos.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "download_url": f"/api/photos/{filename}"
                })

    return {"photos": sorted(photos, key=lambda x: x["created"], reverse=True)}