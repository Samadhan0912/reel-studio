from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Reel Studio API"
    database_path: Path = Path("./data/reelstudio.db")
    upload_dir: Path = Path("./uploads")
    output_dir: Path = Path("./outputs")
    max_upload_mb: int = 2048
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    demo_mode: bool = True
    transcription_provider: str = "none"
    llm_provider: str = "none"
    tts_provider: str = "none"
    render_provider: str = "ffmpeg"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
