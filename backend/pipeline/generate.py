from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from backend.agents.graph import generation_graph
from backend.agents.validator import validate_project
from backend.audio.mixer import mix_audio
from backend.config import settings
from backend.schemas import AspectRatio, NarrationSegment, Project, Resolution
from backend.tools.timing_tools import seconds_to_frames
from backend.tts.kokoro_engine import KokoroEngine

log = logging.getLogger(__name__)


def resolution_for(aspect: str) -> Resolution:
    return Resolution(width=1080, height=1920) if aspect == "9:16" else Resolution(width=1920, height=1080)


def build_project(prompt: str, output_dir: str | Path | None = None, use_llm: bool = False, generate_audio: bool = True, aspect: str | None = None) -> Project:
    settings.ensure_directories()
    result = generation_graph.invoke({"prompt": prompt, "use_llm": use_llm})
    plan = result["plan"]
    target_aspect = aspect or plan.get("format", "16:9")
    if target_aspect == "both":
        target_aspect = "16:9"
    segments_data = result["segments"]
    project_id = f"vf-{uuid.uuid4().hex[:10]}"
    if generate_audio:
        segments_data = KokoroEngine().synthesize_segments(segments_data)
    segments = [NarrationSegment(
        id=item["id"], text=item["text"], start_second=item["start_second"],
        duration_second=float(item.get("measured_duration_second", item["duration_second"])),
        audio_path=item.get("audio_path"), emotion="excitement" if "energetic" in plan.get("tone", []) else "neutral",
    ) for item in segments_data]
    # Once audio exists, measured segment durations—not word-count estimates—own
    # the timeline. Re-pack segments sequentially so subtitles and scenes cannot
    # drift because an individual TTS segment took longer than predicted.
    measured_cursor = 0.0
    for segment in segments:
        segment.start_second = round(measured_cursor, 6)
        measured_cursor += segment.duration_second
    actual_duration = max(measured_cursor, 0.1)
    # Normalize scene timeline to measured duration while preserving ordering.
    scenes = result["scenes"]
    scale = actual_duration / max(0.01, plan["duration_second"])
    cursor = 0
    for index, scene in enumerate(scenes):
        scene.start_frame = cursor
        remaining_scenes = len(scenes) - index - 1
        scaled_frames = max(settings.fps, seconds_to_frames(scene.duration_frames / settings.fps * scale, settings.fps))
        if index == len(scenes) - 1:
            scene.duration_frames = max(settings.fps, seconds_to_frames(actual_duration, settings.fps) - cursor)
        else:
            scene.duration_frames = min(scaled_frames, max(settings.fps, seconds_to_frames(actual_duration, settings.fps) - cursor - remaining_scenes * settings.fps))
        cursor += scene.duration_frames
    actual_duration = max(actual_duration, cursor / settings.fps)
    subtitles = []
    for segment in segments:
        subtitles.append({"id": segment.id, "text": segment.text, "start_frame": seconds_to_frames(segment.start_second, settings.fps), "end_frame": seconds_to_frames(segment.start_second + segment.duration_second, settings.fps)})
    project = Project(
        project_id=project_id, title="How Does a Database Index Work?" if "database" in plan["topic"].lower() else plan["topic"].title(),
        original_prompt=prompt, requested_duration_second=float(plan["duration_second"]), actual_duration_second=max(0.1, actual_duration),
        fps=settings.fps, resolution=resolution_for(target_aspect), aspect_ratio=AspectRatio(target_aspect),
        narrator={"voice": plan.get("voice", settings.tts_voice), "speed": settings.tts_speed}, script=result["script"], scenes=scenes,
        narration_segments=segments, subtitles=subtitles, metadata={"plan": plan, "audio_placeholder_allowed": True},
    )
    if generate_audio and all(segment.audio_path for segment in segments):
        voice_path = settings.audio / f"{project_id}-voice.wav"
        mix_audio(str(segments[0].audio_path), [(str(segment.audio_path), segment.start_second, 1.0) for segment in segments[1:]], voice_path)
        project.metadata["mixed_audio_path"] = str(voice_path)
    return validate_project(project)


def save_project(project: Project, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(project.model_dump(mode="json"), indent=2), encoding="utf-8")
    return target


def generate_project(prompt: str, project_path: str | Path, use_llm: bool = False, generate_audio: bool = True, aspect: str | None = None) -> Project:
    project = build_project(prompt, use_llm=use_llm, generate_audio=generate_audio, aspect=aspect)
    save_project(project, project_path)
    return project

