from __future__ import annotations

import logging
import shutil
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)


class AudioMixError(RuntimeError):
    pass


@dataclass(frozen=True)
class AudioClip:
    path: str | Path
    start_second: float
    volume: float = 1.0
    track: str = "narration"


def _read_with_soundfile(path: Path) -> tuple[np.ndarray, int]:
    try:
        import soundfile as sf
        data, rate = sf.read(str(path), always_2d=True, dtype="float32")
        return np.asarray(data, dtype=np.float32), int(rate)
    except Exception as exc:
        raise AudioMixError(f"Unable to decode audio file {path}: {exc}") from exc


def read_audio(path: str | Path, sample_rate: int = 24000) -> tuple[np.ndarray, int]:
    source = Path(path)
    if not source.exists():
        raise AudioMixError(f"Audio asset is missing: {source}")
    try:
        audio, rate = _read_with_soundfile(source)
    except AudioMixError:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise AudioMixError(f"{source.suffix} decoding requires SoundFile support or FFmpeg on PATH.")
        import tempfile
        with tempfile.TemporaryDirectory(prefix="vectorforge-audio-") as temp:
            decoded = Path(temp) / "decoded.wav"
            result = subprocess.run([ffmpeg, "-y", "-i", str(source), "-ar", str(sample_rate), "-ac", "2", str(decoded)], capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise AudioMixError(f"FFmpeg could not decode {source}: {result.stderr[-800:]}")
            audio, rate = _read_with_soundfile(decoded)
    if rate != sample_rate:
        old_x = np.linspace(0, 1, num=len(audio), endpoint=False)
        new_len = max(1, round(len(audio) * sample_rate / rate))
        new_x = np.linspace(0, 1, num=new_len, endpoint=False)
        audio = np.stack([np.interp(new_x, old_x, audio[:, channel]) for channel in range(audio.shape[1])], axis=1).astype(np.float32)
        rate = sample_rate
    if audio.size == 0 or not np.isfinite(audio).all():
        raise AudioMixError(f"Audio file is empty or corrupt: {source}")
    return audio, rate


def write_wav(path: str | Path, audio: np.ndarray, sample_rate: int = 24000) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = np.asarray(audio, dtype=np.float32)
    if data.ndim == 1:
        data = data[:, None]
    data = np.clip(data, -0.98, 0.98)
    try:
        import soundfile as sf
        sf.write(str(target), data, sample_rate, subtype="PCM_16")
    except Exception:
        pcm = (data * 32767).astype(np.int16)
        with wave.open(str(target), "wb") as handle:
            handle.setnchannels(data.shape[1])
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            handle.writeframes(pcm.tobytes())


def _mix(clips: list[AudioClip], duration_second: float, sample_rate: int, base_gain: float) -> np.ndarray:
    if duration_second <= 0:
        raise AudioMixError("Audio timeline duration must be positive.")
    total_frames = max(1, round(duration_second * sample_rate))
    mix = np.zeros((total_frames, 2), dtype=np.float32)
    for clip in clips:
        if clip.start_second < 0 or clip.volume < 0:
            raise AudioMixError(f"Invalid audio clip timing or volume: {clip}")
        data, rate = read_audio(clip.path, sample_rate)
        if rate != sample_rate:
            raise AudioMixError(f"Resampling failed for {clip.path}")
        if data.shape[1] == 1:
            data = np.repeat(data, 2, axis=1)
        start = round(clip.start_second * sample_rate)
        end = min(total_frames, start + len(data))
        if end > start:
            mix[start:end] += data[: end - start] * float(clip.volume) * base_gain
    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    if peak > 0.95:
        mix *= 0.95 / peak
    fade_frames = min(round(0.04 * sample_rate), total_frames // 2)
    if fade_frames:
        mix[:fade_frames] *= np.linspace(0, 1, fade_frames)[:, None]
        mix[-fade_frames:] *= np.linspace(1, 0, fade_frames)[:, None]
    return mix


def mix_tracks(narration: list[AudioClip], effects: list[AudioClip], output_dir: str | Path, duration_second: float, sample_rate: int = 24000, reaction: list[AudioClip] | None = None, music: list[AudioClip] | None = None) -> dict[str, Path | float]:
    if not narration:
        raise AudioMixError("At least one real narration clip is required.")
    for clip in narration:
        if not Path(clip.path).exists():
            raise AudioMixError(f"Narration clip is missing: {clip.path}")
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    narration_audio = _mix(narration, duration_second, sample_rate, base_gain=1.0)
    final_audio = _mix(narration + effects + (reaction or []) + (music or []), duration_second, sample_rate, base_gain=1.0)
    narration_path = target_dir / "narration.wav"
    final_path = target_dir / "final_audio.wav"
    write_wav(narration_path, narration_audio, sample_rate)
    write_wav(final_path, final_audio, sample_rate)
    log.info("Audio timeline composed: narration=%s final=%s duration=%.3fs", narration_path, final_path, duration_second)
    return {"narration_path": narration_path, "final_audio_path": final_path, "duration_second": duration_second}


def mix_audio(voice_path: str | Path, clips: list[tuple[str | Path, float, float]], output_path: str | Path, duration_second: float | None = None, fade_seconds: float = 0.04) -> float:
    """Compatibility wrapper: the first clip is narration, all remaining clips are effects."""
    first, rate = read_audio(voice_path)
    inferred = len(first) / rate
    duration = max(inferred, max((start + read_audio(path)[0].shape[0] / rate for path, start, _ in clips), default=0))
    result = mix_tracks([AudioClip(voice_path, 0, 1.0, "narration")], [AudioClip(path, start, volume, "sfx") for path, start, volume in clips], Path(output_path).parent, duration_second or duration, rate)
    Path(result["final_audio_path"]).replace(output_path)
    return float(result["duration_second"])
