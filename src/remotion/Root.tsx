import React from 'react';
import {Composition} from 'remotion';
import type {CalculateMetadataFunction} from 'remotion';
import {ProjectPropsSchema} from './schemas/project';
import type {Project} from './schemas/project';
import {Video} from './Video';

const previewProject: Project = {
  schema_version:'1.1', project_id:'development-preview', title:'VectorForge Preview', original_prompt:'', requested_duration_second:8, actual_duration_second:8, fps:30,
  resolution:{width:1920,height:1080}, aspect_ratio:'16:9', narrator:{voice:'am_michael',language:'en-US',speed:1,model:'Kokoro-82M',model_version:'82M'}, script:'',
  scenes:[{
    id:'preview-scene', start_frame:0, duration_frames:240, scene_type:'developer_search', environment:'developer_desk', background_color:'#101828',
    text_elements:[{id:'preview-title',text:'VectorForge Preview',position:{x:50,y:12},font_size:60,color:'#fff',weight:'800',align:'center',animation:'pop'}],
    visual_objects:[{id:'monitor',kind:'computer_monitor',position:{x:66,y:52},size:{x:34,y:27},color:'#4CC9F0',data:{query:'SELECT * FROM records'}}],
    characters:[{id:'developer',rig:'human_simple',position:{x:24,y:68},expression:'confused',scale:1,visible:true}],
    actions:[{target:'developer',type:'blink',start_frame:20,duration_frames:18,easing:'ease',metadata:{}}],
    animation:{enter:'fade',exit:'fade',emphasis:'none',easing:'ease'},camera:{start:{x:0,y:0},end:{x:0,y:0},zoom_start:1,zoom_end:1.04},narration_segment_ids:[],sound_effect_ids:[],transition:{kind:'fade',frames:12},
  }],
  narration_segments:[{id:'preview',text:'Development preview',start_second:0,duration_second:8,audio_path:null,emotion:'neutral',delivery:'neutral',delivery_speed:1,pause_after_ms:0,voice:'am_michael'}],
  subtitles:[],sound_effect_cues:[],audio_assets:[],render:{codec:'h264',audio_codec:'aac',crf:18,pixel_format:'yuv420p',include_subtitles:true},metadata:{development_preview:true},
};

export type VideoProps = {project: Project};

export function resolveProject(input: unknown): Project {
  const parsed = ProjectPropsSchema.safeParse(input);
  if (!parsed.success) {
    const detail = parsed.error.issues.slice(0, 8).map((issue) => `${issue.path.join('.') || 'project'}: ${issue.message}`).join('; ');
    throw new Error(`VectorForge project props are invalid. Expected { project: {...} }. ${detail}`);
  }
  return parsed.data.project;
}

const calculateMetadata: CalculateMetadataFunction<VideoProps> = ({props}) => {
  const project = resolveProject(props);
  return {
    durationInFrames: Math.max(1, Math.round(project.actual_duration_second * project.fps)),
    fps: project.fps,
    width: project.resolution.width,
    height: project.resolution.height,
    props: {project},
  };
};

export const RemotionRoot: React.FC = () => <Composition<VideoProps>
  id="VectorForge" component={Video} defaultProps={{project: previewProject}}
  durationInFrames={240} fps={30} width={1920} height={1080} calculateMetadata={calculateMetadata}
/>;
