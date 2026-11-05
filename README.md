# VectorForge

VectorForge is a local-first MVP for turning a natural-language idea into a faceless 2D vector animation video. It plans with a deterministic LangGraph workflow, optionally improves the script with local Ollama/Qwen, generates cached Kokoro narration, selects only explicitly catalogued sound effects, and renders an aspect-ratio-aware Remotion composition.

## Architecture

`backend/` owns orchestration, Pydantic schemas, timing, local TTS, audio mixing, SFX metadata, and the CLI. `src/remotion/` owns the typed Zod mirror of the project format and the SVG/HTML vector composition. The project JSON is the contract between Python planning and Remotion rendering. LLM output is never executed; it is parsed and validated as data.

The pipeline is: prompt interpretation → script writing → scene direction → Pydantic validation → segment TTS/cache → measured timeline → subtitles → Remotion render.

## Windows setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm install
```

Install FFmpeg and add its `bin` directory to PATH. Install Ollama, start it, then download the local model:

```powershell
ollama pull qwen2.5:7b
```

Kokoro is optional for project/timeline tests but required for real narration. In the active venv install the Kokoro package, PyTorch, SoundFile, and NumPy according to the current Kokoro Windows instructions. Phonemisation packages can require a separate espeak-ng installation; verify that `python -c "from kokoro import KPipeline; print('ok')"` succeeds. The adapter defaults to `am_michael`; use `KOKORO_VOICE=am_adam` for the alternate male voice.

Run:

```powershell
python -m backend.main doctor
python -m backend.main voices
```

## First demo

```powershell
python -m backend.main demo --format both
```

This writes project JSON under `outputs/demo/`. With Node/Remotion available it renders landscape and portrait MP4s under `outputs/<project-id>/`. The pipeline mixes cached segment WAVs into `public/audio/<project-id>-voice.wav` and muxes AAC audio with FFmpeg when FFmpeg is available. If Kokoro is not installed or model weights are not locally available, the demo still exercises project generation and rendering with a clearly marked quiet timing placeholder; install/cache Kokoro before publishing. Missing optional SFX never block rendering.

To generate a custom project, optionally allowing local Qwen to improve the script:

```powershell
python -m backend.main generate --prompt "Explain database indexing in 30 seconds. Make it funny and beginner-friendly." --format both --use-llm
python -m backend.main render --project outputs/generated/project-16x9.json
```

`--use-llm` is bounded by the deterministic fallback: if Ollama is unavailable or returns invalid JSON, the application uses the local scriptwriter and still validates the result.

## Sound effects and licensing

`assets/sfx/manifest.json` is intentionally empty. Add WAV files only when you have verified their licence. Each entry must include `id`, `path`, `category`, `tags`, `duration_second`, `source_url`, `author`, `licence`, `attribution_required`, and `commercial_use`. Supported categories are click, pop, whoosh, typing, success, error, dramatic_hit, laughter, sigh, and transition. VectorForge does not scrape sound libraries and does not assume that “free download” means commercial use.

```powershell
python -m backend.main sfx list
python -m backend.main sfx validate
```

## Extending animation templates

Add a supported scene type to `backend/schemas/models.py`, implement its deterministic visual branch in `src/remotion/Video.tsx`, and add any reusable primitive in `src/remotion/components/primitives.tsx`. Update `backend/tools/scene_tools.py` and tests. Keep positions percentage-based so 16:9 and 9:16 compositions use intentional layouts rather than a crop.

## Testing

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
npx tsc --noEmit
```

The deterministic Python tests do not require Ollama, Kokoro, FFmpeg, or sound assets. `doctor` reports missing integration dependencies exactly. The repository's original `test_kokoro.py` remains a manual Kokoro smoke script and requires the optional package.

## Current limitations

The MVP uses segment-level subtitle timing, not word alignment. Emotion metadata maps to speed/segmentation hints; Kokoro does not provide arbitrary acting controls. The scene director supports a small deterministic template set. SFX are optional until licensed files are catalogued. Rendering requires a working Node/Remotion installation and FFmpeg may be needed by the host for final audio workflows. No cloud API or paid service is required.

