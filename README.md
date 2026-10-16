# Reel Studio backend

Local demo backend for an AI video studio. It provides persistent upload records, recording and explainer jobs, editable clip boundaries, brand kits, and render-job requests. Demo mode generates visibly labeled sample results so the API and frontend can be explored without external AI accounts. Demo outputs do not analyze source media or produce a rendered video.

## Run locally

```powershell
cd backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python run_local.py
```

Open http://127.0.0.1:8000/docs for interactive API docs and http://127.0.0.1:8000 for the studio demo UI. SQLite is stored under `data/`; uploaded media goes to `uploads/`; rendered media goes to `outputs/`.

`python run_local.py` starts the FastAPI app when dependencies are installed. If they are unavailable, it starts a dependency-free preview server with in-memory demo data; the preview is intended for interface walkthroughs only.

## API outline

- `GET /health`
- `GET /api/v1/capabilities` to inspect demo and provider feature availability
- `POST /api/v1/assets` multipart upload; `GET /api/v1/assets`
- `POST /api/v1/jobs/recording` with uploaded `asset_id`, vocabulary, language, clip length, and brand
- `POST /api/v1/jobs/explainer` with topic, audience, target duration, language, and brand
- `GET /api/v1/jobs`, `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/clips`, `PATCH /api/v1/clips/{clip_id}`
- `POST /api/v1/clips/{clip_id}/render`
- `POST /api/v1/brands`, `GET /api/v1/brands`
- `PUT /api/v1/brands/{brand_id}`

## Processing architecture

In demo mode, web requests generate sample storyboard and clip metadata in-process. To build a production workflow, set `DEMO_MODE=false` and configure provider adapters for word-aligned multilingual transcription (with a technical-term glossary), transcript/audio/screen highlight ranking, active-region tracking, script and code generation, TTS, and FFmpeg composition. Keep provider credentials in environment or a secret manager. Social publishing and performance feedback are intentionally not enabled until platform OAuth credentials and consent flows are configured.

For a local worker, run `python -m workers.run` from this directory. Real provider adapters are deployment work; without them the worker marks unsupported jobs as failed with a clear reason.
