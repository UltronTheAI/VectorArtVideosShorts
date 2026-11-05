from __future__ import annotations

import hashlib
import importlib.util
import logging
import os
import re
from pathlib import Path

import numpy as np

from backend.audio.mixer import write_wav
from backend.config import settings

log = logging.getLogger(__name__)


class KokoroUnavailable(RuntimeError):
    pass


class KokoroEngine:
    def __init__(self, voice: str | None = None, speed: float | None = None, output_dir: str | Path | None = None):
        self.voice = voice or settings.tts_voice
        self.speed = speed or settings.tts_speed
        self.output_dir = Path(output_dir or settings.audio)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def available(self) -> bool:
        return importlib.util.find_spec("kokoro") is not None

    @property
    def model_download_allowed(self) -> bool:
        # Kokoro may attempt a large Hugging Face download on first import. Keep
        # the CLI deterministic/offline by requiring an explicit opt-in.
        return os.getenv("VECTORFORGE_KOKORO_ALLOW_DOWNLOAD", "0").lower() in {"1", "true", "yes"}

    def _cache_path(self, text: str) -> Path:
        key = hashlib.sha256(f"{text}|{self.voice}|{self.speed}|Kokoro-82M".encode()).hexdigest()[:20]
        return self.output_dir / f"tts-{key}.wav"

    def synthesize(self, text: str, filename: str | None = None, allow_placeholder: bool = True) -> tuple[Path, float, bool]:
        path = self.output_dir / filename if filename else self._cache_path(text)
        if path.exists():
            from backend.audio.sfx_library import index_audio_duration
            return path, index_audio_duration(path), True
        if self.available and self.model_download_allowed:
            try:
                from kokoro import KPipeline
                pipeline = KPipeline(lang_code=settings.tts_lang)
                chunks = [audio for _, _, audio in pipeline(text, voice=self.voice, speed=self.speed, split_pattern=r"\n+")]
                if chunks:
                    audio = np.concatenate(chunks).astype(np.float32)
                    write_wav(path, audio, 24000)
                    return path, len(audio) / 24000, False
            except Exception as exc:
                log.warning("Kokoro generation failed: %s", exc)
        if not allow_placeholder:
            raise KokoroUnavailable("Kokoro is not installed or failed to generate audio")
        # This is intentionally a quiet timing placeholder, never used as a sound effect.
        words = len(re.findall(r"\b\w+\b", text))
        duration = max(0.5, words / 145 * 60)
        write_wav(path, np.zeros(int(duration * 24000), dtype=np.float32), 24000)
        return path, duration, False

    def synthesize_segments(self, segments: list[dict]) -> list[dict]:
        output = []
        for segment in segments:
            path, duration, cached = self.synthesize(segment["text"], filename=f"{segment['id']}.wav")
            output.append({**segment, "audio_path": str(path), "measured_duration_second": duration, "cached": cached})
        return output

