# REEL STUDIO 🎬

> AI Video Studio converting Hinglish educational lectures into branded vertical reels and generating topic-driven educational explainers.

## Project Workflows
- **Mode A — Lecture to Reels:** Upload lecture recording -> Hinglish transcription -> AI highlight detection (30–60s) -> OpenCV 9:16 reframing -> Synced captions -> Branded export.
- **Mode B — Topic to Explainer:** Topic prompt -> Gemini multi-scene script -> TTS voiceover -> Code/visual graphics -> 9:16 vertical render.

## Tech Stack
- **Frontend:** Flutter Web (Dart)
- **Backend:** Python FastAPI
- **AI & Speech:** Google Gemini API, `faster-whisper`
- **Vision & Render:** OpenCV, FFmpeg

## Setup Instructions

### Backend Setup
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000