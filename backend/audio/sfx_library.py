from __future__ import annotations

import hashlib
import json
import shutil
import wave
from pathlib import Path
from typing import Iterable

from backend.config import settings
from backend.schemas import AudioAsset

SUPPORTED_SFX_CATEGORIES = {
    "click", "pop", "whoosh", "typing", "keyboard", "impact", "error", "failure", "success", "glitch",
    "footsteps", "laughter", "sigh", "transition", "ambience", "dramatic_hit", "background_music",
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
                continue
            try:
                from backend.audio.mixer import validate_audio_file
                stats = validate_audio_file(asset.path)
                if bool(stats["silent"]):
                    missing.append(f"{asset.id}: effectively silent audio")
            except Exception as exc:
                missing.append(f"{asset.id}: unreadable audio ({exc})")
        return missing

    @staticmethod
    def content_hash(path: str | Path) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def import_asset(self, source: str | Path, *, category: str, source_url: str, licence: str, author: str = "Unknown", attribution_required: bool = True, commercial_use: bool = False, provider: str = "local") -> AudioAsset:
        source_path = Path(source).resolve()
        if not source_path.exists():
            raise ValueError(f"SFX file does not exist: {source_path}")
        category = "background_music" if category == "music" else category
        if category not in SUPPORTED_SFX_CATEGORIES:
            raise ValueError(f"Unsupported SFX category: {category}")
        if not source_url or not licence:
            raise ValueError("source_url and licence are required; licence terms may not be invented")
        digest = self.content_hash(source_path)
        target_dir = settings.sfx_cache if category != "background_music" else settings.music_cache
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{digest[:16]}-{source_path.name}"
        if not target.exists():
            shutil.copy2(source_path, target)
        from backend.audio.mixer import audio_stats
        duration_second = float(audio_stats(target)["duration_second"])
        asset = AudioAsset(id=f"asset-{digest[:16]}", path=str(target), category=category, provider=provider, tags=[category], duration_second=duration_second, content_hash=digest, source_url=source_url, author=author, licence=licence, attribution_required=attribution_required, commercial_use=commercial_use)
        current = [item for item in self.assets if item.content_hash != digest and item.id != asset.id]
        current.append(asset)
        self._write_assets(current)
        self.assets = current
        return asset

    def _write_assets(self, assets: list[AudioAsset]) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps({"version": "1.1", "assets": [asset.model_dump(mode="json") for asset in sorted(assets, key=lambda item: item.id)]}, indent=2), encoding="utf-8")

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

    def match(self, category: str, tags: Iterable[str] = (), duration_second: float | None = None, commercial_only: bool = False) -> AudioAsset | None:
        aliases = {"keyboard": "typing", "failure": "error", "music": "background_music"}
        category = aliases.get(category.lower(), category.lower())
        wanted = {category, *(tag.lower() for tag in tags)}
        candidates = [a for a in self.assets if (not commercial_only or a.commercial_use)]
        candidates.sort(key=lambda a: a.id)
        def distance(asset: AudioAsset) -> float:
            return abs(asset.duration_second - duration_second) if duration_second is not None else 0
        ranked = sorted(candidates, key=lambda a: (0 if a.category.lower() == category else 1, distance(a), -len(wanted & set(map(str.lower, a.tags)))))
        return next((a for a in ranked if a.category.lower() == category or wanted & set(map(str.lower, a.tags))), None)

    def manifest_template(self) -> dict:
        return DEFAULT_MANIFEST.copy()


def index_audio_duration(path: str | Path) -> float:
    try:
        with wave.open(str(path), "rb") as handle:
            return handle.getnframes() / handle.getframerate()
    except (OSError, wave.Error):
        return 0.0

