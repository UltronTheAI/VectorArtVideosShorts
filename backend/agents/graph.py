from __future__ import annotations

import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.agents.director import direct_scenes
from backend.agents.scriptwriter import interpret_prompt, write_script

log = logging.getLogger(__name__)


class GenerationState(TypedDict, total=False):
    prompt: str
    use_llm: bool
    plan: dict[str, Any]
    script: str
    scenes: list[Any]
    segments: list[dict[str, Any]]
    errors: list[str]


def build_generation_graph():
    graph = StateGraph(GenerationState)

    def interpret(state: GenerationState) -> GenerationState:
        return {"plan": interpret_prompt(state["prompt"])}

    def script(state: GenerationState) -> GenerationState:
        return {"script": write_script(state["plan"], use_llm=state.get("use_llm", False))}

    def direct(state: GenerationState) -> GenerationState:
        scenes, segments = direct_scenes(state["plan"], state["script"])
        return {"scenes": scenes, "segments": segments}

    graph.add_node("interpret", interpret)
    graph.add_node("script", script)
    graph.add_node("direct", direct)
    graph.add_edge(START, "interpret")
    graph.add_edge("interpret", "script")
    graph.add_edge("script", "direct")
    graph.add_edge("direct", END)
    return graph.compile()


generation_graph = build_generation_graph()

