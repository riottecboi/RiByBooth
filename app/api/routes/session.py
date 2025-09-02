from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import uuid

from app.models.session import (
    PhotoSession, SessionCreateRequest, PhotoSelectionRequest,
    SessionStatusResponse, PhotoCaptureResponse, SessionFinalizeResponse
)
from app.services.camera import CameraService
from app.services.photo import PhotoService
from app.services.websocket import WebSocketManager
from app.api.dependencies import get_camera_service, get_photo_service, get_websocket_manager
from app.config import settings

router = APIRouter(prefix="/session", tags=["session"])
active_sessions: dict = {}
current_session: Optional[str] = None


@router.post("/create", response_model=dict)
async def create_session(
        request: SessionCreateRequest,
        websocket_manager: WebSocketManager = Depends(get_websocket_manager)
):
    global current_session

    session_id = str(uuid.uuid4())
    session = PhotoSession(
        session_id=session_id,
        layout=request.layout,
        orientation=request.orientation
    )

    active_sessions[session_id] = session
    current_session = session_id

    print(f"Created session {session_id} with layout: {request.layout}, orientation: {request.orientation}")

    return {
        "session_id": session_id,
        "layout": request.layout,
        "orientation": request.orientation,
        "max_capture_photos": settings.capture_limits[request.layout],
        "final_photos_needed": settings.final_limits[request.layout]
    }


@router.post("/capture", response_model=PhotoCaptureResponse)
async def capture_photo(
        camera_service: CameraService = Depends(get_camera_service),
        websocket_manager: WebSocketManager = Depends(get_websocket_manager)
):
    global current_session

    if current_session is None or current_session not in active_sessions:
        raise HTTPException(status_code=400, detail="No active session. Please create a session first.")

    session = active_sessions[current_session]
    photo_b64 = camera_service.capture_photo()
    session.photos.append(photo_b64)

    print(f"Captured photo {len(session.photos)} for session {current_session}")
    max_capture_photos = settings.capture_limits[session.layout]
    final_photos_needed = settings.final_limits[session.layout]
    capture_complete = len(session.photos) >= max_capture_photos
    if capture_complete:
        session.capture_complete = True

    await websocket_manager.broadcast({
        "type": "photo_captured",
        "session_id": current_session,
        "photo_count": len(session.photos),
        "photo": photo_b64,
        "capture_complete": capture_complete,
        "max_capture_photos": max_capture_photos,
        "final_photos_needed": final_photos_needed
    })

    return PhotoCaptureResponse(
        success=True,
        photo_count=len(session.photos),
        capture_complete=capture_complete,
        max_capture_photos=max_capture_photos,
        final_photos_needed=final_photos_needed,
        photo=photo_b64
    )


@router.post("/select-photos")
async def select_photos(
        request: PhotoSelectionRequest,
        websocket_manager: WebSocketManager = Depends(get_websocket_manager)
):
    global current_session

    if current_session is None or current_session not in active_sessions:
        raise HTTPException(status_code=404, detail="No active session")

    session = active_sessions[current_session]

    if not session.capture_complete:
        raise HTTPException(status_code=400, detail="Photo capture not complete yet")

    final_photos_needed = settings.final_limits[session.layout]

    if len(request.selected_indices) != final_photos_needed:
        raise HTTPException(status_code=400, detail=f"Must select exactly {final_photos_needed} photos")
    for idx in request.selected_indices:
        if idx < 0 or idx >= len(session.photos):
            raise HTTPException(status_code=400, detail="Invalid photo index")

    session.selected_photos = request.selected_indices
    session.selection_complete = True

    print(f"Selected photos {request.selected_indices} for session {current_session}")
    await websocket_manager.broadcast({
        "type": "selection_complete",
        "session_id": current_session,
        "selected_indices": request.selected_indices
    })

    return {"success": True, "selected_indices": request.selected_indices}


@router.post("/finalize", response_model=SessionFinalizeResponse)
async def finalize_session(
        photo_service: PhotoService = Depends(get_photo_service),
        websocket_manager: WebSocketManager = Depends(get_websocket_manager)
):
    global current_session

    if current_session is None or current_session not in active_sessions:
        raise HTTPException(status_code=404, detail="No active session")

    session = active_sessions[current_session]

    if not session.selection_complete:
        raise HTTPException(status_code=400, detail="Photo selection not complete")

    print(f"Finalizing session {current_session} with selected photos: {session.selected_photos}")
    selected_photos = [session.photos[i] for i in session.selected_photos]
    collage_b64 = photo_service.create_collage(selected_photos, session.layout, session.orientation)
    filename = photo_service.save_photo(collage_b64)

    await websocket_manager.broadcast({
        "type": "session_complete",
        "session_id": current_session,
        "filename": filename,
        "collage": collage_b64
    })

    del active_sessions[current_session]
    current_session = None

    return SessionFinalizeResponse(
        success=True,
        filename=filename,
        download_url=f"/api/photos/{filename}",
        collage=collage_b64
    )


@router.get("/status", response_model=SessionStatusResponse)
async def get_session_status():
    global current_session

    if current_session is None or current_session not in active_sessions:
        return SessionStatusResponse(
            session_id=None,
            photo_count=0,
            layout=None,
            orientation=None,
            max_capture_photos=0,
            final_photos_needed=0,
            capture_complete=False,
            selection_complete=False
        )

    session = active_sessions[current_session]
    max_capture_photos = settings.capture_limits[session.layout]
    final_photos_needed = settings.final_limits[session.layout]

    return SessionStatusResponse(
        session_id=current_session,
        photo_count=len(session.photos),
        layout=session.layout,
        orientation=session.orientation,
        max_capture_photos=max_capture_photos,
        final_photos_needed=final_photos_needed,
        capture_complete=session.capture_complete,
        selection_complete=session.selection_complete,
        selected_photos=session.selected_photos,
        photos=session.photos if session.capture_complete else []
    )


@router.delete("/reset")
async def reset_session():
    global current_session

    if current_session and current_session in active_sessions:
        del active_sessions[current_session]
    current_session = None
    return {"success": True}