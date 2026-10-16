# System Architecture

## Overview
REEL STUDIO converts long-form Hinglish educational lectures into branded vertical videos (Mode A) and generates topic-driven animated explainers (Mode B).

## Tech Stack
- **Frontend:** Flutter Web (Dart) - Single-page responsive studio with timeline controls and real-time state management.
- **Backend Orchestrator:** Python FastAPI - Async processing jobs, media pipelines, and API layer.
- **Speech Engine:** `faster-whisper` for offline, word-level Hinglish transcription.
- **AI Reasoning:** Google Gemini API for transcript cleanup, technical keyword normalization, highlight scoring, and explainer script creation.
- **Vision & Layout:** OpenCV for active-window, code-editor, and speaker visual saliency detection.
- **Rendering:** Subprocess FFmpeg pipeline for crop, keyframe reframing, animated captions, and audio normalization.