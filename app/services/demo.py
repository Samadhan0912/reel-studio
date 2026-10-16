"""Deterministic demo processors; outputs are always labeled as simulated."""
from typing import Any
from app.services.jobs import add_clips


def process_demo_job(job_id: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    if kind == "recording_highlights":
        duration = payload["target_clip_seconds"]
        clip = {
            "title": "Demo highlight · complete teaching moment",
            "start_seconds": 0,
            "end_seconds": duration,
            "transcript": "Demo transcript preview. Connect a speech recognition provider to analyze the uploaded class recording.",
            "metadata": {"demo": True, "score": 0.91, "reframe": "active screen region tracking requires a video vision provider"},
        }
        add_clips(job_id, [clip])
        return {"demo": True, "message": "Simulated highlight created. The uploaded video was not analyzed.", "clip_count": 1,
                "pipeline": ["upload received", "highlight preview simulated", "ready for timeline editing"]}
    if kind == "topic_explainer":
        topic = payload["topic"]
        duration = payload["duration_seconds"]
        return {
            "demo": True,
            "message": "Sample explainer storyboard. Connect an LLM and TTS provider for generated content and audio.",
            "script": f"Let's make {topic} simple. Start with the core idea, compare a small example, then remember when to use each approach.",
            "duration_seconds": duration,
            "scenes": [
                {"at_seconds": 0, "kind": "hook", "text": f"{topic}, explained simply", "code": ""},
                {"at_seconds": 8, "kind": "concept", "text": "First, understand the key idea.", "code": "// concept"},
                {"at_seconds": 20, "kind": "example", "text": "Now compare a concrete example.", "code": "const example = true;"},
                {"at_seconds": 35, "kind": "recap", "text": "Choose based on the problem you need to solve.", "code": "// recap"},
            ],
            "captions": [{"start": 0.0, "end": 2.4, "text": topic}, {"start": 2.4, "end": 5.0, "text": "explained simply"}],
        }
    if kind == "clip_render":
        return {"demo": True, "message": "Render request saved. Configure FFmpeg composition to produce a downloadable MP4.", "clip_id": payload["clip_id"], "status": "preview_only"}
    raise ValueError(f"Unsupported job type: {kind}")
