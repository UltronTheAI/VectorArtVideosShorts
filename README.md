# VectorForge

VectorForge is a local-only pipeline for turning a natural-language technical idea into an animated, faceless 2D vector video. The pipeline is intentionally strict: a normal generation run requires real Kokoro speech and a valid final audio timeline. It never substitutes silence for narration.

## Architecture

The Python side interprets the prompt, writes and validates the narration, plans supported environments/characters/actions with LangGraph and optional local Qwen, synthesizes segment WAVs with Kokoro, retrieves only catalogued licensed SFX, composes `narration.wav` and `final_audio.wav`, writes subtitles/SRT, and passes one JSON contract to Remotion.

The Remotion side accepts exactly `{ "project": { ... } }`. Zod validates the project before metadata is calculated. Duration, FPS, width, height, scenes, actions, environments, character rigs, subtitles, and audio metadata all come from that project. The development fixture is used only as Composition `defaultProps` when opening the Remotion project without external props; invalid supplied props throw an explicit error.

## Windows installation

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm install
```

Install FFmpeg and `ffprobe`, then add their `bin` directory to PATH. Install Ollama and pull the local planner model:

```powershell
ollama pull qwen2.5:7b
```

Run the TTS setup guidance:

```powershell
python -m backend.main setup-tts
```

Kokoro requires the `kokoro` Python package, a compatible PyTorch build, NumPy, SoundFile, and an espeak-ng installation suitable for Windows phonemisation. Set `KOKORO_MODEL_DIR` to the local Hugging Face cache directory. On the first setup run, set `KOKORO_OFFLINE=0` so Kokoro can populate the Kokoro-82M cache; after the weights and voice files are present, set `KOKORO_OFFLINE=1` for offline inference. The default male voice is `am_michael`; `am_adam` is also supported.

```powershell
$env:KOKORO_MODEL_DIR = "C:\Models\kokoro"
$env:KOKORO_OFFLINE = "0"   # first run only, if weights are not cached
python -m backend.main doctor
$env:KOKORO_OFFLINE = "1"
```

## Local model and audio configuration

Copy `.env.example` to `.env` or set the variables in PowerShell:

```text
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
KOKORO_VOICE=am_michael
KOKORO_SPEED=1.0
KOKORO_LANG=a
KOKORO_MODEL=Kokoro-82M
KOKORO_MODEL_VERSION=82M
KOKORO_REPO_ID=hexgrad/Kokoro-82M
KOKORO_MODEL_DIR=C:\Models\kokoro
KOKORO_OFFLINE=1
KOKORO_DEVICE=auto
```

Kokoro cache keys include text, voice, speed, model/version, repository, device, language, delivery metadata, and pause metadata. Cached WAVs are checked for corruption, zero length, and effective silence; legacy ID-named placeholders are not accepted. `KOKORO_DEVICE=auto` follows the local PyTorch availability check and selects CUDA when available, otherwise CPU. You can override it with `cpu` or `cuda`.

## First video

The default demo uses the actual local pipeline and stops with a nonzero exit code if Kokoro, FFmpeg, Remotion, or required project data is unavailable:

```powershell
python -m backend.main demo --format both
```

Custom prompt generation:

```powershell
python -m backend.main generate --prompt "Explain how database indexing works in 30 seconds with colourful animation and a male narrator" --format both --use-llm
```

`--use-llm` enables local Qwen script and scene-hint planning. All output remains constrained by Pydantic schemas and supported scene/action/environment lists. If Qwen is unavailable, the deterministic fallback is still a multi-scene visual plan; it is never a title-only fallback.

To render an existing generated project:

```powershell
python -m backend.main render --project outputs\<project-id>\project.json --format 16:9
python -m backend.main render --project outputs\<project-id>\project.json --format 9:16
```

## Output layout

```text
outputs/<project-id>/
  project.json
  script.json
  narration.wav
  final_audio.wav
  subtitles.srt
  asset-attribution.json
  landscape.mp4
  portrait.mp4
```

Remotion receives a generated `remotion-props-landscape.json` or `remotion-props-portrait.json` containing `{ "project": ... }`. The final mux uses AAC, preserves the full video duration, pads audio when necessary, and verifies the AAC stream when `ffprobe` is available. It does not use `-shortest`.

## Sound effects and licensing

VectorForge does not generate or scrape sound effects. `assets/sfx/manifest.json` is a managed local catalogue. Each asset needs an existing local file and explicit metadata: ID, category, tags, content hash, source URL, author, licence, attribution requirement, and commercial-use eligibility. Noncommercial licences are never marked commercial-use.

Supported categories include click, pop, whoosh, typing, impact, error, success, glitch, footsteps, laughter, sigh, transition, ambience, and dramatic_hit.

Freesound access uses its official API only:

```powershell
$env:FREESOUND_API_KEY = "your-key"
python -m backend.main sfx list
python -m backend.main sfx validate
python -m backend.main sfx attribution
```

If an API result has no permitted download URL or no explicit licence metadata, it is rejected. For manually downloaded Pixabay or other legitimate assets, use the importer abstraction with verified metadata; never invent a source URL or licence.

## Animation system

Scenes use deterministic frame-based SVG/React components: expressive `VectorCharacter` rigs, face/body/arms/legs, speech bubbles, developer desks, server rooms, whiteboards, networks, database tables, B-tree nodes, connector paths, cursors, highlight boxes, comparison panels, labels, progress bars, particles, camera pan/zoom, and subtitle safe zones.

The database reference demo contains six scenes: developer search, full collection scan, index introduction, indexed traversal, comparison, and ending. Actions are validated and include move, point, blink, nod, frustrated, surprised, celebrate, draw_path, highlight, camera pan, and camera zoom. Characters have visible expression variants and simple speech-active mouth motion.

Landscape uses wide side-by-side compositions at 1920×1080. Portrait uses a stacked composition at 1080×1920 with larger character scale, shorter text lines, and subtitles above the lower safe zone. It is not a crop of the landscape layout.

## Troubleshooting

- Silent narration: check `python -m backend.main doctor`, `KOKORO_MODEL_DIR`, `KOKORO_OFFLINE`, espeak-ng, and the selected voice. Delete only the affected `tts-<hash>.wav` cache after fixing the dependency; do not create a replacement WAV.
- Static or title-only render: inspect the generated `project.json` scene count and `remotion-props-*.json` wrapper. Remotion now rejects invalid external props instead of silently using the preview fixture.
- Missing SFX: run `python -m backend.main sfx validate`. Add a real licensed asset and complete metadata; the generator records missing optional categories rather than fabricating audio.
- FFmpeg failure: verify both `ffmpeg` and `ffprobe` resolve in PowerShell. Final MP4 muxing requires an AAC stream and will fail explicitly if it cannot be created.

## Limitations

Subtitles are segment-level, not word-level forced alignment. Kokoro controls delivery through supported speed, punctuation, pauses, and segment boundaries; emotion labels are planning metadata and do not guarantee acting. SFX retrieval requires either configured official API access or manually imported licensed assets. No cloud inference or paid API is required.
