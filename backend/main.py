from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import shutil
import urllib.request
from pathlib import Path

from backend.audio.sfx_library import SfxLibrary
from backend.config import settings
from backend.pipeline.generate import generate_project
from backend.pipeline.render import render_project
from backend.tts.kokoro_engine import KokoroEngine, SUPPORTED_VOICES

log = logging.getLogger("vectorforge")


def progress(stage: str, message: str) -> None:
    log.info("[%s] %s", stage, message)


def check_ollama() -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(f"{settings.ollama_url}/api/tags", timeout=2) as response:
            data = json.loads(response.read().decode())
        names = [item.get("name", "") for item in data.get("models", [])]
        return settings.ollama_model in names, f"reachable; models: {', '.join(names) or 'none'}"
    except Exception as exc:
        return False, str(exc)


def doctor() -> int:
    settings.ensure_directories()
    ollama_ok, ollama_message = check_ollama()
    checks = {
        "pydantic": importlib.util.find_spec("pydantic") is not None,
        "langchain": importlib.util.find_spec("langchain") is not None,
        "langgraph": importlib.util.find_spec("langgraph") is not None,
        "kokoro_package": KokoroEngine().available,
        "node": shutil.which("node") is not None,
        "npx": shutil.which("npx") is not None,
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "ffprobe": shutil.which("ffprobe") is not None,
        "ollama_qwen": ollama_ok,
        "sound_catalogue": settings.manifest.exists(),
        "required_directories": all(path.exists() for path in (settings.outputs, settings.generated, settings.sfx_dir)),
    }
    print("VectorForge doctor")
    for name, ok in checks.items():
        suffix = f" ({ollama_message})" if name == "ollama_qwen" else ""
        print(f"  {'OK' if ok else 'MISSING':7} {name}{suffix}")
    if not checks["kokoro_package"]:
        print("  Install Kokoro, PyTorch, SoundFile, NumPy, and espeak-ng; see README.md.")
    if not checks["ffmpeg"]:
        print("  Install FFmpeg and ffprobe, then add both bin directories to PATH.")
    if not checks["ollama_qwen"]:
        print(f"  Start Ollama and install the model: ollama pull {settings.ollama_model}")
    return 0 if all(checks.values()) else 1


def setup_tts() -> int:
    print("Kokoro first-run setup")
    print("1. Install Kokoro, PyTorch, SoundFile, NumPy, and espeak-ng for Windows.")
    print("2. Set KOKORO_MODEL_DIR to a writable local Hugging Face cache directory.")
    print("3. For the first run only, set KOKORO_OFFLINE=0 so Kokoro can populate the local Kokoro-82M cache.")
    print("4. Set KOKORO_OFFLINE=1 for subsequent offline inference.")
    print(f"Supported male voices: {', '.join(sorted(SUPPORTED_VOICES))}; default: {settings.tts_voice}")
    return 0


def generate_one(prompt: str, fmt: str, use_llm: bool, render: bool) -> Path:
    progress("prompt", f"Parsing request for {fmt}")
    project = generate_project(prompt, use_llm=use_llm, aspect=fmt)
    project_path = Path(project.metadata["project_dir"]) / "project.json"
    progress("script", "Narration written and validated")
    progress("scenes", f"Planned {len(project.scenes)} animated scenes")
    progress("voice", str(project.metadata.get("narration_path", "real Kokoro audio required")))
    progress("sfx", f"Selected {len(project.audio_assets)} licensed assets")
    missing_sfx = project.metadata.get("missing_sfx_requirements", [])
    if missing_sfx:
        log.warning("No licensed local SFX available for: %s. Add verified assets to assets/sfx/manifest.json.", ", ".join(missing_sfx))
    progress("timeline", f"Composed {project.actual_duration_second:.2f}s timeline")
    if render:
        progress("render", "Starting Remotion and AAC mux")
        outputs = render_project(project_path, fmt)
        for output in outputs:
            if not output.exists():
                raise RuntimeError(f"Renderer reported a missing output: {output}")
            progress("output", str(output))
    return project_path


def main() -> int:
    parser = argparse.ArgumentParser(prog="vectorforge", description="Local AI-powered 2D vector animation video generator")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("setup-tts")
    sub.add_parser("voices")
    sfx = sub.add_parser("sfx"); sfx.add_argument("action", choices=["list", "validate", "attribution"])
    gen = sub.add_parser("generate"); gen.add_argument("--prompt", required=True); gen.add_argument("--format", default="16:9", choices=["16:9", "9:16", "both"]); gen.add_argument("--use-llm", action="store_true")
    demo = sub.add_parser("demo"); demo.add_argument("--format", default="both", choices=["16:9", "9:16", "both"])
    render = sub.add_parser("render"); render.add_argument("--project", required=True); render.add_argument("--format", choices=["16:9", "9:16"]); render.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.command == "doctor":
        return doctor()
    if args.command == "setup-tts":
        return setup_tts()
    if args.command == "voices":
        print("\n".join(sorted(SUPPORTED_VOICES)))
        print(f"Default: {settings.tts_voice}; Kokoro package: {'available' if KokoroEngine().available else 'missing'}")
        return 0
    if args.command == "sfx":
        library = SfxLibrary()
        if args.action == "list":
            for asset in library.assets:
                print(f"{asset.id}\t{asset.category}\t{asset.licence}\tcommercial={asset.commercial_use}")
        elif args.action == "validate":
            errors = library.validate_files() + library.validate_metadata()
            if errors:
                raise RuntimeError("SFX catalogue errors:\n" + "\n".join(errors))
            print("SFX catalogue is valid.")
        else:
            print(json.dumps(library.attribution_manifest(), indent=2))
        return 0
    if args.command == "demo":
        prompt = "Explain how database indexing works in 30 seconds. Make it funny, energetic and beginner-friendly. Use colourful 2D vector animations and a male narrator."
        formats = ["16:9", "9:16"] if args.format == "both" else [args.format]
        for fmt in formats:
            generate_one(prompt, fmt, use_llm=True, render=True)
        return 0
    if args.command == "generate":
        formats = ["16:9", "9:16"] if args.format == "both" else [args.format]
        for fmt in formats:
            generate_one(args.prompt, fmt, use_llm=args.use_llm, render=True)
        return 0
    if args.command == "render":
        outputs = render_project(args.project, args.format, args.preview)
        if not all(output.exists() for output in outputs):
            raise RuntimeError("Render completed without producing every requested output.")
        print("Rendered:\n" + "\n".join(map(str, outputs)))
        return 0
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        logging.basicConfig(level=logging.ERROR, format="%(levelname)s %(message)s")
        log.error("VectorForge failed: %s", exc)
        raise SystemExit(1) from exc
