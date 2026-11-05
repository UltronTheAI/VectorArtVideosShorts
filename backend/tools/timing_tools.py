from __future__ import annotations

import re
from dataclasses import dataclass


def seconds_to_frames(seconds: float, fps: int = 30) -> int:
    """Convert seconds to deterministic integer frames using nearest-frame rounding."""
    return max(0, int(round(seconds * fps)))


def frames_to_seconds(frames: int, fps: int = 30) -> float:
    return round(frames / fps, 6)


def estimate_narration_duration(text: str, words_per_minute: int = 145) -> float:
    words = len(re.findall(r"\b[\w'’-]+\b", text))
    pause_bonus = text.count("...") * 0.35 + text.count("!") * 0.06 + text.count("?") * 0.06
    return max(0.25, words / words_per_minute * 60 + pause_bonus)


@dataclass(frozen=True)
class TimingAdjustment:
    speed: float
    removed_pause_seconds: float
    regenerated: bool


def reconcile_duration(measured_seconds: float, requested_seconds: float, speed: float = 1.0) -> TimingAdjustment:
    if measured_seconds <= requested_seconds:
        return TimingAdjustment(speed=speed, removed_pause_seconds=0.0, regenerated=False)
    ratio = measured_seconds / requested_seconds
    safe_speed = min(1.2, max(speed, ratio))
    remaining = measured_seconds / safe_speed
    return TimingAdjustment(speed=round(safe_speed, 3), removed_pause_seconds=max(0.0, measured_seconds - remaining), regenerated=True)

