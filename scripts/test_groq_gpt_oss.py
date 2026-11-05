"""Groq GPT-OSS 20B smoke test for VectorForge.

This intentionally bypasses the VectorForge fallback chain so it verifies Groq
credentials, model availability, timeout configuration, and structured output
independently of Ollama.

Run from the repository root:
    python scripts/test_groq_gpt_oss.py
    python scripts/test_groq_gpt_oss.py --prompt "Name one benefit of a database index."
"""

from __future__ import annotations

import argparse
import sys

from pydantic import BaseModel, ConfigDict, Field

from backend.config import settings


class SmokeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=1000)
    confidence: str = Field(min_length=1, max_length=32)


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Groq openai/gpt-oss-20b without Ollama fallback")
    parser.add_argument("--prompt", default="Explain one benefit of a database index in one sentence.")
    args = parser.parse_args()

    if not settings.groq_api_key:
        print("GROQ_API_KEY is missing. Put it in .env; it will not be printed by this script.", file=sys.stderr)
        return 2

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_groq import ChatGroq

        model = ChatGroq(
            model="openai/gpt-oss-20b",
            api_key=settings.groq_api_key,
            temperature=0,
            timeout=settings.groq_timeout,
            max_retries=0,
            reasoning_effort=settings.groq_reasoning_effort,
        )
        structured = model.with_structured_output(SmokeResponse, method="json_schema")
        response = structured.invoke([
            SystemMessage(content="Return only the requested structured response. Be technically accurate."),
            HumanMessage(content=args.prompt),
        ])
        parsed = response if isinstance(response, SmokeResponse) else SmokeResponse.model_validate(response)
    except ImportError as exc:
        print(f"Missing Groq dependency: {exc}. Install with: python -m pip install langchain-groq", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"Groq GPT-OSS 20B request failed: {exc}", file=sys.stderr)
        return 1

    print("Groq GPT-OSS 20B: OK")
    print(f"model=openai/gpt-oss-20b reasoning_effort={settings.groq_reasoning_effort}")
    print(f"confidence={parsed.confidence}")
    print(parsed.answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
