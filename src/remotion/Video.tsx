import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {Project, ProjectSchema} from './schemas/project';
import {AnimatedText, Arrow, ComparisonPanel, ConnectorLine, DatabaseCylinder, DatabaseRecord, ProgressIndicator, SubtitleOverlay, TreeNode} from './components/primitives';

const SceneVisual: React.FC<{scene: Project['scenes'][number]}> = ({scene}) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, Math.max(1, scene.duration_frames)], [0, 1], {extrapolateLeft:'clamp', extrapolateRight:'clamp'});
  const object = scene.visual_objects[0];
  if (scene.scene_type === 'database_scan') return <><DatabaseCylinder/><div style={{position:'absolute',left:'50%',top:'55%',transform:'translate(-50%,-50%)',width:'70%',display:'flex',justifyContent:'space-around'}}>{Array.from({length:8}).map((_,i)=><DatabaseRecord key={i} text={i===6?'MATCH':'row '+(i+1)} x={12+i*11} y={55}/>)}</div><ProgressIndicator progress={p}/></>;
  if (scene.scene_type === 'index_traversal') return <><TreeNode text="INDEX" x={50} y={35}/><ConnectorLine x={50} y={47} width={220}/><TreeNode text="A–M" x={32} y={56}/><TreeNode text="N–Z" x={68} y={56}/><Arrow x={64} y={70} length={150}/><DatabaseRecord text="target record" x={50} y={78}/></>;
  if (scene.scene_type === 'comparison') return <ComparisonPanel leftText="Scan: many rows" rightText="Index: narrow path"/>;
  if (object?.kind === 'tree') return <TreeNode text="the useful structure"/>;
  return null;
};

export const Video: React.FC<{project: Project}> = ({project}) => {
  const frame = useCurrentFrame();
  const scene = project.scenes.find(s => frame >= s.start_frame && frame < s.start_frame + s.duration_frames) ?? project.scenes[project.scenes.length - 1];
  const subtitle = project.subtitles.find(s => frame >= s.start_frame && frame < s.end_frame);
  const localFrame = frame - scene.start_frame;
  return <AbsoluteFill style={{background:scene.background_color, fontFamily:'Arial, sans-serif', overflow:'hidden'}}>
    <div style={{position:'absolute',inset:0,transform:`scale(${1 + Math.min(0.04, localFrame / Math.max(1, scene.duration_frames) * .04)})`}}>
      {scene.text_elements.map(t => <AnimatedText key={t.id} text={t.text} x={t.position.x} y={t.position.y} size={t.font_size} color={t.color}/>) }
      <SceneVisual scene={scene}/>
    </div>
    {subtitle && <SubtitleOverlay text={subtitle.text}/>} 
  </AbsoluteFill>;
};

export function parseProject(input: unknown): Project { return ProjectSchema.parse(input); }

