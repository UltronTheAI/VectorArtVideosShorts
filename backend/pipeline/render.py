from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from backend.config import settings
from backend.schemas import Project


def load_project(path: str | Path) -> Project:
    return Project.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def render_project(project_path: str | Path, format_name: str | None = None, preview: bool = False) -> list[Path]:
    project = load_project(project_path)
    outputs: list[Path] = []
    formats = [format_name] if format_name in {"16:9", "9:16"} else [project.aspect_ratio.value]
    for fmt in formats:
        output_dir = settings.outputs / project.project_id / fmt.replace(":", "x")
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / ("preview.png" if preview else "video.mp4")
        npm_runner = "npx.cmd" if os.name == "nt" else "npx"
        if preview:
            # Render stills through the same Remotion composition when available.
            cmd = [npm_runner, "remotion", "still", "src/remotion/index.ts", "VectorForge", str(output), "--props", str(project_path)]
        else:
            cmd = [npm_runner, "remotion", "render", "src/remotion/index.ts", "VectorForge", str(output), "--props", str(project_path)]
        try:
            result = subprocess.run(cmd, cwd=settings.root, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise RuntimeError(f"Remotion failed ({result.returncode}): {result.stderr[-1200:]}")
            audio_path = project.metadata.get("mixed_audio_path")
            ffmpeg = shutil.which("ffmpeg")
            if not preview and audio_path and ffmpeg and Path(audio_path).exists():
                muxed = output.with_name("video-muxed.mp4")
                mux_result = subprocess.run([ffmpeg, "-y", "-i", str(output), "-i", str(audio_path), "-c:v", "copy", "-c:a", "aac", "-shortest", str(muxed)], cwd=settings.root, capture_output=True, text=True, check=False)
                if mux_result.returncode == 0 and muxed.exists():
                    output.unlink()
                    muxed.replace(output)
                else:
                    raise RuntimeError(f"FFmpeg audio mux failed: {mux_result.stderr[-1200:]}")
        except FileNotFoundError as exc:
            raise RuntimeError("Node/npx is required for rendering") from exc
        outputs.append(output)
    return outputs


def doctor_rendering() -> dict[str, bool | str]:
    return {"node": shutil.which("node") is not None, "npx": shutil.which("npx") is not None, "remotion_config": (settings.root / "remotion.config.ts").exists()}

