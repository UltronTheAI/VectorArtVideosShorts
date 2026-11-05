"""Deterministic scene layout and collision guards for planned projects.

The renderer repeats the same orientation-aware rules in TypeScript because a
Remotion render must be self-contained. This module normalizes generated scene
data before it is persisted, preventing common overlaps in project JSON and in
older clients that do not yet use the TypeScript layout helper.
"""

from __future__ import annotations

from backend.schemas import AspectRatio, Scene


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def solve_scene_layout(scene: Scene, aspect_ratio: AspectRatio | str) -> Scene:
    """Apply safe, repeatable placements without using randomness or LLM data."""

    aspect_value = getattr(aspect_ratio, "value", aspect_ratio)
    portrait = str(aspect_value) == "9:16"
    no_character = scene.character_mode == "none" or scene.layout_template == "full_screen_diagram"

    for character in scene.characters:
        if no_character or not character.visible or character.mode == "none":
            character.visible = False
            continue
        if character.anchor == "feet":
            character.ground_y = _clamp(character.ground_y, 67 if portrait else 68, 78 if portrait else 86)
        if portrait:
            character.position.x = 50 if scene.layout_template == "reaction_closeup" else _clamp(character.position.x, 28, 72)
            character.scale = min(character.scale * (1.22 if scene.layout_template == "reaction_closeup" else 0.92), 1.35 if scene.layout_template == "reaction_closeup" else 1.12)
        else:
            character.position.x = _clamp(character.position.x, 16, 34)
            character.scale = min(character.scale, 1.12)

    for visual in scene.visual_objects:
        if scene.scene_type.value == "developer_search" and visual.kind == "computer_monitor":
            visual.position.x = 50 if portrait else 70
            visual.position.y = 45 if portrait else 48
        elif scene.scene_type.value == "full_scan" and visual.kind == "database_table":
            visual.position.x = 50 if portrait else 61
            visual.position.y = 47 if portrait else 57
        elif scene.scene_type.value in {"index_intro", "indexed_search"} and visual.kind == "btree":
            visual.position.x = 50 if portrait else 60
            visual.position.y = 45 if portrait else 54
        elif scene.scene_type.value == "comparison" and visual.kind == "comparison_panel":
            visual.position.x = 50
            visual.position.y = 48 if portrait else 58
        elif scene.scene_type.value == "ending" and visual.kind == "database_cylinder":
            visual.position.x = 50 if portrait else 67
            visual.position.y = 47 if portrait else 55

    return scene


def solve_scenes_layout(scenes: list[Scene], aspect_ratio: AspectRatio | str) -> list[Scene]:
    return [solve_scene_layout(scene, aspect_ratio) for scene in scenes]

