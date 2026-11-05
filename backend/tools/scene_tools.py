from __future__ import annotations

from typing import Any

from backend.schemas import SUPPORTED_ENVIRONMENTS, SUPPORTED_ACTIONS, SceneType

ANIMATION_TEMPLATES: tuple[str, ...] = tuple(item.value for item in SceneType)
PALETTES: dict[str, list[str]] = {
    "vectorforge": ["#101828", "#4CC9F0", "#F72585", "#FFD166", "#80ED99", "#FFFFFF"],
    "ocean": ["#081C2C", "#2EC4B6", "#71C7EC", "#CBF3F0", "#FF9F1C"],
    "sunset": ["#261447", "#FF6B6B", "#FFA94D", "#FFE66D", "#F7FFF7"],
}


def list_animation_templates() -> list[str]:
    return list(ANIMATION_TEMPLATES)


def lookup_palette(name: str = "vectorforge") -> list[str]:
    return PALETTES.get(name, PALETTES["vectorforge"])


def list_environments() -> list[str]:
    return sorted(SUPPORTED_ENVIRONMENTS)


def list_animation_actions() -> list[str]:
    return sorted(SUPPORTED_ACTIONS)


def list_character_expressions() -> list[str]:
    return ["happy", "excited", "confused", "angry", "frustrated", "surprised", "thinking", "worried", "celebrating", "neutral"]


def validate_scene_parameters(scene: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if scene.get("scene_type") not in ANIMATION_TEMPLATES:
        errors.append(f"unsupported scene_type: {scene.get('scene_type')}")
    if int(scene.get("duration_frames", 0)) <= 0:
        errors.append("duration_frames must be positive")
    return not errors, errors

