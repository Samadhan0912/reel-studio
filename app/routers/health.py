import importlib.util
import shutil
from fastapi import APIRouter
from app.config import settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "reel-studio-api"}


@router.get("/api/v1/capabilities")
def capabilities():
    local_asr_installed = importlib.util.find_spec("faster_whisper") is not None
    ffmpeg_available = shutil.which("ffmpeg") is not None or importlib.util.find_spec("imageio_ffmpeg") is not None
    gemini_configured = bool(settings.gemini_api_key)
    return {
        "demo_mode": settings.demo_mode,
        "features": {
            "uploads": True,
            "brand_kits": True,
            "clip_timeline_edits": True,
            "sample_storyboards": settings.demo_mode,
            "gemini_configured": gemini_configured,
            "ai_transcription": False,
            "ai_highlight_detection": not settings.demo_mode and gemini_configured,
            "local_transcription": not settings.demo_mode and local_asr_installed,
            "voice_generation": not settings.demo_mode and gemini_configured and settings.enable_generated_audio,
            "mp4_rendering": not settings.demo_mode and ffmpeg_available and settings.enable_video_rendering,
            "social_publishing": False,
        },
    }
