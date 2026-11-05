import {z} from 'zod';

export const Vec2Schema = z.object({x: z.number(), y: z.number()});
export const TextElementSchema = z.object({
  id: z.string(), text: z.string(), position: Vec2Schema, font_size: z.number(), color: z.string(),
  weight: z.string(), align: z.string(), animation: z.string(),
});
export const VisualObjectSchema = z.object({
  id: z.string(), kind: z.string(), position: Vec2Schema, size: Vec2Schema, color: z.string(),
  label: z.string().nullable().optional(), data: z.record(z.string(), z.unknown()),
});
export const CharacterSchema = z.object({
  id: z.string(), rig: z.string(), position: Vec2Schema, expression: z.string(), scale: z.number(), visible: z.boolean(),
  identity_id: z.string().default('developer'), mode: z.enum(['none', 'presenter', 'observer', 'actor', 'reaction']).default('presenter'),
  anchor: z.enum(['feet', 'center']).default('feet'), ground_y: z.number().default(82), pose: z.enum(['standing', 'seated', 'walking', 'celebrating']).default('standing'),
});
export const CharacterIdentitySchema = z.object({
  id: z.string(), skin_color: z.string(), hair_color: z.string(), hair_style: z.string(), shirt_color: z.string(), pants_color: z.string(), shoe_color: z.string(), body_proportions: z.record(z.string(), z.number()),
});
export const CharacterPlacementSchema = z.object({anchor: z.enum(['feet', 'center']).default('feet'), ground_y: z.number().default(82), x: z.number().default(50), scale: z.number().default(1)});
export const LipSyncSampleSchema = z.object({frame: z.number(), mouth_open: z.number(), speech_active: z.boolean(), viseme: z.string()});
export const ActionSchema = z.object({
  target: z.string(), type: z.string(), start_frame: z.number(), duration_frames: z.number(), easing: z.string(),
  from_value: Vec2Schema.nullable().optional(), to_value: Vec2Schema.nullable().optional(), value: z.number().nullable().optional(),
  metadata: z.record(z.string(), z.unknown()),
});
export const SceneSchema = z.object({
  id: z.string(), start_frame: z.number(), duration_frames: z.number(), scene_type: z.string(), environment: z.string(),
  background_color: z.string(), text_elements: z.array(TextElementSchema), visual_objects: z.array(VisualObjectSchema),
  characters: z.array(CharacterSchema), actions: z.array(ActionSchema), animation: z.record(z.string(), z.unknown()),
  camera: z.record(z.string(), z.unknown()), narration_segment_ids: z.array(z.string()),
  sound_effect_ids: z.array(z.string()), sound_requests: z.array(z.unknown()).default([]), character_mode: z.enum(['none', 'presenter', 'observer', 'actor', 'reaction']).default('presenter'), focus: z.string().default(''),
  layout_template: z.string().default('character_left_diagram_right'), focal_point: Vec2Schema.default({x: 50, y: 50}), motion_plan: z.record(z.string(), z.unknown()).default({}), transition: z.record(z.string(), z.unknown()),
});
export const NarrationSegmentSchema = z.object({
  id: z.string(), text: z.string(), start_second: z.number(), duration_second: z.number(), audio_path: z.string().nullable().optional(),
  emotion: z.string(), delivery: z.string(), delivery_speed: z.number(), pause_after_ms: z.number(), voice: z.string(),
});
export const ProjectSchema = z.object({
  schema_version: z.string(), project_id: z.string(), title: z.string(), original_prompt: z.string(),
  requested_duration_second: z.number(), actual_duration_second: z.number(), fps: z.number(),
  resolution: z.object({width: z.number(), height: z.number()}), aspect_ratio: z.enum(['16:9', '9:16']),
  narrator: z.object({voice: z.string(), language: z.string(), speed: z.number(), model: z.string(), model_version: z.string()}),
  script: z.string(), scenes: z.array(SceneSchema), narration_segments: z.array(NarrationSegmentSchema), character_identities: z.array(CharacterIdentitySchema).default([]), lip_sync: z.array(LipSyncSampleSchema).default([]),
  subtitles: z.array(z.object({id: z.string(), text: z.string(), start_frame: z.number(), end_frame: z.number(), emphasis: z.array(z.string())})),
  sound_effect_cues: z.array(z.unknown()), audio_assets: z.array(z.unknown()), audio_events: z.array(z.unknown()).default([]),
  music: z.record(z.string(), z.unknown()).default({}), render: z.record(z.string(), z.unknown()), metadata: z.record(z.string(), z.unknown()),
});
export const ProjectPropsSchema = z.object({project: ProjectSchema});
export type Project = z.infer<typeof ProjectSchema>;
export type Action = z.infer<typeof ActionSchema>;
