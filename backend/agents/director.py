from __future__ import annotations

import re
from typing import Any

from backend.schemas import (
    AnimationParams, CameraParams, Scene, SceneType, TextElement, Vec2, VisualObject,
)
from backend.tools.timing_tools import estimate_narration_duration, seconds_to_frames


def split_script(script: str, target_duration: float, fps: int = 30) -> list[dict[str, Any]]:
    chunks = [part.strip() for part in re.split(r"(?<=[.!?])\s+", script) if part.strip()]
    if not chunks:
        chunks = [script.strip()]
    estimates = [estimate_narration_duration(chunk) for chunk in chunks]
    total = sum(estimates) or target_duration
    scale = target_duration / total
    cursor = 0.0
    result = []
    for index, (text, estimate) in enumerate(zip(chunks, estimates), 1):
        duration = max(1.0, estimate * scale)
        result.append({"id": f"narration-{index:02d}", "text": text, "start_second": cursor, "duration_second": duration})
        cursor += duration
    return result


def direct_scenes(plan: dict[str, Any], script: str, fps: int = 30) -> tuple[list[Scene], list[dict[str, Any]]]:
    segments = split_script(script, float(plan["duration_second"]), fps)
    topic = plan["topic"].lower()
    if "database" in topic and "index" in topic:
        types = [SceneType.TITLE, SceneType.DATABASE_SCAN, SceneType.INDEX_TRAVERSAL, SceneType.COMPARISON, SceneType.OUTRO]
    else:
        types = [SceneType.TITLE, SceneType.EXPLAINER, SceneType.CALLOUT, SceneType.OUTRO]
    scenes: list[Scene] = []
    palette = ["#101828", "#172554", "#20104D", "#102A43", "#101828"]
    seg_index = 0
    scene_count = len(types)
    # Keep at least one segment per scene, then attach remaining segments in order.
    groups: list[list[dict[str, Any]]] = [[] for _ in range(scene_count)]
    for i, segment in enumerate(segments):
        groups[min(i * scene_count // max(1, len(segments)), scene_count - 1)].append(segment)
    cursor_frame = 0
    for i, (scene_type, group) in enumerate(zip(types, groups), 1):
        if not group:
            duration = max(1.0, plan["duration_second"] / scene_count)
            segment_ids: list[str] = []
        else:
            start = min(x["start_second"] for x in group)
            end = max(x["start_second"] + x["duration_second"] for x in group)
            duration = max(1.0, end - start)
            segment_ids = [x["id"] for x in group]
        frames = max(fps, seconds_to_frames(duration, fps))
        title = {
            SceneType.TITLE: "How does a database index work?",
            SceneType.DATABASE_SCAN: "Without an index: scan, scan, scan...",
            SceneType.INDEX_TRAVERSAL: "An organised path narrows the search",
            SceneType.COMPARISON: "Full scan vs indexed lookup",
            SceneType.OUTRO: "An index is a shortcut map—not magic.",
            SceneType.EXPLAINER: f"The idea behind {plan['topic']}",
            SceneType.CALLOUT: "Make the invisible structure visible",
        }[scene_type]
        objects: list[VisualObject] = []
        if scene_type == SceneType.DATABASE_SCAN:
            objects = [VisualObject(id="records", kind="database", position=Vec2(x=50, y=52), size=Vec2(x=55, y=32), color="#4CC9F0", data={"count": 8})]
        elif scene_type == SceneType.INDEX_TRAVERSAL:
            objects = [VisualObject(id="tree", kind="tree", position=Vec2(x=50, y=56), size=Vec2(x=62, y=38), color="#80ED99", data={"levels": 3})]
        elif scene_type == SceneType.COMPARISON:
            objects = [VisualObject(id="compare", kind="comparison", position=Vec2(x=50, y=57), size=Vec2(x=76, y=36), color="#FFD166", data={"left": "full scan", "right": "index"})]
        scenes.append(Scene(
            id=f"scene-{i:02d}", start_frame=cursor_frame, duration_frames=frames, scene_type=scene_type,
            background_color=palette[(i - 1) % len(palette)],
            text_elements=[TextElement(id=f"title-{i:02d}", text=title, position=Vec2(x=50, y=14), font_size=54 if i == 1 else 40, animation="pop" if i == 1 else "slide")],
            visual_objects=objects, animation=AnimationParams(enter="fade", exit="fade", emphasis="highlight" if scene_type in (SceneType.DATABASE_SCAN, SceneType.INDEX_TRAVERSAL) else "none"),
            camera=CameraParams(start=Vec2(x=0, y=0), end=Vec2(x=0, y=0), zoom_start=1.0, zoom_end=1.04 if scene_type == SceneType.INDEX_TRAVERSAL else 1.0),
            narration_segment_ids=segment_ids, sound_effect_ids=[],
        ))
        cursor_frame += frames
    return scenes, segments

