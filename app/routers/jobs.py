from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse
from app.config import settings
from app.db import connect
from app.schemas import RecordingJobRequest, ExplainerJobRequest, RenderRequest
from app.services.jobs import create_job, get_job, list_jobs
from app.services.jobs import set_job_status
from app.services.demo import process_demo_job
from app.utils.files import path_is_within

router = APIRouter(prefix="/api/v1", tags=["studio jobs"])


def ensure_brand_exists(brand_id: str | None) -> None:
    if not brand_id:
        return
    with connect() as db:
        exists = db.execute("SELECT 1 FROM brands WHERE id=?", (brand_id,)).fetchone()
    if not exists:
        raise HTTPException(404, "Brand kit not found")


def run_demo_job(job_id: str, kind: str, payload: dict):
    set_job_status(job_id, "processing", 25)
    try:
        result = process_demo_job(job_id, kind, payload)
        set_job_status(job_id, "completed", 100, result=result)
    except Exception as exc:
        set_job_status(job_id, "failed", 0, error=f"Demo processing failed: {exc}")


@router.post("/jobs/recording", status_code=202)
def create_recording_job(body: RecordingJobRequest, background_tasks: BackgroundTasks):
    with connect() as db:
        asset = db.execute("SELECT * FROM assets WHERE id=?", (body.asset_id,)).fetchone()
        if not asset:
            raise HTTPException(404, "Recording asset not found; upload the source video first")
    ensure_brand_exists(body.brand_id)
    payload = body.model_dump() | {"source_path": asset["stored_path"], "source_filename": asset["filename"], "source_content_type": asset["content_type"], "source_size_bytes": asset["size_bytes"]}
    job = create_job("recording_highlights", payload)
    if settings.demo_mode:
        background_tasks.add_task(run_demo_job, job["id"], job["kind"], job["input_json"])
    return job


@router.post("/jobs/explainer", status_code=202)
def create_explainer_job(body: ExplainerJobRequest, background_tasks: BackgroundTasks):
    ensure_brand_exists(body.brand_id)
    job = create_job("topic_explainer", body.model_dump())
    if settings.demo_mode:
        background_tasks.add_task(run_demo_job, job["id"], job["kind"], job["input_json"])
    return job


@router.get("/jobs")
def get_jobs(limit: int = Query(default=50, ge=1, le=200)):
    return list_jobs(limit)


@router.get("/jobs/{job_id}")
def get_one_job(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.post("/clips/{clip_id}/render", status_code=202)
def request_clip_render(clip_id: str, body: RenderRequest, background_tasks: BackgroundTasks):
    with connect() as db:
        clip = db.execute("SELECT id,job_id FROM clips WHERE id=?", (clip_id,)).fetchone()
    if not clip:
        raise HTTPException(404, "Clip not found")
    ensure_brand_exists(body.brand_id)
    job = create_job("clip_render", {"clip_id": clip_id, **body.model_dump()})
    if settings.demo_mode:
        background_tasks.add_task(run_demo_job, job["id"], job["kind"], job["input_json"])
    return job


@router.get("/jobs/{job_id}/download")
def download_job_output(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    result = job.get("result_json") or {}
    output = result.get("output_path")
    if not output:
        raise HTTPException(404, "This job has no rendered video output")
    output_path = Path(output)
    if not path_is_within(output_path, settings.output_dir) or not output_path.is_file():
        raise HTTPException(404, "Rendered video is unavailable")
    return FileResponse(output_path, media_type="video/mp4", filename=output_path.name)
