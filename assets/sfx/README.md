# Licensed SFX library

Place manually downloaded, licence-compatible audio here and add one complete entry to `manifest.json`. Required fields are `id`, `path`, `category`, `tags`, `duration_second`, `source_url`, `author`, `licence`, `attribution_required`, `commercial_use`, and optionally `content_hash`.

Use `backend.audio.sfx_providers.LocalAssetImporter` for content-hash deduplication. Use `FreesoundProvider` only with an authenticated official API key. Do not paste a page URL when the asset has no permitted direct download URL, and do not mark CC-BY-NC or other noncommercial licences as commercially usable.
