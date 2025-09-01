from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
import base64
import json
import asyncio
import os
from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageFont
import io

app = FastAPI(title="Enhanced Web Photobooth",
              description="A modern web-based photobooth application with photo selection")

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories
os.makedirs("static/photos", exist_ok=True)
os.makedirs("static/templates", exist_ok=True)


class PhotoSession(BaseModel):
    session_id: str
    photos: List[str] = []
    selected_photos: List[int] = []  # Indices of selected photos
    layout: str = "double"  # double, quad, strip
    orientation: str = "portrait"  # portrait, landscape
    template: Optional[str] = None
    capture_complete: bool = False
    selection_complete: bool = False


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                pass


manager = WebSocketManager()


class PhotoboothService:
    def __init__(self):
        self.camera = None
        self.is_camera_active = False

    def initialize_camera(self):
        """Initialize camera connection"""
        try:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                raise Exception("Could not open camera")

            # Set camera properties for better quality
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            self.camera.set(cv2.CAP_PROP_FPS, 30)

            self.is_camera_active = True
            return True
        except Exception as e:
            print(f"Camera initialization failed: {e}")
            return False

    def capture_photo(self) -> str:
        """Capture a photo and return base64 encoded image"""
        if not self.is_camera_active or self.camera is None:
            if not self.initialize_camera():
                raise HTTPException(status_code=500, detail="Camera not available")

        ret, frame = self.camera.read()
        if not ret:
            raise HTTPException(status_code=500, detail="Failed to capture photo")

        # Flip horizontally for mirror effect
        frame = cv2.flip(frame, 1)

        # Encode to JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

        # Convert to base64
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        return img_base64

    def get_preview_frame(self) -> str:
        """Get a preview frame for live view"""
        if not self.is_camera_active or self.camera is None:
            if not self.initialize_camera():
                return None

        ret, frame = self.camera.read()
        if not ret:
            return None

        # Flip horizontally for mirror effect
        frame = cv2.flip(frame, 1)

        # Resize for preview (smaller size)
        height, width = frame.shape[:2]
        preview_width = 640
        preview_height = int(height * preview_width / width)
        frame = cv2.resize(frame, (preview_width, preview_height))

        # Encode to JPEG with lower quality for speed
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])

        return base64.b64encode(buffer).decode('utf-8')

    def create_collage(self, photos: List[str], layout: str = "double", orientation: str = "portrait") -> str:
        """Create a collage from multiple photos"""
        if not photos:
            raise ValueError("No photos provided")

        # Decode base64 images
        pil_images = []
        for photo_b64 in photos:
            img_data = base64.b64decode(photo_b64)
            img = Image.open(io.BytesIO(img_data))
            pil_images.append(img)

        print(f"Creating collage with {len(pil_images)} images for layout: {layout}, orientation: {orientation}")

        if layout == "double":
            img1, img2 = pil_images[0], pil_images[1]

            if orientation == "landscape":
                target_height = 600
                img1_ratio = img1.width / img1.height
                img2_ratio = img2.width / img2.height

                img1 = img1.resize((int(target_height * img1_ratio), target_height))
                img2 = img2.resize((int(target_height * img2_ratio), target_height))

                gap = 20
                total_width = img1.width + img2.width + gap * 3
                total_height = target_height + gap * 2

                final_img = Image.new('RGB', (total_width, total_height), 'white')
                final_img.paste(img1, (gap, gap))
                final_img.paste(img2, (img1.width + gap * 2, gap))
            else:
                target_width = 600
                img1_ratio = img1.height / img1.width
                img2_ratio = img2.height / img2.width

                img1 = img1.resize((target_width, int(target_width * img1_ratio)))
                img2 = img2.resize((target_width, int(target_width * img2_ratio)))

                gap = 20
                total_width = target_width + gap * 2
                total_height = img1.height + img2.height + gap * 3

                final_img = Image.new('RGB', (total_width, total_height), 'white')
                final_img.paste(img1, (gap, gap))
                final_img.paste(img2, (gap, img1.height + gap * 2))

        elif layout == "quad":
            pil_images = pil_images[:4]

            if orientation == "landscape":
                target_size = (400, 300)
                cols, rows = 2, 2

                resized_images = [img.resize(target_size, Image.Resampling.LANCZOS) for img in pil_images]

                gap = 20
                final_width = target_size[0] * cols + gap * (cols + 1)
                final_height = target_size[1] * rows + gap * (rows + 1)

                final_img = Image.new('RGB', (final_width, final_height), 'white')

                positions = [
                    (gap, gap),
                    (target_size[0] + gap * 2, gap),
                    (gap, target_size[1] + gap * 2),
                    (target_size[0] + gap * 2, target_size[1] + gap * 2)
                ]
            else:
                target_size = (350, 250)
                cols, rows = 1, 4

                resized_images = [img.resize(target_size, Image.Resampling.LANCZOS) for img in pil_images]

                gap = 15
                final_width = target_size[0] + gap * 2
                final_height = target_size[1] * rows + gap * (rows + 1)

                final_img = Image.new('RGB', (final_width, final_height), 'white')

                positions = [
                    (gap, gap),
                    (gap, target_size[1] + gap * 2),
                    (gap, target_size[1] * 2 + gap * 3),
                    (gap, target_size[1] * 3 + gap * 4)
                ]

            for img, pos in zip(resized_images, positions):
                final_img.paste(img, pos)

        elif layout == "strip":
            pil_images = pil_images[:8]

            if orientation == "portrait":
                target_size = (280, 200)
                cols, rows = 2, 4
            else:
                target_size = (200, 280)
                cols, rows = 4, 2

            resized_images = [img.resize(target_size, Image.Resampling.LANCZOS) for img in pil_images]

            gap = 15
            final_width = target_size[0] * cols + gap * (cols + 1)
            final_height = target_size[1] * rows + gap * (rows + 1)

            final_img = Image.new('RGB', (final_width, final_height), 'white')

            positions = []
            for row in range(rows):
                for col in range(cols):
                    x = gap + col * (target_size[0] + gap)
                    y = gap + row * (target_size[1] + gap)
                    positions.append((x, y))

            for img, pos in zip(resized_images, positions):
                final_img.paste(img, pos)

        else:
            final_img = pil_images[0]

        # Add timestamp
        draw = ImageDraw.Draw(final_img)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
            except:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                except:
                    font = ImageFont.load_default()

        text_bbox = draw.textbbox((0, 0), timestamp, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        text_x = (final_img.width - text_width) // 2
        text_y = final_img.height - text_height - 20

        background_padding = 10
        background_bbox = [
            text_x - background_padding,
            text_y - background_padding,
            text_x + text_width + background_padding,
            text_y + text_height + background_padding
        ]

        overlay = Image.new('RGBA', final_img.size, (255, 255, 255, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(background_bbox, fill=(0, 0, 0, 128))

        final_img = Image.alpha_composite(final_img.convert('RGBA'), overlay).convert('RGB')

        draw = ImageDraw.Draw(final_img)
        draw.text((text_x, text_y), timestamp, fill='white', font=font)

        buffer = io.BytesIO()
        final_img.save(buffer, format='JPEG', quality=95)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def save_photo(self, photo_b64: str, filename: str = None) -> str:
        """Save photo to disk and return filename"""
        if filename is None:
            filename = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"

        filepath = f"static/photos/{filename}"

        img_data = base64.b64decode(photo_b64)
        with open(filepath, 'wb') as f:
            f.write(img_data)

        return filename

    def cleanup(self):
        """Release camera resources"""
        if self.camera:
            self.camera.release()
            self.is_camera_active = False


# Global photobooth service
photobooth = PhotoboothService()

# Active sessions
active_sessions: dict = {}
current_session: Optional[str] = None

# Updated capture limits for selection feature
CAPTURE_LIMITS = {
    "double": 4,  # Capture 4, select 2
    "quad": 6,  # Capture 6, select 4
    "strip": 12  # Capture 12, select 8
}

FINAL_LIMITS = {
    "double": 2,
    "quad": 4,
    "strip": 8
}


@app.on_event("startup")
async def startup_event():
    """Initialize camera on startup"""
    photobooth.initialize_camera()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    photobooth.cleanup()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            frame = photobooth.get_preview_frame()
            if frame:
                await websocket.send_text(json.dumps({
                    "type": "preview",
                    "data": frame
                }))
            await asyncio.sleep(1 / 15)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.post("/api/photo/capture")
async def capture_photo_direct():
    """Capture a photo directly"""
    global current_session

    if current_session is None or current_session not in active_sessions:
        raise HTTPException(status_code=400, detail="No active session. Please create a session first.")

    session = active_sessions[current_session]

    # Capture photo
    photo_b64 = photobooth.capture_photo()
    session.photos.append(photo_b64)

    print(f"Captured photo {len(session.photos)} for session {current_session}")

    # Get capture limits
    max_capture_photos = CAPTURE_LIMITS[session.layout]
    final_photos_needed = FINAL_LIMITS[session.layout]

    # Check if capture phase is complete
    capture_complete = len(session.photos) >= max_capture_photos
    if capture_complete:
        session.capture_complete = True

    # Broadcast photo captured
    await manager.broadcast({
        "type": "photo_captured",
        "session_id": current_session,
        "photo_count": len(session.photos),
        "photo": photo_b64,
        "capture_complete": capture_complete,
        "max_capture_photos": max_capture_photos,
        "final_photos_needed": final_photos_needed
    })

    return {
        "success": True,
        "photo_count": len(session.photos),
        "capture_complete": capture_complete,
        "max_capture_photos": max_capture_photos,
        "final_photos_needed": final_photos_needed,
        "photo": photo_b64
    }


@app.post("/api/session/create")
async def create_session(request: dict):
    """Create a new photo session"""
    global current_session

    layout = request.get("layout", "double")
    orientation = request.get("orientation", "portrait")

    session_id = str(uuid.uuid4())
    session = PhotoSession(session_id=session_id, layout=layout, orientation=orientation)
    active_sessions[session_id] = session
    current_session = session_id

    print(f"Created session {session_id} with layout: {layout}, orientation: {orientation}")
    return {
        "session_id": session_id,
        "layout": layout,
        "orientation": orientation,
        "max_capture_photos": CAPTURE_LIMITS[layout],
        "final_photos_needed": FINAL_LIMITS[layout]
    }


@app.post("/api/session/select-photos")
async def select_photos(request: dict):
    """Select photos for the final collage"""
    global current_session

    if current_session is None or current_session not in active_sessions:
        raise HTTPException(status_code=404, detail="No active session")

    session = active_sessions[current_session]

    if not session.capture_complete:
        raise HTTPException(status_code=400, detail="Photo capture not complete yet")

    selected_indices = request.get("selected_indices", [])
    final_photos_needed = FINAL_LIMITS[session.layout]

    if len(selected_indices) != final_photos_needed:
        raise HTTPException(status_code=400, detail=f"Must select exactly {final_photos_needed} photos")

    # Validate indices
    for idx in selected_indices:
        if idx < 0 or idx >= len(session.photos):
            raise HTTPException(status_code=400, detail="Invalid photo index")

    session.selected_photos = selected_indices
    session.selection_complete = True

    print(f"Selected photos {selected_indices} for session {current_session}")

    # Broadcast selection complete
    await manager.broadcast({
        "type": "selection_complete",
        "session_id": current_session,
        "selected_indices": selected_indices
    })

    return {
        "success": True,
        "selected_indices": selected_indices
    }


@app.post("/api/session/finalize")
async def finalize_current_session():
    """Finalize current session and create collage"""
    global current_session

    if current_session is None or current_session not in active_sessions:
        raise HTTPException(status_code=404, detail="No active session")

    session = active_sessions[current_session]

    if not session.selection_complete:
        raise HTTPException(status_code=400, detail="Photo selection not complete")

    print(f"Finalizing session {current_session} with selected photos: {session.selected_photos}")

    # Get selected photos
    selected_photos = [session.photos[i] for i in session.selected_photos]

    # Create collage
    collage_b64 = photobooth.create_collage(selected_photos, session.layout, session.orientation)
    filename = photobooth.save_photo(collage_b64)

    # Broadcast completion
    await manager.broadcast({
        "type": "session_complete",
        "session_id": current_session,
        "filename": filename,
        "collage": collage_b64
    })

    # Clean up session
    del active_sessions[current_session]
    current_session = None

    return {
        "success": True,
        "filename": filename,
        "download_url": f"/api/photos/{filename}",
        "collage": collage_b64
    }


@app.get("/api/session/status")
async def get_current_session_status():
    """Get current session status"""
    global current_session

    if current_session is None or current_session not in active_sessions:
        return {
            "session_id": None,
            "photo_count": 0,
            "layout": None,
            "orientation": None,
            "max_capture_photos": 0,
            "final_photos_needed": 0,
            "capture_complete": False,
            "selection_complete": False
        }

    session = active_sessions[current_session]
    max_capture_photos = CAPTURE_LIMITS[session.layout]
    final_photos_needed = FINAL_LIMITS[session.layout]

    return {
        "session_id": current_session,
        "photo_count": len(session.photos),
        "layout": session.layout,
        "orientation": session.orientation,
        "max_capture_photos": max_capture_photos,
        "final_photos_needed": final_photos_needed,
        "capture_complete": session.capture_complete,
        "selection_complete": session.selection_complete,
        "selected_photos": session.selected_photos,
        "photos": session.photos if session.capture_complete else []
    }


@app.get("/api/photos/{filename}")
async def download_photo(filename: str):
    """Download a saved photo"""
    filepath = f"static/photos/{filename}"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Photo not found")

    return FileResponse(filepath, media_type="image/jpeg", filename=filename)


@app.get("/api/photos")
async def list_photos():
    """List all saved photos"""
    photos = []
    photos_dir = "static/photos"

    if os.path.exists(photos_dir):
        for filename in os.listdir(photos_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                filepath = os.path.join(photos_dir, filename)
                stat = os.stat(filepath)
                photos.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "download_url": f"/api/photos/{filename}"
                })

    return {"photos": sorted(photos, key=lambda x: x["created"], reverse=True)}


@app.delete("/api/session/reset")
async def reset_session():
    """Reset current session"""
    global current_session

    if current_session and current_session in active_sessions:
        del active_sessions[current_session]
    current_session = None
    return {"success": True}


@app.get("/")
async def get_index():
    """Serve the main photobooth interface"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Enhanced Web Photobooth with Photo Selection</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                overflow-x: hidden;
            }
            .container {
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                position: relative;
                padding: 1rem;
            }
            .preview-container {
                width: 80vw;
                max-width: 800px;
                height: 60vh;
                background: rgba(0,0,0,0.8);
                border-radius: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 2rem;
                overflow: hidden;
                box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            }
            #preview {
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
                border-radius: 15px;
            }

            /* Photo Selection Screen */
            .photo-selection-screen {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.95);
                z-index: 1000;
                padding: 2rem;
                overflow-y: auto;
            }
            .selection-header {
                text-align: center;
                margin-bottom: 2rem;
            }
            .selection-instruction {
                font-size: 1.2rem;
                margin-bottom: 1rem;
                color: #fff;
            }
            .photos-grid {
                display: grid;
                gap: 1rem;
                max-width: 1200px;
                margin: 0 auto 2rem;
            }
            .photos-grid.double-selection {
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            }
            .photos-grid.quad-selection {
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            }
            .photos-grid.strip-selection {
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            }
            .photo-option {
                position: relative;
                cursor: pointer;
                border-radius: 15px;
                overflow: hidden;
                transition: all 0.3s ease;
                background: rgba(255,255,255,0.1);
                aspect-ratio: 4/3;
            }
            .photo-option img {
                width: 100%;
                height: 100%;
                object-fit: cover;
                border-radius: 15px;
            }
            .photo-option.selected {
                border: 4px solid #00d2d3;
                transform: scale(1.02);
                box-shadow: 0 10px 30px rgba(0,210,211,0.5);
            }
            .photo-option .selection-indicator {
                position: absolute;
                top: 10px;
                right: 10px;
                width: 30px;
                height: 30px;
                border-radius: 50%;
                background: rgba(0,0,0,0.7);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            .photo-option.selected .selection-indicator {
                opacity: 1;
                background: #00d2d3;
            }
            .selection-controls {
                text-align: center;
                margin-top: 2rem;
            }
            .selection-counter {
                margin-bottom: 1rem;
                font-size: 1.1rem;
                color: #00d2d3;
            }

            .settings-panel {
                background: rgba(255,255,255,0.1);
                padding: 1.5rem;
                border-radius: 20px;
                backdrop-filter: blur(10px);
                margin-bottom: 2rem;
                display: flex;
                flex-direction: column;
                gap: 1rem;
                max-width: 600px;
                width: 100%;
            }
            .setting-group {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }
            .setting-label {
                font-weight: 600;
                font-size: 0.9rem;
                text-transform: uppercase;
                opacity: 0.8;
            }
            .button-group {
                display: flex;
                gap: 0.5rem;
                flex-wrap: wrap;
            }
            .option-btn {
                padding: 0.5rem 1rem;
                border: none;
                border-radius: 20px;
                background: rgba(255,255,255,0.1);
                color: white;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 0.9rem;
            }
            .option-btn.active {
                background: rgba(255,255,255,0.3);
                transform: scale(1.05);
            }
            .option-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            .controls {
                display: flex;
                gap: 1rem;
                align-items: center;
                flex-wrap: wrap;
                justify-content: center;
                margin-bottom: 2rem;
            }
            .btn {
                padding: 1rem 2rem;
                border: none;
                border-radius: 50px;
                font-size: 1.2rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                min-width: 120px;
            }
            .btn-primary {
                background: linear-gradient(45deg, #ff6b6b, #ee5a24);
                color: white;
                box-shadow: 0 10px 25px rgba(255,107,107,0.3);
            }
            .btn-secondary {
                background: linear-gradient(45deg, #4834d4, #686de0);
                color: white;
                box-shadow: 0 10px 25px rgba(72,52,212,0.3);
            }
            .btn-success {
                background: linear-gradient(45deg, #00d2d3, #54a0ff);
                color: white;
                box-shadow: 0 10px 25px rgba(0,210,211,0.3);
            }
            .btn-warning {
                background: linear-gradient(45deg, #ffa726, #ff9800);
                color: white;
                box-shadow: 0 10px 25px rgba(255,167,38,0.3);
            }
            .btn:hover:not(:disabled) {
                transform: translateY(-3px);
                box-shadow: 0 15px 35px rgba(0,0,0,0.2);
            }
            .btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            .status {
                position: absolute;
                top: 2rem;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(0,0,0,0.8);
                padding: 1rem 2rem;
                border-radius: 25px;
                backdrop-filter: blur(10px);
                text-align: center;
                max-width: 90%;
            }
            .countdown {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 8rem;
                font-weight: bold;
                color: #ff6b6b;
                text-shadow: 0 0 30px rgba(255,107,107,0.5);
                z-index: 1000;
                display: none;
            }
            .gallery-btn {
                position: absolute;
                top: 2rem;
                right: 2rem;
                padding: 0.5rem 1rem;
                border: none;
                border-radius: 20px;
                background: rgba(255,255,255,0.1);
                color: white;
                cursor: pointer;
                backdrop-filter: blur(10px);
            }
            .final-photo {
                max-width: 90%;
                max-height: 80%;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            }
            .modal {
                display: none;
                position: fixed;
                z-index: 2000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.9);
                backdrop-filter: blur(5px);
            }
            .modal-content {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(255,255,255,0.1);
                padding: 2rem;
                border-radius: 20px;
                backdrop-filter: blur(20px);
                max-width: 90%;
                max-height: 90%;
                overflow: auto;
            }
            .close {
                color: white;
                float: right;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
                margin-bottom: 1rem;
            }
            .gallery-item {
                margin: 1rem 0;
                padding: 1rem;
                background: rgba(255,255,255,0.1);
                border-radius: 10px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .gallery-item-info h3 {
                margin-bottom: 0.5rem;
            }
            .gallery-item-info p {
                margin: 0.2rem 0;
                opacity: 0.8;
            }
            .auto-mode {
                background: rgba(46, 204, 113, 0.2);
                border: 2px solid #2ecc71;
                border-radius: 15px;
                padding: 1rem;
                margin-bottom: 1rem;
                text-align: center;
            }
            .progress-bar {
                width: 100%;
                height: 8px;
                background: rgba(255,255,255,0.2);
                border-radius: 4px;
                margin-top: 0.5rem;
                overflow: hidden;
            }
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #2ecc71, #27ae60);
                width: 0%;
                transition: width 0.3s ease;
            }

            /* Enhanced styles for selection phase */
            .capture-info {
                background: rgba(0,210,211,0.2);
                border: 2px solid #00d2d3;
                border-radius: 15px;
                padding: 1rem;
                margin-bottom: 1rem;
                text-align: center;
            }

            @media (max-width: 768px) {
                .settings-panel {
                    padding: 1rem;
                }
                .btn {
                    padding: 0.8rem 1.5rem;
                    font-size: 1rem;
                    min-width: 100px;
                }
                .preview-container {
                    width: 95vw;
                    height: 50vh;
                }
                .photos-grid {
                    grid-template-columns: repeat(2, 1fr);
                    gap: 0.5rem;
                }
                .photo-selection-screen {
                    padding: 1rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="status" id="status">
                Enhanced Photobooth Ready!
            </div>

            <button class="gallery-btn" onclick="showGallery()">📸 Gallery</button>

            <div class="countdown" id="countdown">3</div>

            <div class="preview-container" id="previewContainer">
                <img id="preview" src="" alt="Camera Preview" />
            </div>

            <div class="settings-panel">
                <div class="setting-group">
                    <div class="setting-label">Layout</div>
                    <div class="button-group">
                        <button class="option-btn active" data-layout="double" onclick="selectLayout('double')">Double (4→2)</button>
                        <button class="option-btn" data-layout="quad" onclick="selectLayout('quad')">2×2 Grid (6→4)</button>
                        <button class="option-btn" data-layout="strip" onclick="selectLayout('strip')">Photo Strip (12→8)</button>
                    </div>
                </div>

                <div class="setting-group">
                    <div class="setting-label">Orientation</div>
                    <div class="button-group">
                        <button class="option-btn active" data-orientation="portrait" onclick="selectOrientation('portrait')">
                            <span id="portraitLabel">Portrait</span>
                        </button>
                        <button class="option-btn" data-orientation="landscape" onclick="selectOrientation('landscape')">
                            <span id="landscapeLabel">Landscape</span>
                        </button>
                    </div>
                </div>

                <div class="setting-group">
                    <div class="setting-label">Capture Mode</div>
                    <div class="button-group">
                        <button class="option-btn active" data-mode="manual" onclick="selectMode('manual')">Manual</button>
                        <button class="option-btn" data-mode="burst" onclick="selectMode('burst')">Auto Burst</button>
                    </div>
                </div>
            </div>

            <div id="captureInfo" class="capture-info" style="display: none;">
                <h3 id="captureInfoTitle">Capture Phase</h3>
                <p id="captureInfoText">Ready to capture photos</p>
                <div class="progress-bar">
                    <div class="progress-fill" id="captureProgressFill"></div>
                </div>
            </div>

            <div id="autoModeInfo" class="auto-mode" style="display: none;">
                <h3>Auto Burst Mode Active</h3>
                <p id="autoModeText">Ready to capture</p>
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
            </div>

            <div class="controls">
                <button class="btn btn-primary" id="takePhotoBtn" onclick="takePhoto()">📸 Take Photo</button>
                <button class="btn btn-secondary" id="startAutoBtn" onclick="startAutoMode()" style="display: none;">🚀 Start Auto Burst</button>
                <button class="btn btn-warning" id="stopAutoBtn" onclick="stopAutoMode()" style="display: none;">⏹️ Stop Auto Burst</button>
                <button class="btn btn-success" id="selectPhotosBtn" onclick="showPhotoSelection()" style="display: none;" disabled>🎯 Select Photos</button>
                <button class="btn btn-success" id="finishBtn" onclick="finishSession()" style="display: none;" disabled>✅ Finish Session</button>
                <button class="btn btn-secondary" id="resetBtn" onclick="resetSession()">🔄 Reset</button>
            </div>
        </div>

        <!-- Photo Selection Screen -->
        <div id="photoSelectionScreen" class="photo-selection-screen">
            <div class="selection-header">
                <h2>Select Your Best Photos</h2>
                <p class="selection-instruction" id="selectionInstruction">Choose your favorite photos for the final collage</p>
                <div class="selection-counter" id="selectionCounter">0 of 2 photos selected</div>
            </div>
            <div class="photos-grid" id="photosGrid">
                <!-- Photos will be inserted here dynamically -->
            </div>
            <div class="selection-controls">
                <button class="btn btn-success" id="confirmSelectionBtn" onclick="confirmSelection()" disabled>✅ Confirm Selection</button>
                <button class="btn btn-secondary" onclick="closePhotoSelection()">❌ Cancel</button>
            </div>
        </div>

        <div id="galleryModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeGallery()">&times;</span>
                <h2>Photo Gallery</h2>
                <div id="galleryContent">
                    Loading...
                </div>
            </div>
        </div>

        <script>
            let ws = null;
            let selectedLayout = 'double';
            let selectedOrientation = 'portrait';
            let captureMode = 'manual';
            let autoTimeout = null;
            let currentSessionData = null;
            let selectedPhotoIndices = [];

            const CAPTURE_LIMITS = { double: 4, quad: 6, strip: 12 };
            const FINAL_LIMITS = { double: 2, quad: 4, strip: 8 };

            function initWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                ws = new WebSocket(wsUrl);

                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);

                    if (data.type === 'preview') {
                        document.getElementById('preview').src = `data:image/jpeg;base64,${data.data}`;
                    } else if (data.type === 'photo_captured') {
                        updateSessionStatus();
                        updateCaptureProgress(data.photo_count, data.max_capture_photos);
                        console.log(`Photo captured: ${data.photo_count}/${data.max_capture_photos}`);

                        if (data.capture_complete) {
                            console.log('Capture phase complete - ready for selection');
                        }
                    } else if (data.type === 'selection_complete') {
                        console.log('Photo selection completed');
                    } else if (data.type === 'session_complete') {
                        showFinalPhoto(data.collage);
                        stopAutoMode();
                        updateSessionStatus();
                        console.log('Session completed');
                    }
                };

                ws.onerror = function(error) {
                    console.error('WebSocket error:', error);
                    updateStatus('Camera connection failed');
                };

                ws.onclose = function() {
                    console.log('WebSocket connection closed');
                    setTimeout(initWebSocket, 3000);
                };
            }

            function updateCaptureProgress(current, total) {
                const progressFill = document.getElementById('captureProgressFill');
                const captureInfo = document.getElementById('captureInfo');
                const captureInfoText = document.getElementById('captureInfoText');

                if (current > 0) {
                    captureInfo.style.display = 'block';
                    const progress = (current / total) * 100;
                    progressFill.style.width = `${progress}%`;
                    captureInfoText.textContent = `Captured ${current} of ${total} photos`;

                    if (current >= total) {
                        captureInfoText.textContent = `All ${total} photos captured! Ready to select favorites.`;
                    }
                } else {
                    captureInfo.style.display = 'none';
                }
            }

            function selectLayout(layout) {
                selectedLayout = layout;
                document.querySelectorAll('[data-layout]').forEach(btn => btn.classList.remove('active'));
                document.querySelector(`[data-layout="${layout}"]`).classList.add('active');

                updateOrientationLabels();
                updateStatus();
                console.log(`Selected layout: ${layout}`);
            }

            function selectOrientation(orientation) {
                selectedOrientation = orientation;
                document.querySelectorAll('[data-orientation]').forEach(btn => btn.classList.remove('active'));
                document.querySelector(`[data-orientation="${orientation}"]`).classList.add('active');
                updateStatus();
                console.log(`Selected orientation: ${orientation}`);
            }

            function updateOrientationLabels() {
                const portraitLabel = document.getElementById('portraitLabel');
                const landscapeLabel = document.getElementById('landscapeLabel');

                if (selectedLayout === 'strip') {
                    portraitLabel.textContent = 'Portrait (2×4)';
                    landscapeLabel.textContent = 'Landscape (4×2)';
                } else if (selectedLayout === 'quad') {
                    portraitLabel.textContent = 'Portrait (1×4)';
                    landscapeLabel.textContent = 'Landscape (2×2)';
                } else {
                    portraitLabel.textContent = 'Portrait';
                    landscapeLabel.textContent = 'Landscape';
                }
            }

            function selectMode(mode) {
                captureMode = mode;
                document.querySelectorAll('[data-mode]').forEach(btn => btn.classList.remove('active'));
                document.querySelector(`[data-mode="${mode}"]`).classList.add('active');

                const takePhotoBtn = document.getElementById('takePhotoBtn');
                const startAutoBtn = document.getElementById('startAutoBtn');
                const stopAutoBtn = document.getElementById('stopAutoBtn');
                const autoModeInfo = document.getElementById('autoModeInfo');

                if (mode === 'manual') {
                    takePhotoBtn.style.display = 'block';
                    startAutoBtn.style.display = 'none';
                    stopAutoBtn.style.display = 'none';
                    autoModeInfo.style.display = 'none';
                    stopAutoMode();
                } else {
                    takePhotoBtn.style.display = 'none';
                    startAutoBtn.style.display = 'block';
                    stopAutoBtn.style.display = 'none';
                    autoModeInfo.style.display = 'none';
                    stopAutoMode();
                }

                updateButtonStates();
                updateStatus();
                console.log(`Selected mode: ${mode}`);
            }

            async function takePhoto() {
                if (!currentSessionData || !currentSessionData.session_id) {
                    await createSession();
                }

                await showCountdown();

                try {
                    const response = await fetch('/api/photo/capture', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });

                    if (response.ok) {
                        const data = await response.json();

                        // Flash effect
                        document.body.style.background = 'white';
                        setTimeout(() => {
                            document.body.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
                        }, 200);

                        updateStatus(`Photo ${data.photo_count}/${data.max_capture_photos} captured`);
                        await updateSessionStatus();
                    } else {
                        const error = await response.text();
                        console.error('Failed to capture photo:', error);
                        updateStatus('Error capturing photo');
                    }
                } catch (error) {
                    console.error('Error taking photo:', error);
                    updateStatus('Error taking photo');
                }
            }

            async function createSession() {
                try {
                    const response = await fetch('/api/session/create', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            layout: selectedLayout,
                            orientation: selectedOrientation
                        })
                    });

                    if (response.ok) {
                        const data = await response.json();
                        console.log(`Created session: ${data.layout} (capture ${data.max_capture_photos}→${data.final_photos_needed})`);
                        await updateSessionStatus();
                    } else {
                        console.error('Failed to create session');
                        updateStatus('Error creating session');
                    }
                } catch (error) {
                    console.error('Error creating session:', error);
                    updateStatus('Error creating session');
                }
            }

            async function startAutoMode() {
                const startAutoBtn = document.getElementById('startAutoBtn');
                const stopAutoBtn = document.getElementById('stopAutoBtn');
                const autoModeInfo = document.getElementById('autoModeInfo');

                startAutoBtn.style.display = 'none';
                stopAutoBtn.style.display = 'block';
                autoModeInfo.style.display = 'block';

                await createSession();

                const maxPhotos = CAPTURE_LIMITS[selectedLayout];
                let photosTaken = 0;

                const takePhotoInBurst = async () => {
                    if (photosTaken < maxPhotos) {
                        document.getElementById('autoModeText').textContent = `Taking photo ${photosTaken + 1}/${maxPhotos}...`;
                        await takePhoto();
                        photosTaken++;

                        const progress = (photosTaken / maxPhotos) * 100;
                        document.getElementById('progressFill').style.width = `${progress}%`;

                        if (photosTaken < maxPhotos) {
                            autoTimeout = setTimeout(takePhotoInBurst, 3000);
                        } else {
                            document.getElementById('autoModeText').textContent = 'All photos captured! Ready for selection.';
                            setTimeout(() => {
                                stopAutoMode();
                                // Auto-show photo selection after capture
                                setTimeout(showPhotoSelection, 1000);
                            }, 1000);
                        }
                    }
                };

                document.getElementById('autoModeText').textContent = 'Starting auto burst mode...';
                autoTimeout = setTimeout(takePhotoInBurst, 2000);
            }

            function stopAutoMode() {
                if (autoTimeout) {
                    clearTimeout(autoTimeout);
                    autoTimeout = null;
                }

                document.getElementById('startAutoBtn').style.display = captureMode !== 'manual' ? 'block' : 'none';
                document.getElementById('stopAutoBtn').style.display = 'none';
                document.getElementById('autoModeInfo').style.display = 'none';
                document.getElementById('progressFill').style.width = '0%';
            }

            function showCountdown() {
                return new Promise((resolve) => {
                    const countdownEl = document.getElementById('countdown');
                    countdownEl.style.display = 'block';

                    let count = 3;
                    countdownEl.textContent = count;

                    const interval = setInterval(() => {
                        count--;
                        if (count > 0) {
                            countdownEl.textContent = count;
                        } else {
                            countdownEl.textContent = 'SMILE!';
                            setTimeout(() => {
                                countdownEl.style.display = 'none';
                                clearInterval(interval);
                                resolve();
                            }, 500);
                        }
                    }, 1000);
                });
            }

            async function showPhotoSelection() {
                if (!currentSessionData || !currentSessionData.capture_complete) {
                    updateStatus('Please complete photo capture first');
                    return;
                }

                const selectionScreen = document.getElementById('photoSelectionScreen');
                const photosGrid = document.getElementById('photosGrid');
                const selectionInstruction = document.getElementById('selectionInstruction');
                const selectionCounter = document.getElementById('selectionCounter');

                // Update instruction text
                const finalCount = FINAL_LIMITS[currentSessionData.layout];
                selectionInstruction.textContent = `Choose ${finalCount} photos from ${currentSessionData.photos.length} captured photos`;
                selectionCounter.textContent = `0 of ${finalCount} photos selected`;

                // Set grid class based on layout
                photosGrid.className = `photos-grid ${currentSessionData.layout}-selection`;

                // Clear previous photos
                photosGrid.innerHTML = '';
                selectedPhotoIndices = [];

                // Add photos to grid
                currentSessionData.photos.forEach((photo, index) => {
                    const photoDiv = document.createElement('div');
                    photoDiv.className = 'photo-option';
                    photoDiv.onclick = () => togglePhotoSelection(index);

                    photoDiv.innerHTML = `
                        <img src="data:image/jpeg;base64,${photo}" alt="Photo ${index + 1}">
                        <div class="selection-indicator">${index + 1}</div>
                    `;

                    photosGrid.appendChild(photoDiv);
                });

                selectionScreen.style.display = 'block';
                updateSelectionUI();
            }

            function togglePhotoSelection(index) {
                const finalCount = FINAL_LIMITS[currentSessionData.layout];
                const photoOptions = document.querySelectorAll('.photo-option');
                const photoOption = photoOptions[index];

                if (selectedPhotoIndices.includes(index)) {
                    // Deselect
                    selectedPhotoIndices = selectedPhotoIndices.filter(i => i !== index);
                    photoOption.classList.remove('selected');
                } else if (selectedPhotoIndices.length < finalCount) {
                    // Select if we haven't reached the limit
                    selectedPhotoIndices.push(index);
                    photoOption.classList.add('selected');
                }

                updateSelectionUI();
            }

            function updateSelectionUI() {
                const finalCount = FINAL_LIMITS[currentSessionData.layout];
                const selectionCounter = document.getElementById('selectionCounter');
                const confirmBtn = document.getElementById('confirmSelectionBtn');

                selectionCounter.textContent = `${selectedPhotoIndices.length} of ${finalCount} photos selected`;

                // Update selection numbers on selected photos
                document.querySelectorAll('.photo-option').forEach((photoOption, index) => {
                    const indicator = photoOption.querySelector('.selection-indicator');
                    if (selectedPhotoIndices.includes(index)) {
                        const selectionOrder = selectedPhotoIndices.indexOf(index) + 1;
                        indicator.textContent = selectionOrder;
                    } else {
                        indicator.textContent = index + 1;
                    }
                });

                confirmBtn.disabled = selectedPhotoIndices.length !== finalCount;
            }

            function closePhotoSelection() {
                document.getElementById('photoSelectionScreen').style.display = 'none';
                selectedPhotoIndices = [];
            }

            async function confirmSelection() {
                if (selectedPhotoIndices.length !== FINAL_LIMITS[currentSessionData.layout]) {
                    updateStatus('Please select the required number of photos');
                    return;
                }

                try {
                    updateStatus('Processing selected photos...');

                    const response = await fetch('/api/session/select-photos', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            selected_indices: selectedPhotoIndices
                        })
                    });

                    if (response.ok) {
                        closePhotoSelection();
                        updateStatus('Photos selected! Ready to create collage.');
                        await updateSessionStatus();

                        // Auto-finalize after selection
                        setTimeout(finishSession, 1000);
                    } else {
                        const error = await response.text();
                        console.error('Failed to select photos:', error);
                        updateStatus('Error selecting photos');
                    }
                } catch (error) {
                    console.error('Error confirming selection:', error);
                    updateStatus('Error confirming selection');
                }
            }

            async function finishSession() {
                try {
                    updateStatus('Creating final collage...');

                    const response = await fetch('/api/session/finalize', {
                        method: 'POST'
                    });

                    if (response.ok) {
                        const data = await response.json();
                        showFinalPhoto(data.collage);
                        updateStatus('Session completed! Photo saved.');
                        console.log(`Session finalized: ${data.filename}`);

                        setTimeout(() => {
                            updateSessionStatus();
                        }, 3000);
                    } else {
                        console.error('Failed to finish session');
                        updateStatus('Error finishing session');
                    }
                } catch (error) {
                    console.error('Error finishing session:', error);
                    updateStatus('Error finishing session');
                }
            }

            async function resetSession() {
                stopAutoMode();
                closePhotoSelection();

                try {
                    await fetch('/api/session/reset', { method: 'DELETE' });
                    currentSessionData = null;
                    selectedPhotoIndices = [];
                    await updateSessionStatus();
                    updateStatus('Session reset - ready for new photos!');

                    // Reset UI
                    document.getElementById('preview').className = '';
                    document.getElementById('captureInfo').style.display = 'none';
                    document.getElementById('captureProgressFill').style.width = '0%';
                } catch (error) {
                    console.error('Error resetting session:', error);
                }
            }

            async function updateSessionStatus() {
                try {
                    const response = await fetch('/api/session/status');
                    const data = await response.json();
                    currentSessionData = data;

                    updateButtonStates();
                    updateStatus();
                } catch (error) {
                    console.error('Error updating session status:', error);
                }
            }

            function updateButtonStates() {
                const takePhotoBtn = document.getElementById('takePhotoBtn');
                const selectPhotosBtn = document.getElementById('selectPhotosBtn');
                const finishBtn = document.getElementById('finishBtn');

                if (currentSessionData && currentSessionData.session_id) {
                    const maxCapturePhotos = currentSessionData.max_capture_photos || CAPTURE_LIMITS[currentSessionData.layout];
                    const currentCount = currentSessionData.photo_count || 0;
                    const captureComplete = currentSessionData.capture_complete;
                    const selectionComplete = currentSessionData.selection_complete;

                    console.log(`Button states: ${currentCount}/${maxCapturePhotos}, capture: ${captureComplete}, selection: ${selectionComplete}`);

                    if (captureMode === 'manual') {
                        if (!captureComplete) {
                            // Still capturing photos
                            takePhotoBtn.disabled = false;
                            selectPhotosBtn.style.display = 'none';
                            finishBtn.style.display = 'none';
                        } else if (!selectionComplete) {
                            // Capture complete, ready for selection
                            takePhotoBtn.disabled = true;
                            selectPhotosBtn.style.display = 'block';
                            selectPhotosBtn.disabled = false;
                            finishBtn.style.display = 'none';
                        } else {
                            // Selection complete, ready to finish
                            takePhotoBtn.disabled = true;
                            selectPhotosBtn.style.display = 'none';
                            finishBtn.style.display = 'block';
                            finishBtn.disabled = false;
                        }
                    }
                } else {
                    // No active session
                    takePhotoBtn.disabled = false;
                    selectPhotosBtn.style.display = 'none';
                    finishBtn.style.display = 'none';
                }
            }

            function showFinalPhoto(imageData) {
                const preview = document.getElementById('preview');
                preview.src = `data:image/jpeg;base64,${imageData}`;
                preview.className = 'final-photo';
                console.log('Displaying final collage photo');
            }

            function updateStatus(message) {
                const statusEl = document.getElementById('status');

                if (message) {
                    statusEl.textContent = message;
                } else if (currentSessionData && currentSessionData.session_id) {
                    const captureLimit = CAPTURE_LIMITS[selectedLayout];
                    const finalLimit = FINAL_LIMITS[selectedLayout];
                    const currentCount = currentSessionData.photo_count || 0;

                    if (currentSessionData.capture_complete && !currentSessionData.selection_complete) {
                        statusEl.textContent = `${captureLimit} photos captured • Ready to select ${finalLimit} favorites • ${selectedLayout.toUpperCase()} ${selectedOrientation}`;
                    } else if (currentSessionData.selection_complete) {
                        statusEl.textContent = `Photos selected • Creating ${selectedLayout.toUpperCase()} ${selectedOrientation} collage`;
                    } else {
                        statusEl.textContent = `${currentCount}/${captureLimit} photos • Select ${finalLimit} • ${selectedLayout.toUpperCase()} ${selectedOrientation} • ${captureMode.toUpperCase()}`;
                    }
                } else {
                    const captureLimit = CAPTURE_LIMITS[selectedLayout];
                    const finalLimit = FINAL_LIMITS[selectedLayout];
                    statusEl.textContent = `Ready: ${selectedLayout.toUpperCase()} ${selectedOrientation} • Capture ${captureLimit}→Select ${finalLimit} • ${captureMode.toUpperCase()}`;
                }
            }

            async function showGallery() {
                try {
                    const response = await fetch('/api/photos');
                    const data = await response.json();

                    const galleryContent = document.getElementById('galleryContent');

                    if (data.photos.length === 0) {
                        galleryContent.innerHTML = '<p>No photos yet!</p>';
                    } else {
                        galleryContent.innerHTML = data.photos.map(photo => `
                            <div class="gallery-item">
                                <div class="gallery-item-info">
                                    <h3>${photo.filename}</h3>
                                    <p>Created: ${new Date(photo.created).toLocaleString()}</p>
                                    <p>Size: ${(photo.size / 1024).toFixed(1)} KB</p>
                                </div>
                                <a href="${photo.download_url}" download class="btn btn-primary" style="text-decoration: none; padding: 0.5rem 1rem; margin-left: 1rem;">Download</a>
                            </div>
                        `).join('');
                    }

                    document.getElementById('galleryModal').style.display = 'block';
                } catch (error) {
                    console.error('Error loading gallery:', error);
                    const galleryContent = document.getElementById('galleryContent');
                    galleryContent.innerHTML = '<p>Error loading gallery</p>';
                    document.getElementById('galleryModal').style.display = 'block';
                }
            }

            function closeGallery() {
                document.getElementById('galleryModal').style.display = 'none';
            }

            // Initialize
            initWebSocket();
            updateSessionStatus();
            updateOrientationLabels();
            updateButtonStates();

            // Handle window events
            window.addEventListener('beforeunload', () => {
                stopAutoMode();
                if (ws) ws.close();
            });

            window.addEventListener('click', (event) => {
                const modal = document.getElementById('galleryModal');
                if (event.target === modal) {
                    closeGallery();
                }

                const selectionScreen = document.getElementById('photoSelectionScreen');
                if (event.target === selectionScreen) {
                    closePhotoSelection();
                }
            });

            // Keyboard shortcuts
            document.addEventListener('keydown', (event) => {
                if (event.key === 'Escape') {
                    closeGallery();
                    closePhotoSelection();
                    stopAutoMode();
                } else if (event.key === ' ' || event.key === 'Enter') {
                    if (document.getElementById('photoSelectionScreen').style.display === 'block') {
                        // In selection mode
                        if (!document.getElementById('confirmSelectionBtn').disabled) {
                            event.preventDefault();
                            confirmSelection();
                        }
                    } else if (captureMode === 'manual' && !document.getElementById('takePhotoBtn').disabled) {
                        // In capture mode
                        event.preventDefault();
                        takePhoto();
                    }
                } else if (event.key === 'g' || event.key === 'G') {
                    showGallery();
                } else if (event.key === 'r' || event.key === 'R') {
                    resetSession();
                } else if (event.key === 's' || event.key === 'S') {
                    if (!document.getElementById('selectPhotosBtn').disabled && 
                        document.getElementById('selectPhotosBtn').style.display !== 'none') {
                        showPhotoSelection();
                    }
                } else if (event.key === 'f' || event.key === 'F') {
                    if (!document.getElementById('finishBtn').disabled && 
                        document.getElementById('finishBtn').style.display !== 'none') {
                        finishSession();
                    }
                }

                // Number key shortcuts for photo selection
                if (document.getElementById('photoSelectionScreen').style.display === 'block') {
                    const num = parseInt(event.key);
                    if (num >= 1 && num <= 12) {
                        const photoIndex = num - 1;
                        const photoOptions = document.querySelectorAll('.photo-option');
                        if (photoIndex < photoOptions.length) {
                            togglePhotoSelection(photoIndex);
                        }
                    }
                }
            });

            // Mobile touch support
            let touchStartY = 0;
            document.addEventListener('touchstart', (e) => {
                touchStartY = e.touches[0].clientY;
            });

            document.addEventListener('touchend', (e) => {
                const touchEndY = e.changedTouches[0].clientY;
                const diff = touchStartY - touchEndY;

                if (diff > 50) {
                    showGallery();
                } else if (diff < -50) {
                    closeGallery();
                }
            });

            // Periodically update session status
            setInterval(updateSessionStatus, 5000);
        </script>
    </body>
    </html>
    """)


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Enhanced Web Photobooth Server with Photo Selection...")
    print("📸 Camera will initialize automatically")
    print("🌐 Access the photobooth at: http://localhost:8000")
    print("📁 Photos will be saved to: ./static/photos/")
    print("\n🎯 Enhanced Features:")
    print("   - Capture extra photos for selection:")
    print("     • Double layout: Capture 4 → Select 2")
    print("     • 2×2 Grid layout: Capture 6 → Select 4")
    print("     • Photo Strip layout: Capture 12 → Select 8")
    print("   - Interactive photo selection screen")
    print("   - Portrait & Landscape orientations")
    print("   - Manual capture and Auto burst modes")
    print("   - Live camera preview")
    print("   - Photo gallery with downloads")
    print("\n📱 User Flow:")
    print("   1. Choose layout and capture mode")
    print("   2. Take photos (extra shots for selection)")
    print("   3. Select your favorite photos")
    print("   4. Create final collage automatically")
    print("\n⌨️  Keyboard shortcuts:")
    print("   - Space/Enter: Take photo or confirm selection")
    print("   - S: Show photo selection screen")
    print("   - F: Finish session")
    print("   - G: Open gallery")
    print("   - R: Reset session")
    print("   - Escape: Close modals/Stop auto mode")
    print("   - 1-12: Quick select photos (in selection mode)")
    print("\n📱 Mobile gestures:")
    print("   - Swipe up: Open gallery")
    print("   - Swipe down: Close gallery")
    print("\n🛑 Press Ctrl+C to stop the server\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)