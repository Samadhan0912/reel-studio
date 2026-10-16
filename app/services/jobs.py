import json
import uuid
from typing import Any

from app.db import connect, now, decode_json_fields


def create_job(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    job_id, timestamp = str(uuid.uuid4()), now()
    with connect() as db:
        db.execute("INSERT INTO jobs(id,kind,status,input_json,progress,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                   (job_id, kind, "queued", json.dumps(payload), 0, timestamp, timestamp))
    return get_job(job_id)  # type: ignore[return-value]


def get_job(job_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    return decode_json_fields(dict(row) if row else None, ("input_json", "result_json"))


def list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [decode_json_fields(dict(row), ("input_json", "result_json")) for row in rows]  # type: ignore[misc]


def set_job_status(job_id: str, status: str, progress: int, result: dict | None = None, error: str | None = None) -> None:
    encoded_result = json.dumps(result) if result is not None else None
    with connect() as db:
        db.execute("UPDATE jobs SET status=?,progress=?,result_json=COALESCE(?,result_json),error=?,updated_at=? WHERE id=? AND (status!='cancelled' OR ?='cancelled')",
                   (status, progress, encoded_result, error, now(), job_id, status))


def add_clips(job_id: str, clips: list[dict[str, Any]]) -> None:
    with connect() as db:
        for clip in clips:
            db.execute(
                "INSERT INTO clips(id,job_id,title,start_seconds,end_seconds,transcript,metadata_json,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), job_id, clip["title"], clip["start_seconds"], clip["end_seconds"],
                 clip.get("transcript"), json.dumps(clip.get("metadata", {})), now()),
            )
