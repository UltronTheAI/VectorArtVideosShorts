from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AspectRatio(str, Enum):
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"


class SceneType(str, Enum):
    TITLE = "title"
    EXPLAINER = "explainer"
    DATABASE_SCAN = "database_scan"
    INDEX_TRAVERSAL = "index_traversal"
    COMPARISON = "comparison"
    CALLOUT = "callout"
    OUTRO = "outro"


class Resolution(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class Vec2(BaseModel):
    x: float
    y: float


class TextElement(BaseModel):
    id: str
    text: str
    position: Vec2 = Vec2(x=0, y=0)
    font_size: int = Field(default=48, gt=0)
    color: str = "#FFFFFF"
    weight: Literal["400", "500", "600", "700", "800"] = "700"
    align: Literal["left", "center", "right"] = "center"
    animation: Literal["fade", "slide", "scale", "pop", "bounce", "highlight"] = "fade"


class VisualObject(BaseModel):
    id: str
    kind: str
    position: Vec2 = Vec2(x=0, y=0)
    size: Vec2 = Vec2(x=100, y=100)
    color: str = "#4CC9F0"
    label: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class AnimationParams(BaseModel):
    enter: Literal["fade", "slide", "scale", "pop", "bounce", "rotate", "draw", "none"] = "fade"
    exit: Literal["fade", "slide", "scale", "none"] = "fade"
    emphasis: Literal["none", "shake", "highlight", "bounce", "rotate"] = "none"
    easing: Literal["linear", "ease", "spring"] = "ease"


class CameraParams(BaseModel):
    start: Vec2 = Vec2(x=0, y=0)
    end: Vec2 = Vec2(x=0, y=0)
    zoom_start: float = Field(default=1.0, gt=0)
    zoom_end: float = Field(default=1.0, gt=0)


class TransitionParams(BaseModel):
    kind: Literal["cut", "fade", "slide", "wipe"] = "fade"
    frames: int = Field(default=12, ge=0)


class NarrationSegment(BaseModel):
    id: str
    text: str
    start_second: float = Field(ge=0)
    duration_second: float = Field(gt=0)
    audio_path: str | None = None
    emotion: Literal["neutral", "humour", "excitement", "surprise", "frustration"] = "neutral"
    delivery_speed: float = Field(default=1.0, gt=0.5, le=1.5)


class Subtitle(BaseModel):
    id: str
    text: str
    start_frame: int = Field(ge=0)
    end_frame: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> "Subtitle":
        if self.end_frame <= self.start_frame:
            raise ValueError("subtitle end_frame must be greater than start_frame")
        return self


class AudioAsset(BaseModel):
    id: str
    path: str
    category: str
    tags: list[str] = Field(default_factory=list)
    duration_second: float = Field(default=0, ge=0)
    source_url: str = ""
    author: str = ""
    licence: str = ""
    attribution_required: bool = False
    commercial_use: bool = False


class SfxCue(BaseModel):
    id: str
    asset_id: str
    category: str
    start_second: float = Field(ge=0)
    volume: float = Field(default=0.22, ge=0, le=1)
    audio_path: str | None = None


class Scene(BaseModel):
    id: str
    start_frame: int = Field(ge=0)
    duration_frames: int = Field(gt=0)
    scene_type: SceneType
    background_color: str = "#101828"
    text_elements: list[TextElement] = Field(default_factory=list)
    visual_objects: list[VisualObject] = Field(default_factory=list)
    animation: AnimationParams = AnimationParams()
    camera: CameraParams = CameraParams()
    narration_segment_ids: list[str] = Field(default_factory=list)
    sound_effect_ids: list[str] = Field(default_factory=list)
    transition: TransitionParams = TransitionParams()


class NarratorConfig(BaseModel):
    voice: str = "am_michael"
    language: str = "en-US"
    speed: float = Field(default=1.0, gt=0.5, le=1.5)
    model: str = "Kokoro-82M"


class RenderSettings(BaseModel):
    codec: str = "h264"
    audio_codec: str = "aac"
    crf: int = Field(default=18, ge=0, le=51)
    pixel_format: str = "yuv420p"
    include_subtitles: bool = True


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    project_id: str
    title: str
    original_prompt: str
    requested_duration_second: float = Field(gt=0)
    actual_duration_second: float = Field(gt=0)
    fps: int = Field(default=30, gt=0)
    resolution: Resolution
    aspect_ratio: AspectRatio
    narrator: NarratorConfig = NarratorConfig()
    script: str
    scenes: list[Scene] = Field(min_length=1)
    narration_segments: list[NarrationSegment] = Field(min_length=1)
    subtitles: list[Subtitle] = Field(default_factory=list)
    sound_effect_cues: list[SfxCue] = Field(default_factory=list)
    audio_assets: list[AudioAsset] = Field(default_factory=list)
    render: RenderSettings = RenderSettings()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("actual_duration_second")
    @classmethod
    def reasonable_duration(cls, value: float) -> float:
        if value < 0.1 or value > 180.0:
            raise ValueError("actual duration must be between 0.1 and 180 seconds")
        return value

    @model_validator(mode="after")
    def validate_timeline(self) -> "Project":
        total_frames = round(self.actual_duration_second * self.fps)
        if not self.scenes:
            raise ValueError("at least one scene is required")
        previous_end = 0
        for scene in self.scenes:
            if scene.start_frame < previous_end:
                raise ValueError(f"scene {scene.id} overlaps the previous scene")
            previous_end = scene.start_frame + scene.duration_frames
        if previous_end > total_frames + self.fps:
            raise ValueError("scene timeline exceeds project duration")
        known_segments = {segment.id for segment in self.narration_segments}
        for scene in self.scenes:
            unknown = set(scene.narration_segment_ids) - known_segments
            if unknown:
                raise ValueError(f"scene {scene.id} references unknown narration segments: {sorted(unknown)}")
        return self

