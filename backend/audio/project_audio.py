from __future__ import annotations

import json
from pathlib import Path

from backend.audio.mixer import AudioClip, AudioMixError, mix_tracks
from backend.config import settings
from backend.schemas import Project


def mix_project_audio(project: Project) -> Project:
    narration = [AudioClip(event.path, event.start_ms / 1000, event.volume, "narration") for event in project.audio_events if event.type == "narration"]
    effects = [AudioClip(event.path, event.start_ms / 1000, event.volume, event.type) for event in project.audio_events if event.type in {"sfx", "reaction"}]
    music = [AudioClip(event.path, event.start_ms / 1000, event.volume, "music") for event in project.audio_events if event.type == "music"]
    project_dir = Path(project.metadata.get("project_dir", settings.outputs / project.project_id))
    mixed = mix_tracks(narration, effects, project_dir, project.actual_duration_second, music=music)
    project.metadata["narration_path"] = str(mixed["narration_path"])
    project.metadata["mixed_audio_path"] = str(mixed["final_audio_path"])
    project.metadata["audio_ready"] = True
    return project


def save_project_json(project: Project) -> Path:
    target = Path(project.metadata.get("project_dir", settings.outputs / project.project_id)) / "project.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(project.model_dump(mode="json"), indent=2), encoding="utf-8")
    return target
