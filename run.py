import uvicorn
from app.main import app
from app.config import settings

if __name__ == "__main__":
    print("🚀 Starting Touchscreen Web Photobooth Server...")
    print("📱 Optimized for touchscreen displays")
    print("🖥️  Will automatically enter fullscreen mode")
    print("📸 Camera will initialize automatically")
    print(f"🌐 Access the photobooth at: http://{settings.host}:{settings.port}")
    print(f"📁 Photos will be saved to: {settings.photos_dir}")
    print("\n🎯 Features:")
    print("   - Modular FastAPI architecture")
    print("   - Full-screen touchscreen interface")
    print("   - Photo selection workflow")
    print("   - Real-time WebSocket preview")
    print("   - Dependency injection")
    print("   - Configuration management")
    print("\n📱 Photo Selection Process:")
    print("   - Double layout: Capture 4 → Select 2")
    print("   - 2×2 Grid layout: Capture 6 → Select 4")
    print("   - Photo Strip layout: Capture 12 → Select 8")
    print("\n🛑 Press Ctrl+C to stop the server\n")

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )