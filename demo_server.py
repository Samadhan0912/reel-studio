"""Dependency-free local preview server for the Reel Studio demo UI.

Use run_local.py for the normal FastAPI backend. This fallback serves the same
demo screens and a small in-memory subset of the API when dependencies are not
available in the current Python environment.
"""
from __future__ import annotations

import json
import mimetypes
import re
import uuid
from datetime import datetime, timezone
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
UPLOADS = ROOT / "uploads"
UPLOADS.mkdir(exist_ok=True)
ASSETS: dict[str, dict] = {}
JOBS: dict[str, dict] = {}
BRANDS: dict[str, dict] = {}
CLIPS: dict[str, dict] = {}


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_job(kind: str, payload: dict) -> dict:
    job_id = str(uuid.uuid4())
    result: dict
    if kind == "recording_highlights":
        duration = int(payload.get("target_clip_seconds", 45))
        clip_id = str(uuid.uuid4())
        clip = {"id": clip_id, "job_id": job_id, "title": "Demo highlight · complete teaching moment",
                "start_seconds": 0.0, "end_seconds": float(duration),
                "transcript": "Demo transcript preview. This preview does not analyze the uploaded recording.",
                "metadata": {"demo": True, "score": 0.91}, "created_at": timestamp()}
        CLIPS[clip_id] = clip
        result = {"demo": True, "message": "Simulated highlight created. The uploaded video was not analyzed.",
                  "clip_count": 1, "pipeline": ["upload received", "highlight preview simulated", "ready for timeline editing"]}
    elif kind == "topic_explainer":
        topic = payload.get("topic", "your topic")
        duration = int(payload.get("duration_seconds", 45))
        result = {"demo": True, "message": "Sample storyboard only. Connect an LLM and TTS provider for real script and audio generation.",
                  "script": f"Let's make {topic} simple. Start with the core idea, compare a small example, then remember when to use each approach.",
                  "duration_seconds": duration,
                  "scenes": [{"at_seconds": 0, "kind": "hook", "text": f"{topic}, explained simply", "code": ""},
                             {"at_seconds": 8, "kind": "concept", "text": "First, understand the key idea.", "code": "// concept"},
                             {"at_seconds": 20, "kind": "example", "text": "Now compare a concrete example.", "code": "const example = true;"},
                             {"at_seconds": 35, "kind": "recap", "text": "Choose based on the problem you need to solve.", "code": "// recap"}],
                  "captions": [{"start": 0, "end": 2.4, "text": topic}, {"start": 2.4, "end": 5, "text": "explained simply"}]}
    else:
        result = {"demo": True, "message": "Render request saved. Final MP4 rendering needs FFmpeg composition.", "status": "preview_only"}
    job = {"id": job_id, "kind": kind, "status": "completed", "progress": 100, "input_json": payload,
           "result_json": result, "error": None, "created_at": timestamp(), "updated_at": timestamp()}
    JOBS[job_id] = job
    return job


class Handler(BaseHTTPRequestHandler):
    server_version = "ReelStudioDemo/1.0"

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")

    def respond(self, status: int, data, content_type="application/json"):
        if isinstance(data, (dict, list)):
            body = json.dumps(data).encode("utf-8")
        else:
            body = data
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def body_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 5 * 1024 * 1024:
            raise ValueError("Request body is too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/health":
            return self.respond(200, {"status": "ok", "service": "reel-studio-demo-preview"})
        if path == "/api/v1/capabilities":
            return self.respond(200, {"demo_mode": True, "features": {"uploads": True, "brand_kits": True,
                "clip_timeline_edits": True, "sample_storyboards": True, "ai_transcription": False,
                "ai_highlight_detection": False, "voice_generation": False, "mp4_rendering": False,
                "social_publishing": False}})
        if path == "/api/v1/jobs":
            limit = int(parse_qs(parsed.query).get("limit", [50])[0])
            return self.respond(200, sorted(JOBS.values(), key=lambda job: job["created_at"], reverse=True)[:limit])
        if path == "/api/v1/assets":
            return self.respond(200, list(ASSETS.values()))
        if path == "/api/v1/brands":
            return self.respond(200, list(BRANDS.values()))
        match = re.fullmatch(r"/api/v1/jobs/([^/]+)/clips", path)
        if match:
            job_id = match.group(1)
            if job_id not in JOBS:
                return self.respond(404, {"detail": "Job not found"})
            return self.respond(200, [clip for clip in CLIPS.values() if clip["job_id"] == job_id])
        match = re.fullmatch(r"/api/v1/jobs/([^/]+)", path)
        if match:
            job = JOBS.get(match.group(1))
            return self.respond(200, job) if job else self.respond(404, {"detail": "Job not found"})
        match = re.fullmatch(r"/api/v1/brands/([^/]+)", path)
        if match:
            brand = BRANDS.get(match.group(1))
            return self.respond(200, brand) if brand else self.respond(404, {"detail": "Brand kit not found"})
        if path == "/docs":
            html = b"<!doctype html><title>Reel Studio preview</title><body style='font:16px sans-serif;background:#101512;color:#eee;padding:3rem'><h1>Reel Studio local preview</h1><p>The FastAPI API docs are available after installing the project requirements.</p><p>This preview serves the demo UI and a small in-memory API.</p><a style='color:#b9f66a' href='/'>Back to Reel Studio</a></body>"
            return self.respond(200, html, "text/html; charset=utf-8")
        relative = path.lstrip("/") or "index.html"
        file_path = (FRONTEND / relative).resolve()
        try:
            file_path.relative_to(FRONTEND.resolve())
        except ValueError:
            return self.respond(404, b"Not found", "text/plain")
        if not file_path.is_file():
            return self.respond(404, b"Not found", "text/plain")
        return self.respond(200, file_path.read_bytes(), mimetypes.guess_type(file_path.name)[0] or "application/octet-stream")

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/v1/assets":
            length = int(self.headers.get("Content-Length", "0"))
            if length > 100 * 1024 * 1024:
                return self.respond(413, {"detail": "Preview upload limit is 100 MB"})
            content_type = self.headers.get("Content-Type", "")
            raw = self.rfile.read(length)
            message = BytesParser(policy=default).parsebytes((f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n").encode() + raw)
            part = next((part for part in message.iter_parts() if part.get_filename()), None)
            if part is None:
                return self.respond(422, {"detail": "Choose a file to upload"})
            filename = Path(part.get_filename()).name
            asset_id = str(uuid.uuid4())
            payload = part.get_payload(decode=True) or b""
            (UPLOADS / f"{asset_id}{Path(filename).suffix[:12]}").write_bytes(payload)
            asset = {"id": asset_id, "filename": filename, "content_type": part.get_content_type(),
                     "size_bytes": len(payload), "created_at": timestamp()}
            ASSETS[asset_id] = asset
            return self.respond(201, asset)
        if path in ("/api/v1/jobs/recording", "/api/v1/jobs/explainer"):
            try:
                payload = self.body_json()
            except (ValueError, json.JSONDecodeError) as exc:
                return self.respond(400, {"detail": str(exc)})
            if path.endswith("recording"):
                asset = ASSETS.get(payload.get("asset_id"))
                if not asset:
                    return self.respond(404, {"detail": "Recording asset not found"})
                payload["source_filename"] = asset["filename"]
                kind = "recording_highlights"
            else:
                kind = "topic_explainer"
            return self.respond(202, make_job(kind, payload))
        if path == "/api/v1/brands":
            body = self.body_json()
            brand_id = str(uuid.uuid4())
            brand = {"id": brand_id, **body, "created_at": timestamp(), "updated_at": timestamp()}
            BRANDS[brand_id] = brand
            return self.respond(201, brand)
        match = re.fullmatch(r"/api/v1/clips/([^/]+)/render", path)
        if match:
            if match.group(1) not in CLIPS:
                return self.respond(404, {"detail": "Clip not found"})
            body = self.body_json()
            return self.respond(202, make_job("clip_render", {"clip_id": match.group(1), **body}))
        return self.respond(404, {"detail": "Route not found"})

    def do_PUT(self):
        match = re.fullmatch(r"/api/v1/brands/([^/]+)", urlparse(self.path).path)
        if not match or match.group(1) not in BRANDS:
            return self.respond(404, {"detail": "Brand kit not found"})
        brand = BRANDS[match.group(1)]
        brand.update(self.body_json())
        brand["updated_at"] = timestamp()
        return self.respond(200, brand)

    def do_PATCH(self):
        match = re.fullmatch(r"/api/v1/clips/([^/]+)", urlparse(self.path).path)
        if not match or match.group(1) not in CLIPS:
            return self.respond(404, {"detail": "Clip not found"})
        clip = CLIPS[match.group(1)]
        body = self.body_json()
        start, end = float(body.get("start_seconds", clip["start_seconds"])), float(body.get("end_seconds", clip["end_seconds"]))
        if start < 0 or not 5 <= end - start <= 90:
            return self.respond(422, {"detail": "Clip duration must be between 5 and 90 seconds"})
        clip.update(start_seconds=start, end_seconds=end)
        if body.get("title"):
            clip["title"] = body["title"]
        return self.respond(200, clip)


def run():
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("Reel Studio preview running at http://127.0.0.1:8000 (in-memory demo API; Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Reel Studio preview")
    finally:
        server.server_close()
