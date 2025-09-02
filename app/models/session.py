from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class LayoutType(str, Enum):
    double = "double"
    quad = "quad"
    strip = "strip"

class OrientationType(str, Enum):
    portrait = "portrait"
    landscape = "landscape"

class PhotoSession(BaseModel):
    session_id: str
    photos: List[str] = []
    selected_photos: List[int] = []
    layout: LayoutType = LayoutType.double
    orientation: OrientationType = OrientationType.portrait
    template: Optional[str] = None
    capture_complete: bool = False
    selection_complete: bool = False

class SessionCreateRequest(BaseModel):
    layout: LayoutType = LayoutType.double
    orientation: OrientationType = OrientationType.portrait

class PhotoSelectionRequest(BaseModel):
    selected_indices: List[int]

class SessionStatusResponse(BaseModel):
    session_id: Optional[str]
    photo_count: int
    layout: Optional[LayoutType]
    orientation: Optional[OrientationType]
    max_capture_photos: int
    final_photos_needed: int
    capture_complete: bool
    selection_complete: bool
    selected_photos: List[int] = []
    photos: List[str] = []

class PhotoCaptureResponse(BaseModel):
    success: bool
    photo_count: int
    capture_complete: bool
    max_capture_photos: int
    final_photos_needed: int
    photo: str

class SessionFinalizeResponse(BaseModel):
    success: bool
    filename: str
    download_url: str
    collage: str