from __future__ import annotations

from backend.audio.sfx_library import SfxLibrary


def list_available_sound_effects(manifest_path=None) -> list[dict]:
    return [asset.model_dump() for asset in SfxLibrary(manifest_path).assets]

