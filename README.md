# Reel Studio backend

Local full-stack app for an AI video studio. It provides persistent uploads, local Faster-Whisper transcription, Gemini-powered highlight selection and topic explainers, editable clip boundaries, brand kits, optional TTS narration, and FFmpeg MP4 rendering. Social publishing remains disabled until platform OAuth credentials are configured.

## Run locally

```powershell
cd backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Set GEMINI_API_KEY in .env before starting AI jobs.
python run_local.py
```

Open http://127.0.0.1:8000/docs for interactive API docs and http://127.0.0.1:8000 for the Reel Studio UI. SQLite and temporary extraction files are stored under `data/`; uploaded media goes to `uploads/`; rendered media goes to `outputs/`.

`python run_local.py` starts the real FastAPI app and bundled UI. It never silently switches to a fake preview. Keep this terminal open while using the app; stop it with Ctrl+C.

## API outline

- `GET /health`
- `GET /api/v1/capabilities` to inspect demo and provider feature availability
- `POST /api/v1/assets` multipart upload; `GET /api/v1/assets`
- `POST /api/v1/jobs/recording` with uploaded `asset_id`, vocabulary, language, clip length, and brand
- `POST /api/v1/jobs/explainer` with topic, audience, target duration, language, and brand
- `GET /api/v1/jobs`, `GET /api/v1/jobs/{job_id}`
- `POST /api/v1/jobs/{job_id}/cancel`
- `GET /api/v1/jobs/{job_id}/clips`, `PATCH /api/v1/clips/{clip_id}`
- `POST /api/v1/clips/{clip_id}/render`
- `POST /api/v1/brands`, `GET /api/v1/brands`
- `PUT /api/v1/brands/{brand_id}`

## Processing architecture

Class recordings stay local for transcription: FFmpeg extracts audio and `faster-whisper` (CPU, int8, `small` model by default) transcribes it with timestamps. The Whisper model downloads once on first use to `WHISPER_CACHE_DIR` and runs locally afterwards. Only the timestamped transcript, language, requested clip length, and optional glossary go to Gemini for highlight selection; the video itself is not uploaded to Gemini. Change `WHISPER_MODEL` in `.env` to `base` for a smaller/faster first download or `medium` for better accuracy if your computer can handle it. Topic jobs generate a storyboard and captions, optionally request Gemini TTS audio, and render a vertical MP4. Brand kits can include a logo, intro, and outro; intro/outro assets are trimmed to short 2-second bookends. FFmpeg is supplied by the `imageio-ffmpeg` package when it is not installed system-wide. Keep credentials in the ignored local `.env` file or a secret manager; never commit it.

`DEMO_MODE` defaults to `false`; set it to `true` only when you intentionally want simulated sample jobs. With demo mode off, missing providers produce a visible failure instead of fabricated success. The Studio status banner lists which real capabilities are ready.

Active jobs can be cancelled from their detail panel or with `POST /api/v1/jobs/{job_id}/cancel`. Cancellation stops local transcription and FFmpeg rendering, removes partial renders, and prevents later stages from starting. An already-running Gemini HTTP request may finish in the background before its thread exits; the job remains cancelled and its response is discarded.

For a local worker, run `.\\.venv\\Scripts\\python.exe -m workers.run` from this directory. The same Gemini and FFmpeg processors run in the web app and worker.
