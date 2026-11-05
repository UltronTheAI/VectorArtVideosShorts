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
    provider: str
    duration_override: float | None
    plan: dict[str, Any]
    script: str
    scenes: list[Any]
    segments: list[dict[str, Any]]
    stage_log: list[str]
    errors: list[str]


def build_generation_graph():
    graph = StateGraph(GenerationState)

    def interpret(state: GenerationState) -> GenerationState:
        plan = interpret_prompt(state["prompt"], use_llm=state.get("use_llm", False), provider=state.get("provider"))
        if state.get("duration_override") is not None:
            plan["duration_second"] = float(state["duration_override"])
        return {"plan": plan, "stage_log": ["idea_interpreter"]}

    def script(state: GenerationState) -> GenerationState:
        return {"script": write_script(state["plan"], use_llm=state.get("use_llm", False), provider=state.get("provider")), "stage_log": [*state.get("stage_log", []), "scriptwriter"]}

    def storyboard(state: GenerationState) -> GenerationState:
        scenes, segments = direct_scenes(state["plan"], state["script"], use_llm=state.get("use_llm", False), provider=state.get("provider"))
        return {"scenes": scenes, "segments": segments, "stage_log": [*state.get("stage_log", []), "storyboard_director"]}

    def acting(state: GenerationState) -> GenerationState:
        for scene in state["scenes"]:
            if scene.character_mode == "none" and scene.characters:
                raise ValueError(f"Character acting stage found characters in character-free scene {scene.id}.")
            for character in scene.characters:
                if character.mode == "none" or not character.visible:
                    continue
                if character.anchor != "feet":
                    raise ValueError(f"Character {character.id} in {scene.id} must use feet anchoring.")
        return {"stage_log": [*state.get("stage_log", []), "character_acting_director"]}

    def motion(state: GenerationState) -> GenerationState:
        for scene in state["scenes"]:
            if not scene.motion_plan.get("primary_visual"):
                raise ValueError(f"Scene {scene.id} has no primary visual motion objective.")
        return {"stage_log": [*state.get("stage_log", []), "motion_camera_director"]}

    def audio(state: GenerationState) -> GenerationState:
        for scene in state["scenes"]:
            for request in scene.sound_requests:
                if request.at_ms < 0 or request.volume < 0:
                    raise ValueError(f"Invalid audio cue in {scene.id}.")
        return {"stage_log": [*state.get("stage_log", []), "audio_sfx_director"]}

    def validate_timeline(state: GenerationState) -> GenerationState:
        previous_end = 0
        segment_ids = {segment["id"] for segment in state["segments"]}
        for scene in state["scenes"]:
            if scene.start_frame < previous_end:
                raise ValueError(f"Scene {scene.id} overlaps the previous scene.")
            if set(scene.narration_segment_ids) - segment_ids:
                raise ValueError(f"Scene {scene.id} references an unknown narration segment.")
            previous_end = scene.start_frame + scene.duration_frames
        return {"stage_log": [*state.get("stage_log", []), "timeline_validator"]}

    graph.add_node("interpret", interpret)
    graph.add_node("script", script)
    graph.add_node("storyboard", storyboard)
    graph.add_node("acting", acting)
    graph.add_node("motion", motion)
    graph.add_node("audio", audio)
    graph.add_node("validate", validate_timeline)
    graph.add_edge(START, "interpret")
    graph.add_edge("interpret", "script")
    graph.add_edge("script", "storyboard")
    graph.add_edge("storyboard", "acting")
    graph.add_edge("acting", "motion")
    graph.add_edge("motion", "audio")
    graph.add_edge("audio", "validate")
    graph.add_edge("validate", END)
    return graph.compile()


generation_graph = build_generation_graph()

