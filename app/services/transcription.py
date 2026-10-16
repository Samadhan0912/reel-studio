"""Local speech recognition for uploaded recordings; media never leaves this machine."""
from __future__ import annotations

import tempfile
import os
from pathlib import Path
from typing import Callable, Any

from app.config import settings
from app.services.rendering import ffmpeg_path, run_ffmpeg


def _language_code(language: str | None) -> str | None:
    value = (language or "").strip().lower()
    if not value or value in {"auto", "hi-en", "hinglish", "unknown"}:
        return None
    return value.split("-")[0]


def transcribe_video(path: str, vocabulary: list[str] | None = None, language: str | None = None,
                     check_cancelled: Callable[[], None] | None = None) -> dict[str, Any]:
    """Extract 16 kHz mono audio and transcribe it with faster-whisper locally."""
    source = Path(path)
    if not source.is_file():
        raise RuntimeError("The uploaded recording is missing from the uploads folder.")
    settings.whisper_cache_dir.mkdir(parents=True, exist_ok=True)
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(settings.whisper_cache_dir.resolve()))
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Local transcription is not installed. Run `pip install -r requirements.txt` in backend, then restart the server.") from exc

    if check_cancelled:
        check_cancelled()
    with tempfile.TemporaryDirectory(prefix="reel-studio-asr-", dir=settings.temp_dir) as temp_dir:
        audio = Path(temp_dir) / "recording.wav"
        run_ffmpeg(
            [ffmpeg_path(), "-nostdin", "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio)],
            check_cancelled,
        )
        if check_cancelled:
            check_cancelled()

        model = WhisperModel(settings.whisper_model, device=settings.whisper_device, compute_type=settings.whisper_compute_type)
        glossary = ", ".join((vocabulary or [])[:100])
        kwargs: dict[str, Any] = {
            "language": _language_code(language),
            "word_timestamps": True,
            "vad_filter": True,
            "beam_size": 5,
        }
        if glossary:
            kwargs["initial_prompt"] = f"Technical vocabulary and exact spellings: {glossary}"
        segments_iter, info = model.transcribe(str(audio), **kwargs)
        segments = []
        all_words = []
        for segment in segments_iter:
            if check_cancelled:
                check_cancelled()
            text = segment.text.strip()
            if not text:
                continue
            start, end = float(segment.start), float(segment.end)
            segment_words = []
            if segment.words:
                for word in segment.words:
                    token = str(word.word).strip()
                    if not token:
                        continue
                    word_data = {"text": token, "start_seconds": float(word.start), "end_seconds": float(word.end)}
                    segment_words.append(word_data)
                    all_words.append(word_data)
            segments.append({"start_seconds": start, "end_seconds": end, "text": text, "words": segment_words})
        duration = float(getattr(info, "duration", 0) or (segments[-1]["end_seconds"] if segments else 0))
        if not segments:
            raise RuntimeError("Local transcription did not detect speech in this recording.")
        return {"segments": segments, "words": all_words, "duration_seconds": duration, "language": getattr(info, "language", None)}
