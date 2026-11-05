import React from 'react';
import {AbsoluteFill, Sequence, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {ProjectSchema} from './schemas/project';
import type {Project} from './schemas/project';
import {Environment} from './components/environments';
import {
  AnimatedLabel, AnimatedText, BTreeNode, ComparisonPanel, ConnectorPath, DatabaseCylinder, DatabaseTable,
  DatabaseRecord, HighlightBox, ParticleBurst, ProgressBar, SearchCursor, SpeechBubble, SubtitleOverlay, VectorCharacter,
} from './components/primitives';

const SceneObject: React.FC<{scene: Project['scenes'][number]}> = ({scene}) => {
  const frame = useCurrentFrame();
  return <>{scene.visual_objects.map((object) => {
    const x = object.position.x;
    const y = object.position.y;
    const highlight = scene.actions.find((action) => action.target === object.id && action.type === 'highlight');
    const highlightProgress = highlight ? interpolate(frame,[highlight.start_frame,highlight.start_frame+highlight.duration_frames],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'}) : 0;
    if (object.kind === 'computer_monitor') return <div key={object.id} style={{position:'absolute',left:`${x}%`,top:`${y}%`,transform:'translate(-50%,-50%)',width:'34%',height:'26%',borderRadius:18,background:'#172033',border:'10px solid #4CC9F0',boxShadow:'0 12px 0 #263A63',padding:18,color:'#80ED99',fontFamily:'monospace',fontSize:'clamp(12px,1.6vw,24px)',lineHeight:1.55}}><div>〉 {String(object.data.query || 'SELECT *')}</div><div style={{color:'#FFD166'}}>〉 running...</div><div style={{color:'#F72585'}}>〉 rows: ???</div></div>;
    if (object.kind === 'database_table') return <><DatabaseTable x={x} y={y} count={Number(object.data.count || 12)} matchIndex={Number(object.data.match_index || 9)} frame={frame}/><SearchCursor x={20 + Math.min(70, frame * 1.8)} y={54} progress={Math.min(1,frame/180)}/><ProgressBar x={50} y={82} width={62} progress={Math.min(1, frame / Math.max(1, scene.duration_frames - 1))}/>{highlightProgress > 0.4 ? <HighlightBox x={70} y={57} width={15} height={12} progress={highlightProgress}/> : null}</>;
    if (object.kind === 'btree') { const traversal = Math.min(1, frame / Math.max(1, scene.duration_frames * .72)); return <><ConnectorPath x1={50} y1={35} x2={35} y2={57} progress={traversal} color="#80ED99"/><ConnectorPath x1={50} y1={35} x2={65} y2={57} progress={traversal} color="#80ED99"/><ConnectorPath x1={65} y1={57} x2={74} y2={75} progress={traversal} color="#FFD166"/><BTreeNode x={50} y={35} label="root" active={traversal>.1}/><BTreeNode x={35} y={57} label="A–M" active={traversal>.35}/><BTreeNode x={65} y={57} label="N–Z" active={traversal>.55}/><BTreeNode x={74} y={75} label="id=42" active={traversal>.8} scale={traversal>.8?1.12:1}/><AnimatedLabel text="narrower path" x={65} y={86} progress={traversal}/></>;
    if (object.kind === 'comparison_panel') return <ComparisonPanel x={x} y={y} leftText={String(object.data.left || 'many records')} rightText={String(object.data.right || 'few branches')} progress={Math.min(1,frame/24)}/>;
    if (object.kind === 'database_cylinder') return <svg key={object.id} viewBox="0 0 1000 1000" style={{position:'absolute',inset:0,width:'100%',height:'100%'}}><DatabaseCylinder x={x} y={y} color={object.color} width={260} height={170}/></svg>;
    return <div key={object.id} style={{position:'absolute',left:`${x}%`,top:`${y}%`,transform:'translate(-50%,-50%)'}}><AnimatedLabel text={object.label || object.kind} x={50} y={50}/></div>;
  })}</>;
};

const SceneRenderer: React.FC<{scene: Project['scenes'][number];portrait:boolean;segments:Project['narration_segments']}> = ({scene,portrait,segments}) => {
  const frame = useCurrentFrame();
  const camera = scene.camera;
  const zoom = interpolate(frame,[0,Math.max(1,scene.duration_frames)],[camera.zoom_start,camera.zoom_end],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const panX = interpolate(frame,[0,Math.max(1,scene.duration_frames)],[camera.start.x,camera.end.x],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const activeSegment = segments.find((segment) => scene.narration_segment_ids.includes(segment.id) && frame < scene.duration_frames);
  return <AbsoluteFill style={{background:scene.background_color,overflow:'hidden'}}>
    <Environment name={scene.environment} color={scene.background_color}/>
    <Sequence from={0} durationInFrames={scene.duration_frames}>
      <div style={{position:'absolute',inset:0,transform:`translateX(${panX}px) scale(${zoom})`,transformOrigin:'50% 50%'}}>
        {scene.text_elements.map((text) => <AnimatedText key={text.id} text={text.text} x={portrait?50:text.position.x} y={portrait?10:text.position.y} size={portrait?Math.min(text.font_size,42):text.font_size} color={text.color}/>) }
        {scene.characters.filter((character) => character.visible).map((character) => <VectorCharacter key={character.id} id={character.id} x={portrait?50:character.position.x} y={portrait?67:character.position.y} scale={portrait?Math.min(character.scale,1.18):character.scale} expression={character.expression} actions={scene.actions} activeSpeech={Boolean(activeSegment)}/>) }
        <SceneObject scene={scene}/>
        {scene.scene_type === 'developer_search' ? <SpeechBubble text="Where is record 42?" x={portrait?50:31} y={portrait?36:35} emphasis={frame>40}/> : null}
        {scene.scene_type === 'ending' ? <ParticleBurst x={portrait?50:27} y={52} progress={Math.min(1,frame/100)}/> : null}
      </div>
    </Sequence>
  </AbsoluteFill>;
};

export const Video: React.FC<{project: Project}> = ({project}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const portrait = project.aspect_ratio === '9:16';
  const subtitle = project.subtitles.find((item) => frame >= item.start_frame && frame < item.end_frame);
  return <AbsoluteFill style={{fontFamily:'Arial, sans-serif',background:'#101828'}}>
    {project.scenes.map((scene) => <Sequence key={scene.id} from={scene.start_frame} durationInFrames={scene.duration_frames}><SceneRenderer scene={scene} portrait={portrait} segments={project.narration_segments}/></Sequence>)}
    {subtitle ? <SubtitleOverlay text={subtitle.text} portrait={portrait}/> : null}
    <div style={{position:'absolute',top:portrait?'3%':'2.5%',right:'3%',fontSize:portrait?'16px':'18px',fontWeight:800,color:'rgba(255,255,255,.6)',letterSpacing:1}}>VECTORFORGE</div>
  </AbsoluteFill>;
};

export function parseProject(input: unknown): Project { return ProjectSchema.parse(input); }
