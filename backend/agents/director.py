from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.schemas import Action, AnimationParams, CameraParams, CharacterSpec, SoundRequest, SUPPORTED_ENVIRONMENTS, Scene, SceneType, TextElement, Vec2, VisualObject
from backend.tools.timing_tools import estimate_narration_duration, seconds_to_frames

log = logging.getLogger(__name__)

SUPPORTED_EXPRESSIONS = {"happy", "confused", "surprised", "angry", "frustrated", "neutral"}


def normalize_expression(value: object, default: str = "neutral") -> str:
    """Map descriptive LLM wording to the finite character-rig vocabulary."""
    text = str(value or "").strip().lower().replace("-", " ")
    if text in SUPPORTED_EXPRESSIONS:
        return text
    aliases = {
        "joyful": "happy", "cheerful": "happy", "excited": "surprised", "astonished": "surprised",
        "shocked": "surprised", "curious": "confused", "puzzled": "confused", "uncertain": "confused",
        "annoyed": "frustrated", "slightly frustrated": "frustrated", "stressed": "frustrated",
        "mad": "angry", "calm": "neutral", "focused": "neutral", "serious": "neutral",
    }
    if text in aliases:
        return aliases[text]
    for candidate in SUPPORTED_EXPRESSIONS:
        if candidate in text:
            return candidate
    return default if default in SUPPORTED_EXPRESSIONS else "neutral"


def split_script(script: str, target_duration: float, fps: int = 30) -> list[dict[str, Any]]:
    chunks = [part.strip() for part in re.split(r"(?<=[.!?])\s+", script) if part.strip()] or [script.strip()]
    estimates = [estimate_narration_duration(chunk) for chunk in chunks]
    scale = target_duration / (sum(estimates) or target_duration)
    cursor = 0.0
    result = []
    for index, (text, estimate) in enumerate(zip(chunks, estimates), 1):
        duration = max(0.8, estimate * scale)
        result.append({"id": f"narration-{index:02d}", "text": text, "start_second": cursor, "duration_second": duration})
        cursor += duration
    return result


def _llm_scene_hints(plan: dict[str, Any], script: str) -> list[dict[str, Any]] | None:
    try:
        from langchain_core.messages import HumanMessage
        from langchain_ollama import ChatOllama
        prompt = {
            "task": "Choose visual scene hints for a deterministic vector animation.",
            "topic": plan["topic"], "script": script,
            "supported_scene_types": [item.value for item in SceneType],
            "supported_environments": ["developer_desk", "computer_workstation", "database_server_room", "abstract_database_space", "educational_whiteboard", "digital_network", "office_interior"],
            "output": {"scenes": [{"scene_type": "developer_search", "environment": "developer_desk", "title": "", "character_expression": "neutral"}]},
        }
        response = ChatOllama(model="qwen2.5:7b", temperature=0.1, format="json").invoke([HumanMessage(content=json.dumps(prompt))])
        content = response.content
        raw = "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in content) if isinstance(content, list) else str(content)
        data = json.loads(raw)
        hints = data.get("scenes")
        return hints if isinstance(hints, list) else None
    except Exception as exc:
        log.warning("Scene-hint planning unavailable; using validated deterministic plan: %s", exc)
        return None


def direct_scenes(plan: dict[str, Any], script: str, fps: int = 30, use_llm: bool = False) -> tuple[list[Scene], list[dict[str, Any]]]:
    segments = split_script(script, float(plan["duration_second"]), fps)
    hints = _llm_scene_hints(plan, script) if use_llm else None
    database = "database" in plan["topic"].lower() and "index" in plan["topic"].lower()
    if database:
        blueprint = [
            (SceneType.DEVELOPER_SEARCH, "developer_desk", "The query looks simple...", "confused"),
            (SceneType.FULL_SCAN, "database_server_room", "Without an index: check every record", "frustrated"),
            (SceneType.INDEX_INTRO, "abstract_database_space", "Meet the organised shortcut", "surprised"),
            (SceneType.INDEXED_SEARCH, "digital_network", "Follow the path to the match", "surprised"),
            (SceneType.COMPARISON, "educational_whiteboard", "Full scan vs indexed lookup", "neutral"),
            (SceneType.ENDING, "developer_desk", "Indexes help databases find data faster", "happy"),
        ]
    else:
        blueprint = [
            (SceneType.DEVELOPER_SEARCH, "developer_desk", f"The idea behind {plan['topic']}", "curious"),
            (SceneType.EXPLAINER, "educational_whiteboard", "See the structure", "neutral"),
            (SceneType.CALLOUT, "digital_network", "Follow the important path", "surprised"),
            (SceneType.ENDING, "office_interior", "Remember the big idea", "happy"),
        ]
    scene_count = len(blueprint)
    groups: list[list[dict[str, Any]]] = [[] for _ in range(scene_count)]
    for i, segment in enumerate(segments):
        groups[min(i * scene_count // max(1, len(segments)), scene_count - 1)].append(segment)
    scenes: list[Scene] = []
    cursor_frame = 0
    colors = ["#101828", "#172554", "#20104D", "#102A43", "#16324F", "#101828"]
    for index, (scene_type, environment, title, expression) in enumerate(blueprint):
        group = groups[index]
        duration = (max((x["start_second"] + x["duration_second"] for x in group), default=(index + 1) * plan["duration_second"] / scene_count)
                    - min((x["start_second"] for x in group), default=index * plan["duration_second"] / scene_count))
        duration_frames = max(fps, seconds_to_frames(duration, fps))
        if hints and index < len(hints) and isinstance(hints[index], dict):
            hint = hints[index]
            title = str(hint.get("title") or title)
            environment = str(hint.get("environment") or environment)
            expression = normalize_expression(hint.get("character_expression"), expression)
            if environment not in SUPPORTED_ENVIRONMENTS:
                environment = blueprint[index][1]
        expression = normalize_expression(expression)
        characters = [CharacterSpec(id="developer", position=Vec2(x=24 if index != 2 else 72, y=68), expression=expression)]
        objects: list[VisualObject] = []
        sound_requests: list[SoundRequest] = []
        actions = [
            Action(target="developer", type="blink", start_frame=20, duration_frames=min(18, duration_frames - 1)),
            Action(target="developer", type="nod", start_frame=min(50, duration_frames - 1), duration_frames=min(36, max(1, duration_frames - min(50, duration_frames - 1)))),
        ]
        if scene_type == SceneType.DEVELOPER_SEARCH:
            objects = [VisualObject(id="monitor", kind="computer_monitor", position=Vec2(x=67, y=51), size=Vec2(x=34, y=27), data={"query": "SELECT * FROM records WHERE id = 42"})]
            actions += [Action(target="developer", type="point", start_frame=min(82, duration_frames - 1), duration_frames=min(45, max(1, duration_frames - min(82, duration_frames - 1))))]
            sound_requests.append(SoundRequest(category="typing", description="short keyboard typing", at_ms=500, volume=0.16))
        elif scene_type == SceneType.FULL_SCAN:
            objects = [VisualObject(id="records", kind="database_table", position=Vec2(x=61, y=57), size=Vec2(x=58, y=32), data={"count": 12, "match_index": 9})]
            actions += [Action(target="records", type="highlight", start_frame=min(20, duration_frames - 1), duration_frames=max(1, duration_frames - min(20, duration_frames - 1)), metadata={"stagger": 8})]
            sound_requests.append(SoundRequest(category="click", description="fast digital record click", at_ms=650, volume=0.22))
            sound_requests.append(SoundRequest(category="failure", description="soft search failure", at_ms=2800, volume=0.18))
        elif scene_type in {SceneType.INDEX_INTRO, SceneType.INDEXED_SEARCH}:
            objects = [VisualObject(id="btree", kind="btree", position=Vec2(x=58, y=55), size=Vec2(x=54, y=40), data={"levels": 3, "path": [0, 1, 3]})]
            actions += [Action(target="btree", type="draw_path", start_frame=min(18, duration_frames - 1), duration_frames=max(1, duration_frames - min(18, duration_frames - 1)), metadata={"path": [0, 1, 3]})]
            sound_requests.append(SoundRequest(category="whoosh", description="short cartoon transition", at_ms=350, volume=0.25))
            if scene_type == SceneType.INDEXED_SEARCH:
                sound_requests.append(SoundRequest(category="success", description="small digital success pop", at_ms=2800, volume=0.2))
        elif scene_type == SceneType.COMPARISON:
            objects = [VisualObject(id="comparison", kind="comparison_panel", position=Vec2(x=50, y=56), size=Vec2(x=78, y=35), data={"left": "many records", "right": "few branches"})]
        else:
            objects = [VisualObject(id="database", kind="database_cylinder", position=Vec2(x=65, y=55), size=Vec2(x=30, y=30), color="#4CC9F0")]
            actions += [Action(target="developer", type="celebrate", start_frame=min(40, duration_frames - 1), duration_frames=max(1, duration_frames - min(40, duration_frames - 1)))]
        scenes.append(Scene(
            id=f"scene-{index + 1:02d}", start_frame=cursor_frame, duration_frames=duration_frames, scene_type=scene_type,
            environment=environment, background_color=colors[index % len(colors)],
            text_elements=[TextElement(id=f"title-{index + 1:02d}", text=title, position=Vec2(x=50, y=12), font_size=50 if index == 0 else 40, animation="pop" if index == 0 else "slide")],
            visual_objects=objects, characters=characters, actions=actions,
            animation=AnimationParams(enter="fade", exit="fade", emphasis="highlight" if scene_type in {SceneType.FULL_SCAN, SceneType.INDEXED_SEARCH} else "none"),
            camera=CameraParams(start=Vec2(x=0, y=0), end=Vec2(x=0, y=0), zoom_start=1.0, zoom_end=1.06 if scene_type in {SceneType.DEVELOPER_SEARCH, SceneType.INDEX_INTRO} else 1.0),
            narration_segment_ids=[x["id"] for x in group], sound_effect_ids=[], sound_requests=sound_requests,
        ))
        cursor_frame += duration_frames
    return scenes, segments
