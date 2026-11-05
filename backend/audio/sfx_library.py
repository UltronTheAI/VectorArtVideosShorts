from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Iterable

from backend.config import settings
from backend.schemas import AudioAsset


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
            return [AudioAsset.model_validate(item) for item in raw.get("assets", [])]
        except (OSError, ValueError) as exc:
            raise ValueError(f"Invalid SFX manifest {self.manifest_path}: {exc}") from exc

    def validate_files(self) -> list[str]:
        missing = []
        for asset in self.assets:
            if not Path(asset.path).exists():
                missing.append(f"{asset.id}: {asset.path}")
        return missing

    def match(self, category: str, tags: Iterable[str] = (), commercial_only: bool = False) -> AudioAsset | None:
        wanted = {category.lower(), *(tag.lower() for tag in tags)}
        candidates = [a for a in self.assets if (not commercial_only or a.commercial_use)]
        candidates.sort(key=lambda a: a.id)
        ranked = sorted(candidates, key=lambda a: (0 if a.category.lower() == category.lower() else 1, -len(wanted & set(map(str.lower, a.tags)),)))
        return next((a for a in ranked if a.category.lower() == category.lower() or wanted & set(map(str.lower, a.tags))), None)

    def manifest_template(self) -> dict:
        return DEFAULT_MANIFEST.copy()


def index_audio_duration(path: str | Path) -> float:
    try:
        with wave.open(str(path), "rb") as handle:
            return handle.getnframes() / handle.getframerate()
    except (OSError, wave.Error):
        return 0.0

