from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    fps: int = int(os.getenv("VECTORFORGE_FPS", "30"))
    ollama_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    tts_voice: str = os.getenv("KOKORO_VOICE", "am_michael")
    tts_speed: float = float(os.getenv("KOKORO_SPEED", "1.0"))
    tts_lang: str = os.getenv("KOKORO_LANG", "a")
    tts_model: str = os.getenv("KOKORO_MODEL", "Kokoro-82M")
    tts_model_version: str = os.getenv("KOKORO_MODEL_VERSION", "82M")
    tts_device: str = os.getenv("KOKORO_DEVICE", "cuda")
    kokoro_model_dir: str = os.getenv("KOKORO_MODEL_DIR", "")

    @property
    def outputs(self) -> Path:
        return self.root / "outputs"

    @property
    def generated(self) -> Path:
        return self.root / "public" / "generated"

    @property
    def audio(self) -> Path:
        return self.root / "public" / "audio"

    @property
    def sfx_dir(self) -> Path:
        return self.root / "assets" / "sfx"

    @property
    def manifest(self) -> Path:
        return self.sfx_dir / "manifest.json"

    def ensure_directories(self) -> None:
        for path in (self.outputs, self.generated, self.audio, self.sfx_dir, self.root / "assets" / "fonts"):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()

