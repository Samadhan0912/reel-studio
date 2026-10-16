from fastapi import APIRouter
from app.config import settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "reel-studio-api"}


@router.get("/api/v1/capabilities")
def capabilities():
    return {
        "demo_mode": settings.demo_mode,
        "features": {
            "uploads": True,
            "brand_kits": True,
            "clip_timeline_edits": True,
            "sample_storyboards": settings.demo_mode,
            "ai_transcription": False,
            "ai_highlight_detection": False,
            "voice_generation": False,
            "mp4_rendering": False,
            "social_publishing": False,
        },
    }
