from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AspectRatio(str, Enum):
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"


class SceneType(str, Enum):
    DEVELOPER_SEARCH = "developer_search"
    FULL_SCAN = "full_scan"
    INDEX_INTRO = "index_intro"
    INDEXED_SEARCH = "indexed_search"
    COMPARISON = "comparison"
    ENDING = "ending"
    TITLE = "title"
    EXPLAINER = "explainer"
    CALLOUT = "callout"
    OUTRO = "outro"


SUPPORTED_ENVIRONMENTS = {
    "developer_desk", "computer_workstation", "database_server_room",
    "abstract_database_space", "educational_whiteboard", "digital_network", "office_interior",
}
SUPPORTED_ACTIONS = {
    "move", "scale", "rotate", "fade", "bounce", "shake", "blink", "walk", "point",
    "nod", "celebrate", "frustrated", "surprised", "draw_path", "highlight", "camera_pan", "camera_zoom",
}


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
    position: Vec2 = Vec2(x=50, y=50)
    size: Vec2 = Vec2(x=100, y=100)
    color: str = "#4CC9F0"
    label: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class CharacterSpec(BaseModel):
    id: str
    rig: Literal["human_simple"] = "human_simple"
    position: Vec2 = Vec2(x=50, y=65)
    expression: Literal["happy", "confused", "surprised", "angry", "frustrated", "neutral"] = "neutral"
    scale: float = Field(default=1.0, gt=0.1, le=4)
    visible: bool = True


class AnimationParams(BaseModel):
    enter: Literal["fade", "slide", "scale", "pop", "bounce", "rotate", "draw", "none"] = "fade"
    exit: Literal["fade", "slide", "scale", "none"] = "fade"
    emphasis: Literal["none", "shake", "highlight", "bounce", "rotate"] = "none"
    easing: Literal["linear", "ease", "spring"] = "ease"


class Action(BaseModel):
    target: str
    type: str
    start_frame: int = Field(ge=0)
    duration_frames: int = Field(gt=0)
    easing: Literal["linear", "ease", "spring"] = "ease"
    from_value: Vec2 | None = None
    to_value: Vec2 | None = None
    value: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def supported_type(self) -> "Action":
        if self.type not in SUPPORTED_ACTIONS:
            raise ValueError(f"unsupported animation action: {self.type}")
        return self


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
    delivery: Literal["neutral", "energetic", "calm", "urgent", "warm"] = "neutral"
    delivery_speed: float = Field(default=1.0, gt=0.5, le=1.5)
    pause_after_ms: int = Field(default=0, ge=0, le=3000)
    voice: Literal["am_michael", "am_adam"] = "am_michael"


class Subtitle(BaseModel):
    id: str
    text: str
    start_frame: int = Field(ge=0)
    end_frame: int = Field(gt=0)
    emphasis: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def ordered(self) -> "Subtitle":
        if self.end_frame <= self.start_frame:
            raise ValueError("subtitle end_frame must be greater than start_frame")
        return self


class AudioAsset(BaseModel):
    id: str
    path: str
    category: str
    provider: str = "local"
    tags: list[str] = Field(default_factory=list)
    duration_second: float = Field(default=0, ge=0)
    content_hash: str = ""
    source_url: str = ""
    author: str = ""
    licence: str = ""
    attribution_required: bool = False
    commercial_use: bool = False


class AudioEvent(BaseModel):
    asset_id: str
    type: Literal["narration", "sfx", "reaction", "music"]
    path: str
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)
    volume: float = Field(default=1.0, ge=0, le=2)


class MusicConfig(BaseModel):
    enabled: bool = False
    mood: str = ""
    volume: float = Field(default=0.12, ge=0, le=1)
    ducking: bool = True
    fade_in_ms: int = Field(default=500, ge=0)
    fade_out_ms: int = Field(default=1200, ge=0)


class SfxCue(BaseModel):
    id: str
    asset_id: str
    category: str
    start_second: float = Field(ge=0)
    volume: float = Field(default=0.22, ge=0, le=1)
    audio_path: str | None = None


class SoundRequest(BaseModel):
    category: str
    description: str
    at_ms: int = Field(default=0, ge=0)
    volume: float = Field(default=0.25, ge=0, le=1)


class Scene(BaseModel):
    id: str
    start_frame: int = Field(ge=0)
    duration_frames: int = Field(gt=0)
    scene_type: SceneType
    environment: str = "abstract_database_space"
    background_color: str = "#101828"
    text_elements: list[TextElement] = Field(default_factory=list)
    visual_objects: list[VisualObject] = Field(default_factory=list)
    characters: list[CharacterSpec] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    animation: AnimationParams = AnimationParams()
    camera: CameraParams = CameraParams()
    narration_segment_ids: list[str] = Field(default_factory=list)
    sound_effect_ids: list[str] = Field(default_factory=list)
    sound_requests: list[SoundRequest] = Field(default_factory=list)
    transition: TransitionParams = TransitionParams()

    @model_validator(mode="after")
    def supported_environment(self) -> "Scene":
        if self.environment not in SUPPORTED_ENVIRONMENTS:
            raise ValueError(f"unsupported environment: {self.environment}")
        return self


class NarratorConfig(BaseModel):
    voice: Literal["am_michael", "am_adam"] = "am_michael"
    language: str = "en-US"
    speed: float = Field(default=1.0, gt=0.5, le=1.5)
    model: str = "Kokoro-82M"
    model_version: str = "82M"


class RenderSettings(BaseModel):
    codec: str = "h264"
    audio_codec: str = "aac"
    crf: int = Field(default=18, ge=0, le=51)
    pixel_format: str = "yuv420p"
    include_subtitles: bool = True


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.1"
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
    audio_events: list[AudioEvent] = Field(default_factory=list)
    music: MusicConfig = MusicConfig()
    render: RenderSettings = RenderSettings()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_timeline(self) -> "Project":
        total_frames = round(self.actual_duration_second * self.fps)
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
            for action in scene.actions:
                if action.start_frame + action.duration_frames > scene.duration_frames:
                    raise ValueError(f"action {action.target}:{action.type} exceeds scene {scene.id}")
        return self
