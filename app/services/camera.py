import cv2
import base64
from fastapi import HTTPException
from app.config import settings

class CameraService:
    def __init__(self):
        self.camera = None
        self.is_active = False

    def initialize(self) -> bool:
        try:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                raise Exception("Could not open camera")

            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, settings.camera_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.camera_height)
            self.camera.set(cv2.CAP_PROP_FPS, settings.camera_fps)

            self.is_active = True
            return True
        except Exception as e:
            print(f"Camera initialization failed: {e}")
            return False

    def capture_photo(self) -> str:
        if not self.is_active or self.camera is None:
            if not self.initialize():
                raise HTTPException(status_code=500, detail="Camera not available")

        ret, frame = self.camera.read()
        if not ret:
            raise HTTPException(status_code=500, detail="Failed to capture photo")

        frame = cv2.flip(frame, 1)
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, settings.photo_quality])
        return base64.b64encode(buffer).decode('utf-8')

    def get_preview_frame(self) -> str:
        if not self.is_active or self.camera is None:
            if not self.initialize():
                return None

        ret, frame = self.camera.read()
        if not ret:
            return None

        frame = cv2.flip(frame, 1)
        height, width = frame.shape[:2]
        preview_height = int(height * settings.preview_width / width)
        frame = cv2.resize(frame, (settings.preview_width, preview_height))

        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, settings.preview_quality])
        return base64.b64encode(buffer).decode('utf-8')

    def cleanup(self):
        if self.camera:
            self.camera.release()
            self.is_active = False

camera_service = CameraService()