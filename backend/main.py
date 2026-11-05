from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import shutil
import subprocess
import urllib.request
from pathlib import Path

from backend.audio.mixer import AudioMixError, audio_stats, validate_audio_file
from backend.audio.project_audio import mix_project_audio, save_project_json
from backend.audio.sfx_library import SfxLibrary
from backend.audio.sfx_providers import FreesoundProvider, SfxProviderError, licence_allows_commercial
from backend.config import settings
from backend.pipeline.generate import generate_project
from backend.pipeline.render import load_project, render_project
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


def sfx_search(query: str, category: str | None = None) -> int:
    provider = FreesoundProvider(settings.freesound_api_key, settings.freesound_access_token)
    results = provider.search(query, category=category, commercial_only=True)
    for result in results:
        print(json.dumps({"id": result.get("id"), "name": result.get("name"), "licence": result.get("license"), "author": result.get("username"), "url": result.get("url"), "duration": result.get("duration")}, ensure_ascii=False))
    return 0


def sfx_download(category: str, count: int) -> int:
    provider = FreesoundProvider(settings.freesound_api_key, settings.freesound_access_token)
    library = SfxLibrary()
    results = provider.search(category, category=category, commercial_only=True)[:count]
    if not results:
        raise RuntimeError(f"No commercially usable Freesound results found for {category!r}.")
    for result in results:
        if not licence_allows_commercial(str(result.get("license", ""))):
            log.warning("Skipping %s because licence is not verified for commercial use.", result.get("id"))
            continue
        path = provider.download(result, settings.sfx_cache)
        asset = library.import_asset(path, category=category, source_url=str(result.get("url", "")), licence=str(result.get("license", "")), author=str(result.get("username", "")), attribution_required=True, commercial_use=True, provider="freesound")
        print(f"Imported {asset.id}: {asset.path}")
    return 0


def sfx_import(args: argparse.Namespace) -> int:
    category = "background_music" if args.category == "music" else args.category
    library = SfxLibrary()
    asset = library.import_asset(args.file, category=category, source_url=args.source_url, licence=args.licence, author=args.author, attribution_required=not args.no_attribution, commercial_use=args.commercial_use, provider=args.provider)
    print(f"Imported {asset.id}: {asset.path}")
    return 0


def audio_doctor(project_path: str) -> int:
    project = load_project(project_path)
    errors: list[str] = []
    print(f"Project: {project.project_id}")
    for segment in project.narration_segments:
        if not segment.audio_path:
            errors.append(f"{segment.id}: missing narration path")
            continue
        try:
            stats = validate_audio_file(segment.audio_path, require_audible=True)
            print(f"narration {segment.id}: {stats['duration_second']:.3f}s peak={stats['peak']:.4f} rms={stats['rms']:.4f}")
        except AudioMixError as exc:
            errors.append(str(exc))
    library = SfxLibrary()
    for asset in project.audio_assets:
        if not Path(asset.path).exists():
            errors.append(f"missing asset {asset.id}: {asset.path}")
    mixed = project.metadata.get("mixed_audio_path")
    if mixed:
        try:
            stats = validate_audio_file(mixed, require_audible=True)
            print(f"final_audio.wav: {stats['duration_second']:.3f}s peak={stats['peak']:.4f} rms={stats['rms']:.4f}")
            if abs(float(stats["duration_second"]) - project.actual_duration_second) > 0.15:
                errors.append("final audio duration does not match project duration")
        except AudioMixError as exc:
            errors.append(str(exc))
    else:
        errors.append("project metadata has no mixed_audio_path")
    ffprobe = shutil.which("ffprobe")
    project_dir = Path(project.metadata.get("project_dir", Path(project_path).parent))
    for label in ("landscape", "portrait"):
        mp4 = project_dir / f"{label}.mp4"
        if not mp4.exists():
            continue
        if not ffprobe:
            errors.append("ffprobe is not available to verify MP4 audio streams")
            break
        probe = subprocess.run([ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "default=nw=1:nk=1", str(mp4)], capture_output=True, text=True, check=False)
        if probe.returncode != 0 or "aac" not in probe.stdout.lower():
            errors.append(f"{mp4.name} has no verified AAC audio stream")
    missing = library.validate_files()
    if missing:
        print("Catalogue missing assets: " + ", ".join(missing))
    print(f"timeline: {project.actual_duration_second:.3f}s at {project.fps} fps")
    if errors:
        print("Audio doctor errors:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("Audio doctor: narration and final mix are valid. Use ffprobe to confirm each MP4 after rendering.")
    return 0


def audio_assets() -> int:
    library = SfxLibrary()
    for asset in library.assets:
        print(f"{asset.id}\t{asset.category}\t{asset.duration_second:.2f}s\t{asset.provider}\t{asset.licence}")
    print(f"Cached assets: {len(library.assets)}")
    return 0


def audio_mix(project_path: str) -> int:
    project = load_project(project_path)
    mixed = mix_project_audio(project)
    path = save_project_json(mixed)
    print(f"Mixed audio written to {mixed.metadata['mixed_audio_path']}")
    print(f"Project updated: {path}")
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
    sfx = sub.add_parser("sfx")
    sfx_actions = sfx.add_subparsers(dest="sfx_action", required=True)
    sfx_actions.add_parser("list")
    sfx_search_parser = sfx_actions.add_parser("search"); sfx_search_parser.add_argument("--query", required=True); sfx_search_parser.add_argument("--category")
    sfx_download_parser = sfx_actions.add_parser("download"); sfx_download_parser.add_argument("--category", required=True); sfx_download_parser.add_argument("--count", type=int, default=5)
    sfx_import_parser = sfx_actions.add_parser("import"); sfx_import_parser.add_argument("--file", required=True); sfx_import_parser.add_argument("--category", required=True); sfx_import_parser.add_argument("--source-url", required=True); sfx_import_parser.add_argument("--licence", required=True); sfx_import_parser.add_argument("--author", default="Unknown"); sfx_import_parser.add_argument("--provider", default="local"); sfx_import_parser.add_argument("--commercial-use", action="store_true"); sfx_import_parser.add_argument("--no-attribution", action="store_true")
    sfx_actions.add_parser("validate")
    sfx_actions.add_parser("attribution")
    audio = sub.add_parser("audio")
    audio_actions = audio.add_subparsers(dest="audio_action", required=True)
    audio_doctor_parser = audio_actions.add_parser("doctor"); audio_doctor_parser.add_argument("--project", required=True)
    audio_actions.add_parser("assets")
    audio_mix_parser = audio_actions.add_parser("mix"); audio_mix_parser.add_argument("--project", required=True)
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
        if args.sfx_action == "list":
            for asset in library.assets:
                print(f"{asset.id}\t{asset.category}\t{asset.licence}\tcommercial={asset.commercial_use}")
        elif args.sfx_action == "search":
            return sfx_search(args.query, args.category)
        elif args.sfx_action == "download":
            return sfx_download(args.category, args.count)
        elif args.sfx_action == "import":
            return sfx_import(args)
        elif args.sfx_action == "validate":
            errors = library.validate_files() + library.validate_metadata()
            if errors:
                raise RuntimeError("SFX catalogue errors:\n" + "\n".join(errors))
            print("SFX catalogue is valid.")
        else:
            print(json.dumps(library.attribution_manifest(), indent=2))
        return 0
    if args.command == "audio":
        if args.audio_action == "doctor":
            return audio_doctor(args.project)
        if args.audio_action == "assets":
            return audio_assets()
        if args.audio_action == "mix":
            return audio_mix(args.project)
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
