from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Reel Studio API"
    database_path: Path = Path("./data/reelstudio.db")
    upload_dir: Path = Path("./uploads")
    output_dir: Path = Path("./outputs")
    temp_dir: Path = Path("./data/tmp")
    max_upload_mb: int = 2048
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    # Real processing is the default. Demo mode must be opted into explicitly.
    demo_mode: bool = False
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_tts_model: str = "gemini-3.8-flash-tts"
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_cache_dir: Path = Path("./data/whisper-cache")
    enable_generated_audio: bool = True
    enable_video_rendering: bool = True
    transcription_provider: str = "faster-whisper-local"
    llm_provider: str = "none"
    tts_provider: str = "none"
    render_provider: str = "ffmpeg"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
