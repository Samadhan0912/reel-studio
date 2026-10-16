import shutil
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings

app = FastAPI(
    title="REEL STUDIO API",
    description="Backend processing engine for educational video reel studio",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["System"])
def health_check():
    ffmpeg_detected = shutil.which("ffmpeg") is not None
    ffprobe_detected = shutil.which("ffprobe") is not None
    return {
        "status": "healthy",
        "service": "reel-studio-backend",
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "ffmpeg_available": ffmpeg_detected,
        "ffprobe_available": ffprobe_detected,
    }