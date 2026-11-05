import {z} from 'zod';

export const Vec2Schema = z.object({x: z.number(), y: z.number()});
export const TextElementSchema = z.object({
  id: z.string(), text: z.string(), position: Vec2Schema,
  font_size: z.number(), color: z.string(), weight: z.string(), align: z.string(), animation: z.string(),
});
export const VisualObjectSchema = z.object({
  id: z.string(), kind: z.string(), position: Vec2Schema, size: Vec2Schema,
  color: z.string(), label: z.string().nullable().optional(), data: z.record(z.string(), z.unknown()),
});
export const SceneSchema = z.object({
  id: z.string(), start_frame: z.number(), duration_frames: z.number(), scene_type: z.string(),
  background_color: z.string(), text_elements: z.array(TextElementSchema), visual_objects: z.array(VisualObjectSchema),
  animation: z.record(z.string(), z.unknown()), camera: z.record(z.string(), z.unknown()),
  narration_segment_ids: z.array(z.string()), sound_effect_ids: z.array(z.string()), transition: z.record(z.string(), z.unknown()),
});
export const ProjectSchema = z.object({
  schema_version: z.string(), project_id: z.string(), title: z.string(), original_prompt: z.string(),
  requested_duration_second: z.number(), actual_duration_second: z.number(), fps: z.number(),
  resolution: z.object({width: z.number(), height: z.number()}), aspect_ratio: z.enum(['16:9', '9:16']),
  narrator: z.object({voice: z.string(), language: z.string(), speed: z.number(), model: z.string()}),
  script: z.string(), scenes: z.array(SceneSchema),
  narration_segments: z.array(z.object({id: z.string(), text: z.string(), start_second: z.number(), duration_second: z.number(), audio_path: z.string().nullable().optional(), emotion: z.string(), delivery_speed: z.number()})),
  subtitles: z.array(z.object({id: z.string(), text: z.string(), start_frame: z.number(), end_frame: z.number()})),
  sound_effect_cues: z.array(z.unknown()), audio_assets: z.array(z.unknown()), render: z.record(z.string(), z.unknown()), metadata: z.record(z.string(), z.unknown()),
});
export type Project = z.infer<typeof ProjectSchema>;

