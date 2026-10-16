"""Cooperative cancellation shared by API handlers and background workers."""
from app.db import connect, now


class JobCancelled(RuntimeError):
    pass


def ensure_job_active(job_id: str) -> None:
    with connect() as db:
        row = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row or row["status"] == "cancelled":
        raise JobCancelled("Processing was cancelled.")


def cancel_job(job_id: str) -> dict | None:
    with connect() as db:
        row = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            return None
        if row["status"] in {"queued", "processing"}:
            db.execute(
                "UPDATE jobs SET status='cancelled',error=NULL,updated_at=? WHERE id=? AND status IN ('queued','processing')",
                (now(), job_id),
            )
    from app.services.jobs import get_job
    return get_job(job_id)
