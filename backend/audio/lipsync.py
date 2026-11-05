from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from backend.audio.mixer import read_audio
from backend.schemas import LipSyncSample


def _viseme(open_amount: float, speech_active: bool) -> str:
    if not speech_active or open_amount < 0.08:
        return "closed"
    if open_amount < 0.28:
        return "mbp"
    if open_amount < 0.52:
        return "open"
    if open_amount < 0.75:
        return "wide"
    return "rounded"


def analyze_lip_sync(path: str | Path, fps: int, duration_second: float, window_ms: int = 30, hop_ms: int = 30) -> list[LipSyncSample]:
    """Create deterministic amplitude-driven mouth samples from real narration audio.

    This intentionally does not claim phoneme alignment. Viseme labels are coarse
    placeholders for a future forced-aligner integration.
    """
    audio, rate = read_audio(path)
    mono = audio.mean(axis=1)
    window = max(1, round(rate * window_ms / 1000))
    hop = max(1, round(rate * hop_ms / 1000))
    rms_values: list[float] = []
    for start in range(0, max(1, len(mono) - window + 1), hop):
        chunk = mono[start:start + window]
        rms_values.append(float(np.sqrt(np.mean(np.square(chunk)))) if len(chunk) else 0.0)
    if not rms_values:
        return []
    noise_floor = float(np.percentile(rms_values, 25))
    speech_threshold = max(0.012, noise_floor * 1.8)
    peak = max(rms_values) or 1.0
    total_frames = max(1, round(duration_second * fps))
    samples: list[LipSyncSample] = []
    last = 0.0
    for index, rms in enumerate(rms_values):
        raw = max(0.0, min(1.0, (rms - speech_threshold) / max(1e-5, peak - speech_threshold)))
        smoothed = last * 0.55 + raw * 0.45
        last = smoothed
        frame = min(total_frames - 1, round(index * hop / rate * fps))
        active = rms >= speech_threshold
        samples.append(LipSyncSample(frame=frame, mouth_open=smoothed if active else 0.0, speech_active=active, viseme=_viseme(smoothed, active)))
    return samples
