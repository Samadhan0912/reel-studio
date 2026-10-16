"""Small, explicit adapter around Google's Gemini API."""
from __future__ import annotations

import base64
import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from app.config import settings


class GeminiNotConfigured(RuntimeError):
    pass


BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def _request(url: str, *, data: bytes | None = None, headers: dict[str, str] | None = None, timeout: int = 600):
    request = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data is not None else "GET")
    try:
        return urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(details)
            message = parsed.get("error", {}).get("message", details)
        except (ValueError, AttributeError):
            message = details
        raise RuntimeError(f"Gemini API error ({exc.code}): {message[:600]}") from exc
    except urllib.error.URLError as exc:
        message = str(exc.reason).replace(settings.gemini_api_key, "[redacted]")
        raise RuntimeError(f"Gemini connection failed: {message[:300]}") from exc
    except (TimeoutError, ConnectionError, OSError) as exc:
        message = str(exc).replace(settings.gemini_api_key, "[redacted]")
        raise RuntimeError(f"Gemini connection failed: {message[:300]}") from exc


def _api_url(path: str, **params: str) -> str:
    if not settings.gemini_api_key:
        raise GeminiNotConfigured("Set GEMINI_API_KEY in backend/.env to run AI jobs.")
    query = urllib.parse.urlencode({"key": settings.gemini_api_key, **params})
    return f"{BASE_URL}/{path}?{query}"


def _json_from_response(response: dict[str, Any], *, array_key: str | None = None) -> dict[str, Any]:
    candidates = response.get("candidates", [])
    text = "".join(part.get("text", "") for candidate in candidates for part in candidate.get("content", {}).get("parts", [])).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    if not text:
        reasons = ", ".join(str(candidate.get("finishReason")) for candidate in candidates if candidate.get("finishReason"))
        block = response.get("promptFeedback", {}).get("blockReason")
        details = f" Finish reason: {reasons}." if reasons else ""
        details += f" Prompt block: {block}." if block else ""
        raise RuntimeError("Gemini returned no text for its JSON response." + details)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini returned a response that was not valid JSON.") from exc
    if isinstance(value, list) and array_key:
        return {array_key: value}
    if not isinstance(value, dict):
        raise RuntimeError(f"Gemini returned valid JSON with unsupported type '{type(value).__name__}'.")
    return value


def _generate(body: dict[str, Any], models: list[str], *, timeout: int = 600) -> dict[str, Any]:
    last_error: Exception | None = None
    for model in dict.fromkeys(models):
        for attempt in range(4):
            try:
                with _request(_api_url(f"models/{model}:generateContent"), data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, timeout=timeout) as response:
                    return json.loads(response.read())
            except RuntimeError as exc:
                last_error = exc
                if not any(code in str(exc).lower() for code in ("429", "500", "503", "504", "connection failed", "timed out")):
                    raise
                if attempt < 3:
                    # Google's REST API guidance recommends exponential backoff
                    # with jitter for transient 429/5xx responses.
                    time.sleep(min(8, 2 ** attempt) + random.uniform(0, 0.5))
    assert last_error is not None
    raise last_error


def generate_json(prompt: str, *, model: str | None = None) -> dict[str, Any]:
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.25}}
    response = _generate(body, [model or settings.gemini_model, "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"])
    return _json_from_response(response)


def analyze_transcript(transcript: str, *, language: str, vocabulary: list[str], target_seconds: int,
                       max_clips: int, duration_seconds: float) -> dict[str, Any]:
    """Send only a local ASR transcript and its timestamps to Gemini for edit selection."""
    if not transcript.strip():
        raise RuntimeError("Local transcription returned no transcript to analyze.")
    terms = ", ".join(vocabulary) if vocabulary else "No user glossary was supplied"
    prompt = f"""You are an educational video editor. Analyze ONLY this locally generated timestamped transcript; the source video is not provided to you.
Language: {language}. Technical vocabulary with exact spelling: {terms}.
Video duration: {duration_seconds:.2f} seconds. Select up to {max_clips} strong, standalone teaching moments, preferably {max(30, target_seconds-10)}–{min(60, target_seconds+10)} seconds each.
Choose ranges that begin and end on complete thoughts. Avoid greetings, pauses, repeated ideas, and fragments. Use boundaries supported by transcript timestamps and keep every range inside the video duration. You may overlap clips only when they are clearly distinct.
For each selection return a concise title, start_seconds, end_seconds, and a short reason. Do not rewrite the transcript, invent visual content, or return word timings.
Timestamped transcript follows (timestamps are source-video seconds):
{transcript[:80000]}

Return ONLY JSON: {{"clips":[{{"title":"...","start_seconds":12.3,"end_seconds":54.2,"reason":"...","score":0.9}}]}}. Return an empty clips array if there is no suitable complete thought."""
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.15}}
    response = _generate(body, [settings.gemini_model, "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"], timeout=600)
    return _json_from_response(response, array_key="clips")


def generate_explainer(topic: str, audience: str, duration: int, language: str, vocabulary: list[str] | None = None) -> dict[str, Any]:
    terms = ", ".join(vocabulary or []) or "spell technical terms correctly"
    return generate_json(f"""Create a short educational vertical-video explainer.
Topic: {topic}; audience: {audience}; target duration: {duration} seconds; language: {language}; glossary: {terms}.
Write natural spoken words and a scene-by-scene storyboard. Include a compelling hook, one simple example, and a concise recap.
Keep the spoken script to at most {round(duration * 2.2)} words so a natural voiceover fits the requested duration. For coding topics, provide concise code snippets, never invent APIs.
Return JSON with keys title, script, scenes (array of {{at_seconds, text, code}}), and captions (array of {{start_seconds,end_seconds,text}}).
Captions should be phrase-sized, timed across the requested duration, and preserve exact technical spellings.""")


def synthesize_speech(text: str, output_path: Path) -> bool:
    """Create WAV narration when the configured Gemini TTS model is available."""
    if not settings.enable_generated_audio or not text.strip():
        return False
    body = {
        "contents": [{"parts": [{"text": f"Say the following script clearly and naturally, with an upbeat educational delivery. Read it verbatim:\n{text}"}]}],
        "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}}},
    }
    data = _generate(body, [settings.gemini_tts_model, "gemini-2.5-flash-preview-tts"], timeout=600)
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data") or {}
            if inline.get("data"):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(base64.b64decode(inline["data"]))
                return True
    return False
