"""Processing contracts and dispatch for asynchronous studio jobs.

Concrete AI providers are deliberately injected: API credentials and provider
choices belong to each deployment, and this module must never fake completed work.
"""
from typing import Any, Protocol


class JobProcessor(Protocol):
    def process(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class ProviderNotConfigured(RuntimeError):
    pass


class ProcessorRegistry:
    def __init__(self) -> None:
        self._processors: dict[str, JobProcessor] = {}

    def register(self, kind: str, processor: JobProcessor) -> None:
        self._processors[kind] = processor

    def run(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        processor = self._processors.get(kind)
        if processor is None:
            raise ProviderNotConfigured(
                f"No processor is configured for '{kind}'. Configure transcription, "
                "LLM/highlight, TTS, and/or rendering adapters for this job."
            )
        return processor.process(payload)


processors = ProcessorRegistry()
