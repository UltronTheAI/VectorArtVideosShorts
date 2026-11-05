from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import shutil
import urllib.request
from pathlib import Path

from backend.config import settings
from backend.audio.sfx_library import SfxLibrary
from backend.pipeline.generate import generate_project, save_project
from backend.pipeline.render import render_project
from backend.tts.kokoro_engine import KokoroEngine


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
        "python": True,
        "pydantic": importlib.util.find_spec("pydantic") is not None,
        "langchain": importlib.util.find_spec("langchain") is not None,
        "langgraph": importlib.util.find_spec("langgraph") is not None,
        "kokoro": KokoroEngine().available,
        "node": shutil.which("node") is not None,
        "npx": shutil.which("npx") is not None,
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "ollama": ollama_ok,
        "sound_catalogue": settings.manifest.exists(),
        "required_directories": all(path.exists() for path in (settings.outputs, settings.generated, settings.sfx_dir)),
    }
    print("VectorForge doctor")
    for name, ok in checks.items():
        suffix = f" ({ollama_message})" if name == "ollama" else ""
        print(f"  {'OK' if ok else 'MISSING':7} {name}{suffix}")
    if not checks["kokoro"]:
        print("  Install Kokoro in .venv: pip install kokoro soundfile numpy torch")
    if not checks["ffmpeg"]:
        print("  Install FFmpeg and add its bin directory to PATH.")
    if not checks["ollama"]:
        print(f"  Start Ollama and install the model: ollama pull {settings.ollama_model}")
    return 0 if all(checks.values()) else 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="vectorforge", description="Local AI-powered 2D vector video generator")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("voices")
    sfx = sub.add_parser("sfx"); sfx.add_argument("action", choices=["list", "validate"])
    gen = sub.add_parser("generate"); gen.add_argument("--prompt", required=True); gen.add_argument("--format", default="16:9", choices=["16:9", "9:16", "both"]); gen.add_argument("--use-llm", action="store_true")
    demo = sub.add_parser("demo"); demo.add_argument("--format", default="both", choices=["16:9", "9:16", "both"]); demo.add_argument("--no-render", action="store_true")
    render = sub.add_parser("render"); render.add_argument("--project", required=True); render.add_argument("--format", choices=["16:9", "9:16"]); render.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.command == "doctor": return doctor()
    if args.command == "voices":
        print("am_michael (default male), am_adam (alternative male)")
        print(f"Kokoro available: {'yes' if KokoroEngine().available else 'no'}")
        return 0
    if args.command == "sfx":
        library = SfxLibrary()
        if args.action == "list":
            for asset in library.assets: print(f"{asset.id}\t{asset.category}\t{asset.licence or 'licence not supplied'}")
        else:
            missing = library.validate_files(); print("No missing assets." if not missing else "Missing assets:\n" + "\n".join(missing))
        return 0
    if args.command == "demo":
        prompt = "Explain how database indexing works in 30 seconds. Make it funny, energetic and beginner-friendly. Use colourful 2D vector animations and a male narrator."
        formats = ["16:9", "9:16"] if args.format == "both" else [args.format]
        for fmt in formats:
            path = settings.outputs / "demo" / f"project-{fmt.replace(':', 'x')}.json"
            project = generate_project(prompt, path, use_llm=False, generate_audio=True, aspect=fmt)
            print(f"Project written: {path} ({project.actual_duration_second:.2f}s)")
            if not args.no_render:
                try:
                    print("Rendered:", ", ".join(map(str, render_project(path))))
                except RuntimeError as exc:
                    print(f"Render unavailable: {exc}")
        return 0
    if args.command == "generate":
        formats = ["16:9", "9:16"] if args.format == "both" else [args.format]
        for fmt in formats:
            path = settings.outputs / "generated" / f"project-{fmt.replace(':', 'x')}.json"
            project = generate_project(args.prompt, path, use_llm=args.use_llm, aspect=fmt)
            print(f"Project written: {path} ({project.actual_duration_second:.2f}s)")
        return 0
    if args.command == "render":
        print("Rendered:", ", ".join(map(str, render_project(args.project, args.format, args.preview))))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

