from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from backend.agents.graph import generation_graph
from backend.agents.validator import validate_project
from backend.audio.mixer import AudioClip, AudioMixError, audio_stats, mix_tracks
from backend.audio.sfx_library import SfxLibrary
from backend.config import settings
from backend.schemas import AspectRatio, AudioAsset, AudioEvent, MusicConfig, NarrationSegment, Project, Resolution, SfxCue
from backend.tools.timing_tools import seconds_to_frames
from backend.tts.kokoro_engine import KokoroEngine

log = logging.getLogger(__name__)


def resolution_for(aspect: str) -> Resolution:
    return Resolution(width=1080, height=1920) if aspect == "9:16" else Resolution(width=1920, height=1080)


def _write_srt(project: Project, path: Path) -> None:
    def timestamp(seconds: float) -> str:
        whole = max(0, int(seconds))
        millis = max(0, int(round((seconds - whole) * 1000)))
        return f"{whole // 3600:02d}:{whole % 3600 // 60:02d}:{whole % 60:02d},{millis:03d}"
    lines: list[str] = []
    for index, subtitle in enumerate(project.subtitles, 1):
        lines += [str(index), f"{timestamp(subtitle.start_frame / project.fps)} --> {timestamp(subtitle.end_frame / project.fps)}", subtitle.text, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_artifacts(project: Project, project_dir: Path) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "project.json").write_text(json.dumps(project.model_dump(mode="json"), indent=2), encoding="utf-8")
    (project_dir / "script.json").write_text(json.dumps({"title": project.title, "script": project.script, "segments": [s.model_dump(mode="json") for s in project.narration_segments]}, indent=2), encoding="utf-8")
    _write_srt(project, project_dir / "subtitles.srt")
    (project_dir / "audio-manifest.json").write_text(json.dumps({"events": [event.model_dump(mode="json") for event in project.audio_events], "assets": [asset.model_dump(mode="json") for asset in project.audio_assets]}, indent=2), encoding="utf-8")
    (project_dir / "asset-attribution.json").write_text(json.dumps([asset.model_dump(mode="json") for asset in project.audio_assets if asset.attribution_required], indent=2), encoding="utf-8")


def _select_sfx(project_scenes, library: SfxLibrary) -> tuple[list[SfxCue], list[AudioAsset], list[str]]:
    cues: list[SfxCue] = []
    assets: list[AudioAsset] = []
    missing: list[str] = []
    for scene in project_scenes:
        requests = list(scene.sound_requests)
        if not requests:
            continue
        for index, request in enumerate(requests, 1):
            category = request.category
            asset = library.match(category, tags=request.description.split(), commercial_only=True)
            if not asset or not Path(asset.path).exists():
                missing.append(category)
                continue
            cue_id = f"cue-{scene.id}-{category}-{index}"
            cue = SfxCue(id=cue_id, asset_id=asset.id, category=category, start_second=scene.start_frame / settings.fps + request.at_ms / 1000, volume=request.volume * settings.sfx_volume, audio_path=asset.path)
            cues.append(cue)
            assets.append(asset)
            scene.sound_effect_ids.append(cue_id)
    return cues, assets, sorted(set(missing))


def build_project(prompt: str, output_dir: str | Path | None = None, use_llm: bool = False, generate_audio: bool = True, aspect: str | None = None) -> Project:
    settings.ensure_directories()
    result = generation_graph.invoke({"prompt": prompt, "use_llm": use_llm})
    plan = result["plan"]
    target_aspect = aspect or plan.get("format", "16:9")
    if target_aspect == "both":
        target_aspect = "16:9"
    if target_aspect not in {"16:9", "9:16"}:
        raise ValueError(f"Unsupported output format: {target_aspect}")
    project_id = f"vf-{uuid.uuid4().hex[:10]}"
    project_dir = Path(output_dir or (settings.outputs / project_id)).resolve()
    project_dir.mkdir(parents=True, exist_ok=True)
    segments_data = result["segments"]
    if generate_audio:
        # There is deliberately no silent or synthetic fallback here.
        segments_data = KokoroEngine(voice=plan.get("voice", settings.tts_voice), output_dir=project_dir).synthesize_segments(segments_data)
    segments = [NarrationSegment(
        id=item["id"], text=item["text"], start_second=0, duration_second=float(item.get("measured_duration_second", item["duration_second"])),
        audio_path=item.get("audio_path"), emotion="excitement" if "energetic" in plan.get("tone", []) else "neutral",
        delivery="energetic" if "energetic" in plan.get("tone", []) else "neutral", delivery_speed=float(item.get("speed", 1.0)),
        pause_after_ms=int(item.get("pause_after_ms", 0)), voice=item.get("voice", plan.get("voice", settings.tts_voice)),
    ) for item in segments_data]
    if generate_audio and any(not segment.audio_path for segment in segments):
        raise AudioMixError("Kokoro did not return an audio path for every narration segment.")
    measured_cursor = 0.0
    for segment in segments:
        segment.start_second = round(measured_cursor, 6)
        measured_cursor += segment.duration_second
    actual_duration = max(measured_cursor, 0.1)
    scenes = result["scenes"]
    target_frames = max(1, seconds_to_frames(actual_duration, settings.fps))
    cursor = 0
    for index, scene in enumerate(scenes):
        old_duration = scene.duration_frames
        remaining = len(scenes) - index - 1
        if index == len(scenes) - 1:
            new_duration = max(settings.fps, target_frames - cursor)
        else:
            new_duration = min(max(settings.fps, round(old_duration * actual_duration / max(plan["duration_second"], 0.1))), max(settings.fps, target_frames - cursor - remaining * settings.fps))
        action_scale = new_duration / max(1, old_duration)
        for action in scene.actions:
            action.start_frame = min(new_duration - 1, round(action.start_frame * action_scale))
            action.duration_frames = max(1, min(new_duration - action.start_frame, round(action.duration_frames * action_scale)))
        scene.start_frame = cursor
        scene.duration_frames = new_duration
        cursor += new_duration
    actual_duration = max(actual_duration, cursor / settings.fps)
    subtitles = [{"id": s.id, "text": s.text, "start_frame": seconds_to_frames(s.start_second, settings.fps), "end_frame": seconds_to_frames(s.start_second + s.duration_second, settings.fps), "emphasis": []} for s in segments]
    library = SfxLibrary()
    cues, assets, missing_sfx = _select_sfx(scenes, library)
    audio_events: list[AudioEvent] = [AudioEvent(asset_id=segment.id, type="narration", path=str(segment.audio_path), start_ms=round(segment.start_second * 1000), duration_ms=round(segment.duration_second * 1000), volume=settings.narration_volume) for segment in segments if segment.audio_path]
    audio_events += [AudioEvent(asset_id=cue.asset_id, type="sfx", path=str(cue.audio_path), start_ms=round(cue.start_second * 1000), duration_ms=max(50, round(next((asset.duration_second for asset in assets if asset.id == cue.asset_id), 0.25) * 1000)), volume=cue.volume) for cue in cues if cue.audio_path]
    project = Project(
        schema_version="1.1", project_id=project_id,
        title="How Does a Database Index Work?" if "database" in plan["topic"].lower() else plan["topic"].title(),
        original_prompt=prompt, requested_duration_second=float(plan["duration_second"]), actual_duration_second=actual_duration,
        fps=settings.fps, resolution=resolution_for(target_aspect), aspect_ratio=AspectRatio(target_aspect),
        narrator={"voice": plan.get("voice", settings.tts_voice), "speed": settings.tts_speed}, script=result["script"], scenes=scenes,
        narration_segments=segments, subtitles=subtitles, sound_effect_cues=cues, audio_assets=assets, audio_events=audio_events,
        music=MusicConfig(enabled=settings.music_enabled, mood="playful_technology" if "energetic" in plan.get("tone", []) else "technical", volume=settings.music_volume, ducking=settings.music_ducking_enabled),
        metadata={"plan": plan, "project_dir": str(project_dir), "audio_ready": generate_audio, "missing_sfx_requirements": missing_sfx},
    )
    if generate_audio:
        narration_clips = [AudioClip(segment.audio_path, segment.start_second, settings.narration_volume, "narration") for segment in segments if segment.audio_path]
        effect_clips = [AudioClip(cue.audio_path, cue.start_second, cue.volume, "sfx") for cue in cues if cue.audio_path]
        music_clips: list[AudioClip] = []
        if project.music.enabled:
            music_asset = library.match("background_music", tags=project.music.mood.split(), duration_second=actual_duration, commercial_only=True)
            if music_asset and Path(music_asset.path).exists():
                music_clips.append(AudioClip(music_asset.path, 0, project.music.volume, "music", project.music.fade_in_ms, project.music.fade_out_ms))
                project.audio_assets.append(music_asset)
                project.audio_events.append(AudioEvent(asset_id=music_asset.id, type="music", path=music_asset.path, start_ms=0, duration_ms=round(actual_duration * 1000), volume=project.music.volume))
            else:
                project.metadata.setdefault("missing_sfx_requirements", []).append("background_music")
        mixed = mix_tracks(narration_clips, effect_clips, project_dir, actual_duration, music=music_clips)
        project.metadata["narration_path"] = str(mixed["narration_path"])
        project.metadata["mixed_audio_path"] = str(mixed["final_audio_path"])
    return validate_project(project)


def save_project(project: Project, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(project.model_dump(mode="json"), indent=2), encoding="utf-8")
    return target


def generate_project(prompt: str, project_path: str | Path | None = None, use_llm: bool = False, generate_audio: bool = True, aspect: str | None = None) -> Project:
    requested = Path(project_path) if project_path else None
    project_dir = requested.parent if requested and requested.suffix.lower() == ".json" else requested
    project = build_project(prompt, output_dir=project_dir, use_llm=use_llm, generate_audio=generate_audio, aspect=aspect)
    destination = requested if requested and requested.suffix.lower() == ".json" else Path(project.metadata["project_dir"]) / "project.json"
    save_project(project, destination)
    _write_artifacts(project, Path(project.metadata["project_dir"]))
    return project
