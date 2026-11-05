"""Manual Kokoro smoke script; not part of the automated test suite."""

from backend.tts.kokoro_engine import KokoroEngine


if __name__ == "__main__":
    path, duration, cached = KokoroEngine(voice="am_michael").synthesize(
        "This is a real VectorForge Kokoro narration smoke check.", delivery="neutral"
    )
    print(f"Generated real narration: {path} ({duration:.2f}s, cached={cached})")
