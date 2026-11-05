from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Iterable

from backend.config import settings
from backend.schemas import AudioAsset

SUPPORTED_SFX_CATEGORIES = {
    "click", "pop", "whoosh", "typing", "impact", "error", "success", "glitch",
    "footsteps", "laughter", "sigh", "transition", "ambience", "dramatic_hit",
}


DEFAULT_MANIFEST = {
    "version": "1.0",
    "assets": [],
    "notes": "Add only assets with licence metadata. VectorForge never scrapes or invents licence terms.",
}


class SfxLibrary:
    def __init__(self, manifest_path: str | Path | None = None):
        self.manifest_path = Path(manifest_path or settings.manifest)
        self.assets = self._load()

    def _load(self) -> list[AudioAsset]:
        if not self.manifest_path.exists():
            return []
        try:
            raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            assets = [AudioAsset.model_validate(item) for item in raw.get("assets", [])]
            for asset in assets:
                asset_path = Path(asset.path)
                if not asset_path.is_absolute():
                    asset.path = str((self.manifest_path.parent / asset_path).resolve())
                if asset.category not in SUPPORTED_SFX_CATEGORIES:
                    raise ValueError(f"Unsupported SFX category: {asset.category}")
                if asset.commercial_use and "non-commercial" in asset.licence.lower():
                    raise ValueError(f"Asset {asset.id} incorrectly claims commercial use for {asset.licence}")
            return assets
        except (OSError, ValueError) as exc:
            raise ValueError(f"Invalid SFX manifest {self.manifest_path}: {exc}") from exc

    def validate_files(self) -> list[str]:
        missing = []
        for asset in self.assets:
            if not Path(asset.path).exists():
                missing.append(f"{asset.id}: {asset.path}")
        return missing

    def validate_metadata(self) -> list[str]:
        errors: list[str] = []
        for asset in self.assets:
            if not asset.source_url or not asset.licence or not asset.author:
                errors.append(f"{asset.id}: source_url, licence, and author are required")
            if asset.commercial_use and "non-commercial" in asset.licence.lower():
                errors.append(f"{asset.id}: non-commercial licence cannot be marked commercial_use")
        return errors

    def attribution_manifest(self) -> list[dict]:
        return [asset.model_dump() for asset in self.assets if asset.attribution_required]

    def match(self, category: str, tags: Iterable[str] = (), commercial_only: bool = False) -> AudioAsset | None:
        wanted = {category.lower(), *(tag.lower() for tag in tags)}
        candidates = [a for a in self.assets if (not commercial_only or a.commercial_use)]
        candidates.sort(key=lambda a: a.id)
        ranked = sorted(candidates, key=lambda a: (0 if a.category.lower() == category.lower() else 1, -len(wanted & set(map(str.lower, a.tags)))))
        return next((a for a in ranked if a.category.lower() == category.lower() or wanted & set(map(str.lower, a.tags))), None)

    def manifest_template(self) -> dict:
        return DEFAULT_MANIFEST.copy()


def index_audio_duration(path: str | Path) -> float:
    try:
        with wave.open(str(path), "rb") as handle:
            return handle.getnframes() / handle.getframerate()
    except (OSError, wave.Error):
        return 0.0

