from __future__ import annotations

import hashlib
import json
import os
import shutil
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from backend.audio.sfx_library import SUPPORTED_SFX_CATEGORIES


class SfxProviderError(RuntimeError):
    pass


def licence_allows_commercial(licence: str) -> bool:
    value = licence.lower()
    return "non-commercial" not in value and "-nc" not in value and ("creative commons 0" in value or "cc0" in value or "attribution" in value)


class SfxProvider(ABC):
    @abstractmethod
    def search(self, query: str, category: str | None = None, commercial_only: bool = True) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def download(self, result: dict[str, Any], destination: str | Path) -> Path:
        raise NotImplementedError


class FreesoundProvider(SfxProvider):
    """Official Freesound API client. It never scrapes web pages."""

    endpoint = "https://freesound.org/apiv2"

    def __init__(self, api_key: str | None = None, access_token: str | None = None):
        self.api_key = api_key or os.getenv("FREESOUND_API_KEY")
        self.access_token = access_token or os.getenv("FREESOUND_ACCESS_TOKEN")
        if not self.api_key and not self.access_token:
            raise SfxProviderError("FREESOUND_API_KEY is not configured.")

    @property
    def _authorization(self) -> str:
        return f"Bearer {self.access_token}" if self.access_token else f"Token {self.api_key}"

    def _request(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers={"Authorization": self._authorization})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise SfxProviderError(f"Freesound API request failed: {exc}") from exc

    def search(self, query: str, category: str | None = None, commercial_only: bool = True) -> list[dict[str, Any]]:
        if category and category not in SUPPORTED_SFX_CATEGORIES:
            raise SfxProviderError(f"Unsupported SFX category: {category}")
        filter_parts = ["duration:[0.05 TO 8]"]
        if commercial_only:
            # CC0 and CC-BY families are commercial-compatible; NC licences are not.
            filter_parts.append('license:("Creative Commons 0" OR "Attribution")')
        params = urllib.parse.urlencode({"query": f"{query} {category or ''}", "filter": " ".join(filter_parts), "fields": "id,name,license,username,previews,duration,url"})
        data = self._request(f"{self.endpoint}/search/text/?{params}")
        return [item for item in data.get("results", []) if item.get("license") and licence_allows_commercial(item.get("license", ""))]

    def download(self, result: dict[str, Any], destination: str | Path) -> Path:
        preview = result.get("previews", {}).get("preview-hq-mp3") or result.get("previews", {}).get("preview-lq-mp3")
        if not preview:
            raise SfxProviderError("Freesound result has no permitted preview URL.")
        target_dir = Path(destination)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"freesound-{result.get('id')}.mp3"
        request = urllib.request.Request(preview, headers={"Authorization": self._authorization})
        try:
            with urllib.request.urlopen(request, timeout=60) as source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink)
        except Exception as exc:
            target.unlink(missing_ok=True)
            raise SfxProviderError(f"Could not download permitted Freesound asset: {exc}") from exc
        return target


class LocalAssetImporter:
    def __init__(self, library_dir: str | Path):
        self.library_dir = Path(library_dir)
        self.library_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def content_hash(path: str | Path) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def import_file(self, source: str | Path, metadata: dict[str, Any]) -> dict[str, Any]:
        source_path = Path(source)
        if not source_path.exists():
            raise SfxProviderError(f"Local SFX file is missing: {source_path}")
        category = metadata.get("category")
        required = {"id", "category", "tags", "source_url", "author", "licence", "attribution_required", "commercial_use"}
        missing = required - set(metadata)
        if missing:
            raise SfxProviderError(f"SFX metadata is incomplete; missing: {sorted(missing)}")
        if category not in SUPPORTED_SFX_CATEGORIES:
            raise SfxProviderError(f"Unsupported SFX category: {category}")
        digest = self.content_hash(source_path)
        target = self.library_dir / f"{digest[:16]}-{source_path.name}"
        if not target.exists():
            shutil.copy2(source_path, target)
        return {**metadata, "path": str(target), "content_hash": digest}


class PixabayAudioImporter(LocalAssetImporter):
    """Manual Pixabay audio registration only; Pixabay has no supported audio API here."""

    provider_name = "pixabay_manual"

    def import_file(self, source: str | Path, metadata: dict[str, Any]) -> dict[str, Any]:
        if not metadata.get("source_url"):
            raise SfxProviderError("A manual Pixabay import requires the original source URL.")
        metadata = {**metadata, "provider": self.provider_name}
        return super().import_file(source, metadata)
