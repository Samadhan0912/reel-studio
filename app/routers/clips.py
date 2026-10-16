import json
from fastapi import APIRouter, HTTPException
from app.db import connect, now
from app.schemas import ClipEdit

router = APIRouter(prefix="/api/v1", tags=["clips"])


@router.get("/jobs/{job_id}/clips")
def list_clips(job_id: str):
    with connect() as db:
        if not db.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone():
            raise HTTPException(404, "Job not found")
        rows = db.execute("SELECT * FROM clips WHERE job_id=? ORDER BY start_seconds", (job_id,)).fetchall()
    return [{"id": r["id"], "job_id": r["job_id"], "title": r["title"], "start_seconds": r["start_seconds"], "end_seconds": r["end_seconds"], "transcript": r["transcript"], "metadata": json.loads(r["metadata_json"]), "created_at": r["created_at"]} for r in rows]


@router.patch("/clips/{clip_id}")
def edit_clip(clip_id: str, body: ClipEdit):
    with connect() as db:
        row = db.execute("SELECT * FROM clips WHERE id=?", (clip_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Clip not found")
        duration = body.end_seconds - body.start_seconds
        if not 5 <= duration <= 90:
            raise HTTPException(422, "Clip duration must be between 5 and 90 seconds")
        db.execute("UPDATE clips SET title=?,start_seconds=?,end_seconds=? WHERE id=?",
                   (body.title or row["title"], body.start_seconds, body.end_seconds, clip_id))
        updated = db.execute("SELECT * FROM clips WHERE id=?", (clip_id,)).fetchone()
    return {"id": updated["id"], "job_id": updated["job_id"], "title": updated["title"], "start_seconds": updated["start_seconds"], "end_seconds": updated["end_seconds"], "transcript": updated["transcript"], "metadata": json.loads(updated["metadata_json"])}
