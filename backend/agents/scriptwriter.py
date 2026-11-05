from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.agents.llm_schemas import PromptInterpretation, ScriptDraft
from backend.llm.providers import invoke_json
from backend.tools.timing_tools import estimate_narration_duration

log = logging.getLogger(__name__)


def _deterministic_interpretation(prompt: str) -> dict[str, Any]:
    import re

    lower = prompt.lower()
    duration_match = re.search(r"\b(\d{1,3})\s*(?:seconds?|secs?)\b", lower)
    duration = int(duration_match.group(1)) if duration_match else 30
    duration = min(180, max(10, duration))
    if "9:16" in lower or "portrait" in lower or "shorts" in lower:
        fmt = "9:16"
    elif "both" in lower:
        fmt = "both"
    else:
        fmt = "16:9"
    tones = [name for name in ("funny", "energetic", "surprising", "frustrated", "neutral") if name in lower]
    audience = "beginners" if "beginner" in lower or "new to" in lower else "general audience"
    voice = "am_adam" if "adam" in lower else "am_michael"
    topic = re.sub(r"\b(?:explain|make|create|a|an|in|for|seconds?|with|use|colourful|colorful|2d|vector|animations?|and|a|male|narrator|please)\b", " ", prompt, flags=re.I)
    topic = re.sub(r"\s+", " ", topic).strip(" .,!?") or "the requested topic"
    return {
        "duration_second": duration,
        "format": fmt,
        "topic": topic,
        "audience": audience,
        "tone": tones or ["clear"],
        "style": "colourful flat-vector 2D animation",
        "voice": voice,
        "raw_prompt": prompt,
    }


def interpret_prompt(prompt: str, use_llm: bool = False, provider: str | None = None) -> dict[str, Any]:
    deterministic = _deterministic_interpretation(prompt)
    if not use_llm:
        return deterministic
    from langchain_core.messages import HumanMessage

    instruction = {
        "task": "Interpret a raw video idea for a local vector animation pipeline.",
        "raw_prompt": prompt,
        "defaults": deterministic,
        "constraints": ["duration must be 10-180 seconds", "format must be 16:9, 9:16, or both", "preserve technical topic wording", "do not invent facts"],
        "return_schema": "duration_second, format, topic, audience, tone, style, voice",
    }
    response = invoke_json(
        [HumanMessage(content=json.dumps(instruction))],
        schema=PromptInterpretation,
        provider=provider,
        temperature=0.0,
        cache_payload={"stage": "idea_interpreter", "prompt": prompt, "schema_version": "1"},
    )
    plan = response.data.model_dump(mode="json") if isinstance(response.data, PromptInterpretation) else PromptInterpretation.model_validate(response.data).model_dump(mode="json")
    plan["raw_prompt"] = prompt
    plan["_llm"] = response.metadata()
    return plan


def fallback_script(topic: str, duration_second: float, tone: list[str] | None = None) -> str:
    topic_lower = topic.lower()
    if "database" in topic_lower and "index" in topic_lower:
        return (
            "Imagine asking a database for one record in a giant pile of papers. "
            "Without an index, it may scan the records one by one. That works, but it gets slow as the pile grows. "
            "An index is a separate, organised structure that points toward the data. "
            "Many databases use tree-shaped indexes, such as B-trees, so the search can narrow down at each step. "
            "The database follows the path, finds the matching key, and jumps to the record. "
            "So the big idea is simple: an index spends extra space and update work to make many lookups faster. "
            "It is a shortcut map, not magic—and not every index uses a B-tree."
        )
    tone_text = " Keep it lively and visual." if tone and ("funny" in tone or "energetic" in tone) else ""
    return f"Here is the simple idea behind {topic}: start with the problem, reveal the useful structure, and show the payoff.{tone_text}"


def fit_script_to_duration(script: str, duration_second: float) -> str:
    """Shorten at sentence boundaries before audio generation; never cut raw audio."""
    if estimate_narration_duration(script) <= duration_second * 1.12:
        return script
    budget_words = max(12, int(duration_second * 145 / 60 * 1.05))
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", script) if part.strip()]
    selected: list[str] = []
    words = 0
    for sentence in sentences:
        count = len(re.findall(r"\b[\w'’-]+\b", sentence))
        if selected and words + count > budget_words:
            break
        selected.append(sentence)
        words += count
    return " ".join(selected) or script


def write_script(plan: dict[str, Any], use_llm: bool = False, provider: str | None = None) -> str:
    if use_llm:
        from langchain_core.messages import HumanMessage
        instruction = {
            "task": "Write a technically accurate short narration for a vector animation video.",
            "plan": {key: value for key, value in plan.items() if not key.startswith("_")},
            "constraints": ["No invented statistics", "beginner friendly", "strong opening and memorable ending", "return JSON with script only"],
        }
        response = invoke_json(
            [HumanMessage(content=json.dumps(instruction))],
            schema=ScriptDraft,
            provider=provider,
            temperature=0.2,
            cache_payload={"stage": "scriptwriter", "plan": instruction["plan"], "schema_version": "1"},
        )
        candidate_value = response.data.script if isinstance(response.data, ScriptDraft) else ScriptDraft.model_validate(response.data).script
        candidate = str(candidate_value).strip()
        if not candidate:
            raise ValueError("LLM scriptwriter returned an empty script.")
        if estimate_narration_duration(candidate) > plan["duration_second"] * 1.25:
            log.info("LLM script exceeded target duration; shortening at sentence boundaries.")
        return fit_script_to_duration(candidate, plan["duration_second"])
    return fit_script_to_duration(fallback_script(plan["topic"], plan["duration_second"], plan.get("tone")), plan["duration_second"])

