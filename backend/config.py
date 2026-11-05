from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    fps: int = int(os.getenv("VIDEO_FPS", os.getenv("VECTORFORGE_FPS", "30")))
    ollama_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    tts_voice: str = os.getenv("KOKORO_VOICE", "am_michael")
    tts_speed: float = float(os.getenv("KOKORO_SPEED", "1.0"))
    tts_lang: str = os.getenv("KOKORO_LANG", "a")
    tts_model: str = os.getenv("KOKORO_MODEL", "Kokoro-82M")
    tts_model_version: str = os.getenv("KOKORO_MODEL_VERSION", "82M")
    tts_repo_id: str = os.getenv("KOKORO_REPO_ID", "hexgrad/Kokoro-82M")
    tts_device: str = os.getenv("KOKORO_DEVICE", "auto")
    kokoro_model_dir: str = os.getenv("KOKORO_MODEL_DIR", "")
    audio_sample_rate: int = int(os.getenv("AUDIO_SAMPLE_RATE", "48000"))
    audio_channels: int = int(os.getenv("AUDIO_CHANNELS", "2"))
    narration_volume: float = float(os.getenv("NARRATION_VOLUME", "1.0"))
    sfx_volume: float = float(os.getenv("SFX_VOLUME", "0.35"))
    music_volume: float = float(os.getenv("MUSIC_VOLUME", "0.12"))
    music_ducking_enabled: bool = os.getenv("MUSIC_DUCKING_ENABLED", "true").lower() in {"1", "true", "yes"}
    music_enabled: bool = os.getenv("MUSIC_ENABLED", "false").lower() in {"1", "true", "yes"}
    audio_required: bool = os.getenv("AUDIO_REQUIRED", "true").lower() in {"1", "true", "yes"}
    freesound_api_key: str = os.getenv("FREESOUND_API_KEY", "")
    freesound_access_token: str = os.getenv("FREESOUND_ACCESS_TOKEN", "")
    pixabay_api_key: str = os.getenv("PIXABAY_API_KEY", "")

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
    def sfx_cache(self) -> Path:
        return self.sfx_dir / "cache"

    @property
    def music_dir(self) -> Path:
        return self.root / "assets" / "music"

    @property
    def music_cache(self) -> Path:
        return self.music_dir / "cache"

    @property
    def manifest(self) -> Path:
        return self.sfx_dir / "manifest.json"

    def ensure_directories(self) -> None:
        for path in (self.outputs, self.generated, self.audio, self.sfx_dir, self.sfx_cache, self.music_dir, self.music_cache, self.root / "assets" / "fonts"):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()

