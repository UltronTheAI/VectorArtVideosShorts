from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


def read_wav(path: str | Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as handle:
        rate = handle.getframerate()
        channels = handle.getnchannels()
        frames = handle.readframes(handle.getnframes())
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio, rate


def write_wav(path: str | Path, audio: np.ndarray, sample_rate: int = 24000) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(audio, -0.98, 0.98)
    pcm = (clipped * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())


def mix_audio(voice_path: str | Path, sfx: list[tuple[str | Path, float, float]], output_path: str | Path, fade_seconds: float = 0.04) -> float:
    voice, rate = read_wav(voice_path)
    loaded_effects: list[tuple[np.ndarray, int, float]] = []
    required_length = len(voice)
    for path, start_second, volume in sfx:
        effect, effect_rate = read_wav(path)
        if effect_rate != rate:
            continue
        start = max(0, int(start_second * rate))
        loaded_effects.append((effect, start, volume))
        required_length = max(required_length, start + len(effect))
    mix = np.zeros(required_length, dtype=np.float32)
    mix[:len(voice)] += voice
    for effect, start, volume in loaded_effects:
        end = min(len(mix), start + len(effect))
        if end > start:
            mix[start:end] += effect[: end - start] * volume
    fade = min(int(fade_seconds * rate), len(mix) // 2)
    if fade:
        mix[:fade] *= np.linspace(0, 1, fade)
        mix[-fade:] *= np.linspace(1, 0, fade)
    peak = float(np.max(np.abs(mix))) if len(mix) else 0
    if peak > 0.98:
        mix *= 0.98 / peak
    write_wav(output_path, mix, rate)
    return len(mix) / rate

