from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from backend.config import settings

log = logging.getLogger(__name__)


class AudioMixError(RuntimeError):
    pass


@dataclass(frozen=True)
class AudioClip:
    path: str | Path
    start_second: float
    volume: float = 1.0
    track: str = "narration"
    fade_in_ms: int = 0
    fade_out_ms: int = 0


def _read_soundfile(path: Path) -> tuple[np.ndarray, int]:
    try:
        import soundfile as sf
        data, rate = sf.read(str(path), always_2d=True, dtype="float32")
        return np.asarray(data, dtype=np.float32), int(rate)
    except Exception as exc:
        raise AudioMixError(str(exc)) from exc


def read_audio(path: str | Path, sample_rate: int | None = None) -> tuple[np.ndarray, int]:
    source = Path(path)
    if not source.exists():
        raise AudioMixError(f"Audio asset is missing: {source}")
    target_rate = sample_rate or settings.audio_sample_rate
    try:
        audio, rate = _read_soundfile(source)
    except AudioMixError:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise AudioMixError(f"Cannot decode {source.suffix}; install FFmpeg or use WAV/OGG supported by SoundFile.")
        with tempfile.TemporaryDirectory(prefix="vectorforge-audio-") as temp:
            decoded = Path(temp) / "decoded.wav"
            result = subprocess.run([ffmpeg, "-y", "-i", str(source), "-ar", str(target_rate), "-ac", str(settings.audio_channels), str(decoded)], capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise AudioMixError(f"FFmpeg could not decode {source}: {result.stderr[-1000:]}")
            audio, rate = _read_soundfile(decoded)
    if rate != target_rate:
        old_x = np.linspace(0, 1, num=len(audio), endpoint=False)
        new_len = max(1, round(len(audio) * target_rate / rate))
        new_x = np.linspace(0, 1, num=new_len, endpoint=False)
        audio = np.stack([np.interp(new_x, old_x, audio[:, channel]) for channel in range(audio.shape[1])], axis=1).astype(np.float32)
        rate = target_rate
    if audio.size == 0 or not np.isfinite(audio).all():
        raise AudioMixError(f"Audio file is empty or corrupt: {source}")
    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)
    elif audio.shape[1] > 2:
        audio = audio[:, :2]
    return audio, rate


def audio_stats(path: str | Path) -> dict[str, float | int | bool]:
    audio, rate = read_audio(path)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    rms = float(np.sqrt(np.mean(np.square(audio)))) if audio.size else 0.0
    return {"sample_rate": rate, "channels": int(audio.shape[1]), "duration_second": len(audio) / rate, "peak": peak, "rms": rms, "silent": peak < 1e-4 or rms < 1e-5}


def validate_audio_file(path: str | Path, *, require_audible: bool = False) -> dict[str, float | int | bool]:
    stats = audio_stats(path)
    if require_audible and bool(stats["silent"]):
        raise AudioMixError(f"Audio is effectively silent: {path}")
    return stats


def write_wav(path: str | Path, audio: np.ndarray, sample_rate: int | None = None) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    rate = sample_rate or settings.audio_sample_rate
    data = np.asarray(audio, dtype=np.float32)
    if data.ndim == 1:
        data = data[:, None]
    if data.shape[1] == 1 and settings.audio_channels == 2:
        data = np.repeat(data, 2, axis=1)
    data = np.clip(data, -0.98, 0.98)
    try:
        import soundfile as sf
        sf.write(str(target), data, rate, subtype="PCM_16")
    except Exception:
        pcm = (data * 32767).astype(np.int16)
        with wave.open(str(target), "wb") as handle:
            handle.setnchannels(data.shape[1])
            handle.setsampwidth(2)
            handle.setframerate(rate)
            handle.writeframes(pcm.tobytes())


def _apply_clip_fades(data: np.ndarray, clip: AudioClip, rate: int) -> np.ndarray:
    result = data.copy()
    if clip.fade_in_ms:
        frames = min(len(result), round(clip.fade_in_ms * rate / 1000))
        result[:frames] *= np.linspace(0, 1, frames)[:, None]
    if clip.fade_out_ms:
        frames = min(len(result), round(clip.fade_out_ms * rate / 1000))
        result[-frames:] *= np.linspace(1, 0, frames)[:, None]
    return result


def _mix(clips: list[AudioClip], duration_second: float, sample_rate: int, *, duck_ranges: list[tuple[int, int]] | None = None) -> np.ndarray:
    total_frames = max(1, round(duration_second * sample_rate))
    mix = np.zeros((total_frames, 2), dtype=np.float32)
    for clip in clips:
        if clip.start_second < 0 or clip.volume < 0:
            raise AudioMixError(f"Invalid audio clip timing or volume: {clip}")
        data, rate = read_audio(clip.path, sample_rate)
        start = round(clip.start_second * rate)
        end = min(total_frames, start + len(data))
        if end <= start:
            continue
        data = _apply_clip_fades(data[: end - start], clip, rate) * float(clip.volume)
        if clip.track == "music" and duck_ranges and settings.music_ducking_enabled:
            gain = np.ones(len(data), dtype=np.float32)
            for left, right in duck_ranges:
                overlap_left = max(start, left) - start
                overlap_right = min(end, right) - start
                if overlap_right > overlap_left:
                    gain[overlap_left:overlap_right] *= 0.28
            data *= gain[:, None]
        mix[start:end] += data
    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    if peak > 0.95:
        mix *= 0.95 / peak
    return mix


def mix_tracks(narration: list[AudioClip], effects: list[AudioClip], output_dir: str | Path, duration_second: float, sample_rate: int | None = None, reaction: list[AudioClip] | None = None, music: list[AudioClip] | None = None) -> dict[str, Path | float | dict]:
    if not narration:
        raise AudioMixError("At least one real narration clip is required.")
    rate = sample_rate or settings.audio_sample_rate
    for clip in narration:
        validate_audio_file(clip.path, require_audible=True)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    narration_ranges = [(round(clip.start_second * rate), round((clip.start_second + audio_stats(clip.path)["duration_second"]) * rate)) for clip in narration]
    narration_audio = _mix(narration, duration_second, rate)
    final_audio = _mix(narration + effects + (reaction or []) + (music or []), duration_second, rate, duck_ranges=narration_ranges)
    narration_path = target_dir / "narration.wav"
    final_path = target_dir / "final_audio.wav"
    write_wav(narration_path, narration_audio, rate)
    write_wav(final_path, final_audio, rate)
    narration_stats = validate_audio_file(narration_path, require_audible=True)
    final_stats = validate_audio_file(final_path, require_audible=True)
    log.info("Audio timeline composed: narration=%s final=%s duration=%.3fs peak=%.3f", narration_path, final_path, duration_second, final_stats["peak"])
    return {"narration_path": narration_path, "final_audio_path": final_path, "duration_second": duration_second, "narration_stats": narration_stats, "final_stats": final_stats}


def mix_audio(voice_path: str | Path, clips: list[tuple[str | Path, float, float]], output_path: str | Path, duration_second: float | None = None, fade_seconds: float = 0.04) -> float:
    """Compatibility wrapper using the authoritative multitrack mixer."""
    stats = audio_stats(voice_path)
    duration = duration_second or float(stats["duration_second"])
    effects = [AudioClip(path, start, volume, "sfx") for path, start, volume in clips]
    result = mix_tracks([AudioClip(voice_path, 0, settings.narration_volume, "narration")], effects, Path(output_path).parent, duration)
    source = Path(result["final_audio_path"])
    if source.resolve() != Path(output_path).resolve():
        source.replace(output_path)
    return float(result["duration_second"])
