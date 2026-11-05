from kokoro import KPipeline
import soundfile as sf
import numpy as np
import torch
from pathlib import Path

device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Using device: {device}")

pipeline = KPipeline(
    lang_code="a",
    device=device
)

script = """
Have you ever wondered why databases are so fast?

Imagine searching through ten million records.

Without an index, your database might have to scan every single record.

But with a database index, it can find the correct data much faster.

And that is why database indexes are so powerful.
"""

generator = pipeline(
    script,
    voice="af_heart",
    speed=1.0,
    split_pattern=r"\n+"
)

audio_chunks = []

for _, _, audio in generator:
    audio_chunks.append(audio)

if not audio_chunks:
    raise RuntimeError("Kokoro generated no audio.")

output = Path("public/audio/voiceover.wav")
output.parent.mkdir(parents=True, exist_ok=True)

audio = np.concatenate(audio_chunks)

sf.write(
    str(output),
    audio,
    24000
)

print(f"Voiceover generated: {output}")