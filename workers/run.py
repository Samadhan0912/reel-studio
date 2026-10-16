"""Poll the SQLite queue and run registered processing adapters.

Run with ``python -m workers.run`` from the backend directory. The worker only
claims jobs when a matching processor is registered; missing integrations produce
an explicit failed job instead of silently leaving it in processing state.
"""
import json
import logging
import os
import time

from app.db import connect, init_db, now
from app.config import settings
from app.services.pipeline import ProviderNotConfigured, processors
from app.services.jobs import set_job_status
from app.services.demo import process_demo_job
from app.services.processing import process_ai_job

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("reelstudio.worker")


def claim_one() -> dict | None:
    """Atomically claim the oldest queued job for this worker process."""
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
        if row is None:
            return None
        changed = db.execute("UPDATE jobs SET status='processing',progress=1,updated_at=? WHERE id=? AND status='queued'",
                             (now(), row["id"])).rowcount
        if changed != 1:
            return None
        item = dict(row)
    item["input_json"] = json.loads(item["input_json"])
    return item


def run_once() -> bool:
    job = claim_one()
    if job is None:
        return False
    job_id = job["id"]
    try:
        result = (process_demo_job(job_id, job["kind"], job["input_json"]) if settings.demo_mode
                  else process_ai_job(job_id, job["kind"], job["input_json"]))
        set_job_status(job_id, "completed", 100, result=result)
        log.info("job completed id=%s kind=%s", job_id, job["kind"])
    except ProviderNotConfigured as exc:
        set_job_status(job_id, "failed", 0, error=str(exc))
        log.error("job has no processor id=%s kind=%s: %s", job_id, job["kind"], exc)
    except Exception as exc:
        set_job_status(job_id, "failed", 0, error=f"Processing failed: {exc}")
        log.exception("job failed id=%s kind=%s", job_id, job["kind"])
    return True


def main() -> None:
    init_db()
    poll_seconds = max(1, int(os.getenv("WORKER_POLL_SECONDS", "3")))
    log.info("worker started; poll interval=%ss", poll_seconds)
    while True:
        if not run_once():
            time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
