import React from 'react';
import {Composition, CalculateMetadataFunction} from 'remotion';
import {Video} from './Video';
import {Project, ProjectSchema} from './schemas/project';

const fallback: Project = {
  schema_version:'1.0', project_id:'preview', title:'VectorForge Preview', original_prompt:'', requested_duration_second:30, actual_duration_second:30, fps:30,
  resolution:{width:1920,height:1080}, aspect_ratio:'16:9', narrator:{voice:'am_michael',language:'en-US',speed:1,model:'Kokoro-82M'}, script:'',
  scenes:[{id:'scene-01',start_frame:0,duration_frames:900,scene_type:'title',background_color:'#101828',text_elements:[{id:'title',text:'VectorForge',position:{x:50,y:50},font_size:72,color:'#fff',weight:'800',align:'center',animation:'pop'}],visual_objects:[],animation:{},camera:{},narration_segment_ids:[],sound_effect_ids:[],transition:{}}],
  narration_segments:[],subtitles:[],sound_effect_cues:[],audio_assets:[],render:{},metadata:{},
};
const calculateMetadata: CalculateMetadataFunction<{project: Project}> = async ({props}) => {
  const directProject = ProjectSchema.safeParse(props);
  const project = props.project ?? (directProject.success ? directProject.data : fallback);
  return {durationInFrames:Math.max(1, Math.round(project.actual_duration_second * project.fps)), fps:project.fps, width:project.resolution.width, height:project.resolution.height, props:{project}};
};
export const RemotionRoot: React.FC = () => <Composition id="VectorForge" component={Video} defaultProps={{project:fallback}} durationInFrames={900} fps={30} width={1920} height={1080} calculateMetadata={calculateMetadata}/>;

