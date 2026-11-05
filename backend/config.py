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
    llm_provider: str = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    groq_reasoning_effort: str = os.getenv("GROQ_REASONING_EFFORT", "medium").strip().lower()
    groq_timeout: int = int(os.getenv("GROQ_TIMEOUT", "120"))
    llm_fallback_provider: str = os.getenv("LLM_FALLBACK_PROVIDER", "ollama").strip().lower()
    llm_max_retries: int = max(0, int(os.getenv("LLM_MAX_RETRIES", "2")))
    llm_cache_enabled: bool = os.getenv("LLM_CACHE_ENABLED", "true").lower() in {"1", "true", "yes"}
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

    def __post_init__(self) -> None:
        if self.llm_provider not in {"groq", "ollama"}:
            raise ValueError("LLM_PROVIDER must be groq or ollama")
        if self.llm_fallback_provider not in {"", "groq", "ollama"}:
            raise ValueError("LLM_FALLBACK_PROVIDER must be empty, groq, or ollama")
        if self.groq_reasoning_effort not in {"low", "medium", "high"}:
            raise ValueError("GROQ_REASONING_EFFORT must be low, medium, or high")

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
    def llm_cache_dir(self) -> Path:
        return self.root / ".cache" / "vectorforge" / "llm"

    @property
    def manifest(self) -> Path:
        return self.sfx_dir / "manifest.json"

    def ensure_directories(self) -> None:
        for path in (self.outputs, self.generated, self.audio, self.sfx_dir, self.sfx_cache, self.music_dir, self.music_cache, self.llm_cache_dir, self.root / "assets" / "fonts"):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()

