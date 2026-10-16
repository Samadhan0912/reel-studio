"""Real Gemini and FFmpeg processors used by web requests and the worker."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import settings
from app.db import connect
from app.services.cancellation import JobCancelled, ensure_job_active
from app.services.gemini import analyze_transcript, generate_explainer, synthesize_speech
from app.services.jobs import add_clips, set_job_status
from app.services.rendering import render_explainer, render_recording_clip
from app.services.transcription import transcribe_video


def _brand(brand_id: str | None) -> dict[str, Any] | None:
    if not brand_id:
        return None
    with connect() as db:
        row = db.execute("SELECT config_json FROM brands WHERE id=?", (brand_id,)).fetchone()
        if not row:
            return None
        config = json.loads(row["config_json"])
        for key, target in (("logo_asset_id", "logo_path"), ("intro_asset_id", "intro_path"), ("outro_asset_id", "outro_path")):
            asset_id = config.get(key)
            if asset_id:
                asset = db.execute("SELECT stored_path FROM assets WHERE id=?", (asset_id,)).fetchone()
                if asset and Path(asset["stored_path"]).is_file():
                    config[target] = asset["stored_path"]
    return config


def process_recording(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    set_job_status(job_id, "processing", 5)
    ensure_job_active(job_id)
    vocabulary = payload.get("technical_vocabulary", [])
    transcription = transcribe_video(
        payload["source_path"], vocabulary=vocabulary, language=payload.get("language", "hi-en"),
        check_cancelled=lambda: ensure_job_active(job_id),
    )
    ensure_job_active(job_id)
    segments = transcription["segments"]
    transcript = "\n".join(f"[{item['start_seconds']:.2f}-{item['end_seconds']:.2f}] {item['text']}" for item in segments)
    set_job_status(job_id, "processing", 58, result={
        "demo": False,
        "message": "Local transcription is complete. Gemini is selecting edit moments from transcript text only.",
        "transcript_text": transcript,
        "transcription": {"provider": "faster-whisper (local)", "language": transcription.get("language"), "duration_seconds": transcription["duration_seconds"]},
    })
    response = analyze_transcript(
        transcript, language=payload.get("language", "hi-en"), vocabulary=vocabulary,
        target_seconds=int(payload.get("target_clip_seconds", 45)),
        max_clips=int(payload.get("max_clips", 10)),
        duration_seconds=float(transcription["duration_seconds"]),
    )
    ensure_job_active(job_id)
    raw_clips = response.get("clips", [])
    clean: list[dict[str, Any]] = []
    for clip in raw_clips:
        try:
            start = max(0.0, float(clip["start_seconds"]))
            end = min(float(transcription["duration_seconds"]), float(clip["end_seconds"]))
        except (KeyError, TypeError, ValueError):
            continue
        if start < 0 or end <= start or not (30 <= end - start <= 60):
            continue
        words = [word for word in transcription["words"] if word["end_seconds"] > start and word["start_seconds"] < end]
        local_text = " ".join(item["text"] for item in segments if item["end_seconds"] > start and item["start_seconds"] < end)
        clean.append({
            "title": str(clip.get("title") or "Teaching highlight")[:140],
            "start_seconds": start,
            "end_seconds": end,
            "transcript": local_text,
            "metadata": {
                "score": clip.get("score"), "reason": clip.get("reason"),
                "focus_center_x": min(1, max(0, float(clip.get("focus_center_x", 0.5)))),
                "focus_segments": clip.get("focus_segments", []) if isinstance(clip.get("focus_segments", []), list) else [],
                "words": words,
                "source_path": payload["source_path"],
                "brand_id": payload.get("brand_id"),
                "focus_mode": "center_crop; no visual analysis was sent to Gemini",
            },
        })
    ensure_job_active(job_id)
    if clean:
        add_clips(job_id, clean)
    return {
        "demo": False,
        "message": (f"Local transcription completed; Gemini selected {len(clean)} usable highlight(s) from the transcript." if clean else "Local transcription completed, but Gemini found no complete 30–60 second teaching moment. Try a longer recording or a different language/glossary."),
        "clip_count": len(clean),
        "candidate_count": len(raw_clips),
        "rejected_count": max(0, len(raw_clips) - len(clean)),
        "transcript_text": transcript,
        "transcription": {"provider": "faster-whisper (local)", "language": transcription.get("language"), "duration_seconds": transcription["duration_seconds"]},
        "pipeline": ["audio extracted locally with FFmpeg", "speech transcribed locally with faster-whisper", "timestamped transcript sent to Gemini for highlight selection", "ready for timeline editing"],
    }


def process_explainer(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    set_job_status(job_id, "processing", 8)
    ensure_job_active(job_id)
    result = generate_explainer(
        payload["topic"], payload.get("audience", "beginner"),
        int(payload.get("duration_seconds", 45)), payload.get("language", "en"),
        payload.get("technical_vocabulary", []),
    )
    ensure_job_active(job_id)
    duration = int(payload.get("duration_seconds", 45))
    scenes = result.get("scenes", []) if isinstance(result.get("scenes"), list) else []
    captions = result.get("captions", []) if isinstance(result.get("captions"), list) else []
    if not captions:
        script_words = str(result.get("script", "")).split()
        captions = []
        phrase_size = 5
        for offset in range(0, len(script_words), phrase_size):
            part = script_words[offset:offset + phrase_size]
            left = offset / max(1, len(script_words)) * duration
            right = min(duration, (offset + len(part)) / max(1, len(script_words)) * duration)
            captions.append({"start_seconds": left, "end_seconds": right, "text": " ".join(part)})
    for caption in captions:
        caption["start_seconds"] = float(caption.get("start_seconds", caption.get("start", 0)))
        caption["end_seconds"] = float(caption.get("end_seconds", caption.get("end", duration)))
    set_job_status(job_id, "processing", 45)
    output = settings.output_dir / f"{job_id}.mp4"
    audio = settings.output_dir / f"{job_id}.wav"
    audio_error = None
    try:
        has_audio = synthesize_speech(str(result.get("script", "")), audio)
    except JobCancelled:
        raise
    except Exception as exc:  # Keep the storyboard useful when TTS is unavailable.
        has_audio, audio_error = False, str(exc)
    ensure_job_active(job_id)
    set_job_status(job_id, "processing", 70)
    render_explainer(
        scenes, captions, str(result.get("title") or payload["topic"]), output, duration,
        _brand(payload.get("brand_id")), audio if has_audio else None,
        check_cancelled=lambda: ensure_job_active(job_id),
    )
    result.update({
        "demo": False,
        "message": "Generated storyboard and vertical MP4 with Gemini." + (" Generated voiceover is included." if has_audio else " Video was rendered without generated voiceover."),
        "duration_seconds": duration,
        "scenes": scenes,
        "captions": captions,
        "output_path": str(output.resolve()),
        "download_url": f"/api/v1/jobs/{job_id}/download",
        "audio_path": str(audio.resolve()) if has_audio else None,
    })
    if audio_error:
        result["audio_note"] = f"Gemini TTS did not generate audio: {audio_error}"
    return result


def process_clip_render(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    set_job_status(job_id, "processing", 10)
    ensure_job_active(job_id)
    with connect() as db:
        clip = db.execute("SELECT * FROM clips WHERE id=?", (payload["clip_id"],)).fetchone()
        if not clip:
            raise RuntimeError("Clip no longer exists.")
        parent = db.execute("SELECT input_json FROM jobs WHERE id=?", (clip["job_id"],)).fetchone()
    metadata = json.loads(clip["metadata_json"])
    source_path = payload.get("source_path") or metadata.get("source_path")
    if not source_path and parent:
        source_path = json.loads(parent["input_json"]).get("source_path")
    if not source_path:
        raise RuntimeError("Could not find the recording file for this clip.")
    brand = _brand(payload.get("brand_id") or metadata.get("brand_id"))
    output = settings.output_dir / f"{job_id}.mp4"
    set_job_status(job_id, "processing", 35)
    render_recording_clip(
        source_path, output, float(clip["start_seconds"]), float(clip["end_seconds"]),
        str(clip["title"]), metadata.get("focus_center_x", 0.5), brand,
        metadata.get("words", []), metadata.get("focus_segments", []),
        check_cancelled=lambda: ensure_job_active(job_id),
    )
    ensure_job_active(job_id)
    return {
        "demo": False, "message": "Rendered a vertical MP4 clip with locally cropped framing and synchronized captions.",
        "clip_id": payload["clip_id"], "status": "ready", "output_path": str(output.resolve()),
        "download_url": f"/api/v1/jobs/{job_id}/download",
    }


def process_ai_job(job_id: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    if kind == "recording_highlights":
        return process_recording(job_id, payload)
    if kind == "topic_explainer":
        return process_explainer(job_id, payload)
    if kind == "clip_render":
        return process_clip_render(job_id, payload)
    raise ValueError(f"Unsupported job type: {kind}")


def run_ai_job(job_id: str, kind: str, payload: dict[str, Any]) -> None:
    try:
        ensure_job_active(job_id)
        result = process_ai_job(job_id, kind, payload)
        ensure_job_active(job_id)
        set_job_status(job_id, "completed", 100, result=result)
    except JobCancelled:
        for artifact in settings.output_dir.glob(f"{job_id}.*"):
            artifact.unlink(missing_ok=True)
        return
    except Exception as exc:
        from app.services.jobs import get_job
        job = get_job(job_id)
        set_job_status(job_id, "failed", job.get("progress", 0) if job else 0, error=str(exc))
