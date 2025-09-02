from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    app_name: str = "Touchscreen Web Photobooth"
    app_description: str = "A full-screen touchscreen photobooth application with photo selection"
    debug: bool = False

    host: str = "0.0.0.0"
    port: int = 8000

    camera_width: int = 1920
    camera_height: int = 1080
    camera_fps: int = 30
    preview_width: int = 640

    photo_quality: int = 95
    preview_quality: int = 60
    photos_dir: str = "app/static/photos"
    templates_dir: str = "app/static/templates"

    capture_limits: dict = {
        "double": 4,
        "quad": 6,
        "strip": 12
    }

    final_limits: dict = {
        "double": 2,
        "quad": 4,
        "strip": 8
    }

    class Config:
        env_file = ".env"


settings = Settings()
os.makedirs(settings.photos_dir, exist_ok=True)
os.makedirs(settings.templates_dir, exist_ok=True)