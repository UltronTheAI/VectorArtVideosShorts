
from pathlib import Path
import os
import requests
from dotenv import load_dotenv

# Load .env from project root
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

API_KEY = os.getenv("FREESOUND_API_KEY", "").strip()

if not API_KEY:
    raise SystemExit("ERROR: FREESOUND_API_KEY missing in .env")

URL = "https://freesound.org/apiv2/search/text/"

params = {
    "query": "cartoon pop",
    "filter": 'license:"Creative Commons 0"',
    "fields": "id,name,duration,license,previews,url",
    "page_size": 5,
}

print("Connecting to Freesound...")

try:
    response = requests.get(
        URL,
        headers={"Authorization": f"Token {API_KEY}"},
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()

    print(f"Success! Found {data['count']} CC0 sounds.\n")

    for sound in data.get("results", []):
        print(f"ID:       {sound['id']}")
        print(f"Name:     {sound['name']}")
        print(f"Duration: {sound['duration']} seconds")
        print(f"License:  {sound['license']}")
        print(f"Page:     {sound['url']}")
        print(f"Preview:  {sound.get('previews', {}).get('preview-hq-mp3', 'N/A')}")
        print("-" * 50)

except requests.RequestException as exc:
    print(f"Freesound API error: {exc}")
    raise SystemExit(1)
