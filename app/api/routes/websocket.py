from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import json
import asyncio

from app.services.camera import CameraService
from app.services.websocket import WebSocketManager
from app.api.dependencies import get_camera_service, get_websocket_manager

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    camera_service: CameraService = Depends(get_camera_service),
    websocket_manager: WebSocketManager = Depends(get_websocket_manager)
):
    await websocket_manager.connect(websocket)
    try:
        while True:
            frame = camera_service.get_preview_frame()
            if frame:
                await websocket.send_text(json.dumps({
                    "type": "preview",
                    "data": frame
                }))
            await asyncio.sleep(1 / 15)  # ~15 FPS
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)