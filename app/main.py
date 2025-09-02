from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from app.config import settings
from app.api.routes import session, photos, websocket
from app.services.camera import camera_service
from app.templates.index import get_html_template

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    debug=settings.debug
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(session.router, prefix="/api")
app.include_router(photos.router, prefix="/api")
app.include_router(websocket.router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.on_event("startup")
async def startup_event():
    camera_service.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    camera_service.cleanup()
@app.get("/")
async def get_index():
    return HTMLResponse(get_html_template())

@app.get("/health")
async def health_check():
    return {"status": "healthy", "camera_active": camera_service.is_active}