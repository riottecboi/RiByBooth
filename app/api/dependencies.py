from app.services.camera import camera_service
from app.services.photo import photo_service
from app.services.websocket import websocket_manager

def get_camera_service():
    return camera_service

def get_photo_service():
    return photo_service

def get_websocket_manager():
    return websocket_manager