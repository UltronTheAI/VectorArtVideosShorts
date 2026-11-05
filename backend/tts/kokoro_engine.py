from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import os
import wave
from pathlib import Path

import numpy as np

from backend.audio.mixer import write_wav
from backend.config import settings

log = logging.getLogger(__name__)
SUPPORTED_VOICES = {"am_michael", "am_adam"}


class KokoroError(RuntimeError):
    """A required local speech generation step failed."""


class KokoroUnavailable(KokoroError):
    pass


class KokoroEngine:
    def __init__(self, voice: str | None = None, speed: float | None = None, output_dir: str | Path | None = None, device: str | None = None):
        self.voice = voice or settings.tts_voice
        self.speed = float(speed or settings.tts_speed)
        self.device = (device or settings.tts_device).lower()
        self.output_dir = Path(output_dir or settings.audio).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.voice not in SUPPORTED_VOICES:
            raise KokoroError(f"Unsupported Kokoro voice {self.voice!r}. Use one of: {', '.join(sorted(SUPPORTED_VOICES))}.")
        if not 0.5 < self.speed <= 1.5:
            raise KokoroError("Kokoro speed must be between 0.5 and 1.5.")

    @property
    def available(self) -> bool:
        return importlib.util.find_spec("kokoro") is not None

    @property
    def offline(self) -> bool:
        return os.getenv("KOKORO_OFFLINE", "1").lower() not in {"0", "false", "no"}

    def resolve_device(self) -> str:
        """Follow the proven Kokoro setup: use CUDA only when PyTorch exposes it."""
        if self.device in {"auto", "default"}:
            requested = "auto"
        else:
            requested = self.device
        try:
            import torch
            cuda_available = bool(torch.cuda.is_available())
        except Exception:
            cuda_available = False
        if requested == "cuda" and not cuda_available:
            log.warning("KOKORO_DEVICE=cuda was requested but CUDA is unavailable; using CPU.")
            return "cpu"
        if requested == "auto":
            return "cuda" if cuda_available else "cpu"
        if requested not in {"cpu", "cuda", "mps"}:
            raise KokoroError(f"Unsupported KOKORO_DEVICE={self.device!r}; use auto, cpu, cuda, or mps.")
        return requested

    def initialize(self) -> None:
        if not self.available:
            raise KokoroUnavailable(
                "Kokoro is not installed. Install the local package, PyTorch, soundfile, and espeak-ng; "
                "see README.md for Windows setup instructions."
            )
        configured_cache = Path(settings.kokoro_model_dir) if settings.kokoro_model_dir else None
        configured_has_model = self._cache_contains_model(configured_cache) if configured_cache else False
        if configured_has_model:
            os.environ["HF_HOME"] = str(configured_cache)
        elif configured_cache and self.offline:
            # Do not hide a working default Hugging Face cache behind an empty
            # custom directory. The standalone Kokoro setup commonly uses the
            # default cache under the user's profile.
            log.warning("KOKORO_MODEL_DIR=%s has no cached %s; using the default Hugging Face cache.", configured_cache, settings.tts_repo_id)
        if self.offline:
            os.environ["HF_HUB_OFFLINE"] = "1"

    @staticmethod
    def _cache_contains_model(cache_root: Path | None) -> bool:
        if not cache_root:
            return False
        repo_folder = settings.tts_repo_id.replace("/", "--")
        candidates = [
            cache_root / "hub" / f"models--{repo_folder}",
            cache_root / f"models--{repo_folder}",
        ]
        return any(candidate.exists() and any(candidate.rglob("*.json")) for candidate in candidates)

    def _cache_path(self, text: str, pause_after_ms: int = 0, delivery: str = "neutral") -> Path:
        payload = {
            "text": text, "voice": self.voice, "speed": self.speed,
            "model": settings.tts_model, "model_version": settings.tts_model_version, "repo_id": settings.tts_repo_id,
            "lang": settings.tts_lang, "device": self.resolve_device(), "pause_after_ms": pause_after_ms, "delivery": delivery,
        }
        key = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        return self.output_dir / f"tts-{key}.wav"

    @staticmethod
    def _validate_wav(path: Path) -> float:
        try:
            with wave.open(str(path), "rb") as handle:
                if handle.getnchannels() < 1 or handle.getframerate() <= 0 or handle.getnframes() <= 0:
                    raise KokoroError(f"Invalid or empty cached WAV: {path}")
                channels = handle.getnchannels()
                frames = handle.readframes(handle.getnframes())
                rate = handle.getframerate()
            samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            if samples.size == 0 or not np.isfinite(samples).all() or float(np.max(np.abs(samples))) < 1e-4:
                raise KokoroError(f"Cached WAV is silent or corrupt and will be regenerated: {path}")
            return samples.size / (rate * channels)
        except (OSError, wave.Error, ValueError) as exc:
            raise KokoroError(f"Cannot read cached narration WAV {path}: {exc}") from exc

    @staticmethod
    def _prepare_text(text: str, pause_after_ms: int, delivery: str) -> str:
        prepared = text.strip()
        if not prepared:
            raise KokoroError("Cannot synthesize an empty narration segment.")
        if delivery in {"energetic", "urgent"} and not prepared.endswith(("!", "?", ".")):
            prepared += "!"
        if pause_after_ms >= 100:
            prepared += " " + ("..." if pause_after_ms < 500 else "... ...")
        return prepared

    @staticmethod
    def _is_missing_local_model_error(error: Exception) -> bool:
        message = str(error).lower()
        return "local cache" in message or "cannot find the requested files" in message or "offline mode" in message

    def _generate_audio(self, prepared: str) -> np.ndarray:
        from kokoro import KPipeline
        pipeline = KPipeline(lang_code=settings.tts_lang, repo_id=settings.tts_repo_id, device=self.resolve_device())
        chunks = [audio for _, _, audio in pipeline(prepared, voice=self.voice, speed=self.speed, split_pattern=r"\n+")]
        if not chunks:
            raise KokoroError("Kokoro returned no audio chunks.")
        return np.concatenate(chunks).astype(np.float32)

    def synthesize(self, text: str, pause_after_ms: int = 0, delivery: str = "neutral") -> tuple[Path, float, bool]:
        self.initialize()
        prepared = self._prepare_text(text, pause_after_ms, delivery)
        path = self._cache_path(prepared, pause_after_ms, delivery)
        if path.exists():
            try:
                return path, self._validate_wav(path), True
            except KokoroError:
                path.unlink(missing_ok=True)
        try:
            try:
                audio = self._generate_audio(prepared)
            except Exception as first_error:
                if not self.offline or not self._is_missing_local_model_error(first_error):
                    raise
                log.warning("Kokoro weights are absent from the offline cache; retrying first-run model setup with Hub access.")
                os.environ.pop("HF_HUB_OFFLINE", None)
                audio = self._generate_audio(prepared)
            write_wav(path, audio, 24000)
            duration = self._validate_wav(path)
            return path, duration, False
        except KokoroError:
            raise
        except Exception as exc:
            path.unlink(missing_ok=True)
            raise KokoroError(
                f"Kokoro synthesis failed for voice {self.voice}: {exc}. Verify cached Kokoro-82M weights, "
                "espeak-ng, and the selected voice."
            ) from exc

    def synthesize_segments(self, segments: list[dict]) -> list[dict]:
        output: list[dict] = []
        for segment in segments:
            voice = segment.get("voice", self.voice)
            engine = self if voice == self.voice else KokoroEngine(voice=voice, speed=segment.get("speed", self.speed), output_dir=self.output_dir, device=self.device)
            path, duration, cached = engine.synthesize(
                segment["text"], pause_after_ms=int(segment.get("pause_after_ms", 0)),
                delivery=segment.get("delivery", "neutral"),
            )
            output.append({**segment, "audio_path": str(path), "measured_duration_second": duration, "cached": cached, "voice": voice})
        return output
