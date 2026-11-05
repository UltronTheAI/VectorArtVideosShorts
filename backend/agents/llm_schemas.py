from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PromptInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    duration_second: float = Field(ge=10, le=180)
    format: Literal["16:9", "9:16", "both"]
    topic: str = Field(min_length=1, max_length=240)
    audience: str = Field(min_length=1, max_length=120)
    tone: list[str] = Field(min_length=1, max_length=6)
    style: str = Field(min_length=1, max_length=160)
    voice: Literal["am_michael", "am_adam"]


class ScriptDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    script: str = Field(min_length=1, max_length=12000)


class SceneHint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scene_type: str = Field(min_length=1, max_length=64)
    environment: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=180)
    character_expression: str = Field(max_length=32)
    character_mode: Literal["none", "presenter", "observer", "actor", "reaction"]
    layout_template: str = Field(max_length=80)
    focus: str = Field(max_length=160)
    character_actions: list[str] = Field(max_length=8)
    camera_motion: str = Field(max_length=48)
    transition: str = Field(max_length=32)
    sfx_categories: list[str] = Field(max_length=8)


class SceneHintList(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenes: list[SceneHint] = Field(min_length=1, max_length=12)
