from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from backend.audio.mixer import AudioMixError, validate_audio_file
from backend.config import settings
from backend.schemas import Project


class RenderError(RuntimeError):
    pass


def load_project(path: str | Path) -> Project:
    source = Path(path).resolve()
    try:
        return Project.model_validate_json(source.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RenderError(f"Invalid project JSON {source}: {exc}") from exc


def _write_props(project: Project, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"project": project.model_dump(mode="json")}, indent=2), encoding="utf-8")
    return destination


def _require_audio(project: Project) -> Path:
    audio_path = project.metadata.get("mixed_audio_path")
    if not audio_path:
        raise RenderError("Project has no mixed_audio_path. Generate real Kokoro narration and final_audio.wav before rendering.")
    source = Path(audio_path)
    if not source.exists() or source.stat().st_size < 128:
        raise RenderError(f"Project audio is missing or invalid: {source}")
    try:
        stats = validate_audio_file(source, require_audible=True)
    except AudioMixError as exc:
        raise RenderError(str(exc)) from exc
    if abs(float(stats["duration_second"]) - project.actual_duration_second) > 0.15:
        raise RenderError(f"Final audio duration {stats['duration_second']:.3f}s does not match project duration {project.actual_duration_second:.3f}s.")
    return source


def _mux_audio(video: Path, audio: Path, project: Project) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RenderError("FFmpeg is required to mux final_audio.wav into an AAC MP4. Install FFmpeg and add it to PATH.")
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RenderError("ffprobe is required to verify the AAC stream after muxing.")
    temp = video.with_name(f".{video.stem}.muxing.tmp.mp4")
    duration = f"{project.actual_duration_second:.6f}"
    command = [ffmpeg, "-y", "-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", str(settings.audio_sample_rate), "-af", "apad", "-t", duration, "-movflags", "+faststart", str(temp)]
    result = subprocess.run(command, cwd=settings.root, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not temp.exists():
        temp.unlink(missing_ok=True)
        raise RenderError(f"FFmpeg audio mux failed: {result.stderr[-1600:]}")
    probe = subprocess.run([ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name,channels,sample_rate", "-of", "json", str(temp)], capture_output=True, text=True, check=False)
    if probe.returncode != 0 or '"codec_name": "aac"' not in probe.stdout.lower():
        temp.unlink(missing_ok=True)
        raise RenderError(f"Rendered MP4 does not contain the required AAC audio stream: {probe.stderr or probe.stdout}")
    video.unlink()
    temp.replace(video)


def render_project(project_path: str | Path, format_name: str | None = None, preview: bool = False) -> list[Path]:
    project = load_project(project_path)
    audio_path = None if preview else _require_audio(project)
    requested = [format_name] if format_name in {"16:9", "9:16"} else [project.aspect_ratio.value]
    outputs: list[Path] = []
    npm_runner = "npx.cmd" if os.name == "nt" else "npx"
    for fmt in requested:
        label = "landscape" if fmt == "16:9" else "portrait"
        output_dir = Path(project.metadata.get("project_dir", settings.outputs / project.project_id)).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / ("preview.png" if preview else f"{label}.mp4")
        props = _write_props(project, output_dir / f"remotion-props-{label}.json")
        command = [npm_runner, "remotion", "still" if preview else "render", "src/remotion/index.ts", "VectorForge", str(output), "--props", str(props), "--log=verbose"]
        try:
            result = subprocess.run(command, cwd=settings.root, capture_output=True, text=True, check=False)
        except FileNotFoundError as exc:
            raise RenderError("Node.js and npx are required for Remotion rendering.") from exc
        if result.returncode != 0 or not output.exists():
            diagnostic = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
            raise RenderError(f"Remotion failed for {label}:\n{diagnostic[-5000:] or 'Remotion returned no diagnostic output.'}")
        if audio_path:
            _mux_audio(output, audio_path, project)
        outputs.append(output)
    return outputs


def doctor_rendering() -> dict[str, bool | str]:
    return {
        "node": shutil.which("node") is not None,
        "npx": shutil.which("npx") is not None,
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "ffprobe": shutil.which("ffprobe") is not None,
        "remotion_config": (settings.root / "remotion.config.ts").exists(),
    }
