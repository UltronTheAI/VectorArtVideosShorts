import React from 'react';
import {AbsoluteFill, Sequence, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {ProjectSchema} from './schemas/project';
import type {Project} from './schemas/project';
import {Environment} from './components/environments';
import {CharacterRig} from './components/character/CharacterRig';
import {defaultCharacterIdentity} from './components/character/CharacterIdentity';
import {
  AnimatedLabel, AnimatedText, BTreeNode, ComparisonPanel, ConnectorPath, DatabaseCylinder, DatabaseTable,
  HighlightBox, ParticleBurst, ProgressBar, SearchCursor, SpeechBubble, SubtitleOverlay,
} from './components/primitives';
import {computeSceneLayout, type SceneLayout} from './layout';

const BTreeVisual: React.FC<{frame: number; duration: number; portrait: boolean; scale: number}> = ({frame, duration, portrait, scale}) => {
  const traversal = Math.min(1, frame / Math.max(1, duration * 0.72));
  const positions = portrait
    ? {root: [50, 27], left: [34, 47], right: [66, 47], leaf: [66, 70]}
    : {root: [50, 34], left: [35, 56], right: [65, 56], leaf: [74, 75]};
  const active = (threshold: number) => traversal > threshold;
  return <div style={{position: 'absolute', inset: 0, transform: `scale(${scale})`, transformOrigin: '50% 50%'}}>
    <ConnectorPath x1={positions.root[0]} y1={positions.root[1]} x2={positions.left[0]} y2={positions.left[1]} progress={Math.min(1, traversal * 1.5)} color={active(.18) ? '#80ED99' : 'rgba(255,255,255,.25)'} />
    <ConnectorPath x1={positions.root[0]} y1={positions.root[1]} x2={positions.right[0]} y2={positions.right[1]} progress={Math.min(1, Math.max(0, (traversal - .18) * 1.5))} color={active(.35) ? '#80ED99' : 'rgba(255,255,255,.25)'} />
    <ConnectorPath x1={positions.right[0]} y1={positions.right[1]} x2={positions.leaf[0]} y2={positions.leaf[1]} progress={Math.min(1, Math.max(0, (traversal - .35) * 1.55))} color={active(.58) ? '#FFD166' : 'rgba(255,255,255,.25)'} />
    <BTreeNode x={positions.root[0]} y={positions.root[1]} label="root" active={active(.1)} />
    <BTreeNode x={positions.left[0]} y={positions.left[1]} label="A–M" active={active(.34)} />
    <BTreeNode x={positions.right[0]} y={positions.right[1]} label="N–Z" active={active(.5)} />
    <BTreeNode x={positions.leaf[0]} y={positions.leaf[1]} label="id=42" active={active(.8)} scale={active(.8) ? 1.12 : 1} />
    <AnimatedLabel text="narrower path" x={positions.leaf[0]} y={portrait ? 82 : 87} progress={traversal} />
  </div>;
};

const SceneObject: React.FC<{scene: Project['scenes'][number]; layout: SceneLayout; portrait: boolean}> = ({scene, layout, portrait}) => {
  const frame = useCurrentFrame();
  return <React.Fragment>{scene.visual_objects.map((object) => {
    const placement = layout.objects[object.id] ?? {x: object.position.x, y: object.position.y, scale: 1};
    const x = placement.x;
    const y = placement.y;
    const highlight = scene.actions.find((action) => action.target === object.id && action.type === 'highlight');
    const highlightProgress = highlight ? interpolate(frame, [highlight.start_frame, highlight.start_frame + highlight.duration_frames], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 0;

    if (object.kind === 'computer_monitor') {
      return <div key={object.id} style={{position: 'absolute', left: `${x}%`, top: `${y}%`, transform: `translate(-50%,-50%) scale(${placement.scale})`, width: portrait ? '62%' : '34%', height: portrait ? '22%' : '26%', borderRadius: 18, background: '#172033', border: '10px solid #4CC9F0', boxShadow: '0 12px 0 #263A63', padding: 18, color: '#80ED99', fontFamily: 'monospace', fontSize: 'clamp(12px,1.6vw,24px)', lineHeight: 1.55}}>
        <div>&gt; {String(object.data.query || 'SELECT *')}</div>
        <div style={{color: '#FFD166'}}>&gt; running...</div>
        <div style={{color: '#F72585'}}>&gt; rows: ???</div>
      </div>;
    }
    if (object.kind === 'database_table') {
      return <React.Fragment key={object.id}>
        <div style={{position: 'absolute', inset: 0, transform: `scale(${placement.scale})`, transformOrigin: '50% 50%'}}><DatabaseTable x={x} y={y} count={Number(object.data.count || 12)} matchIndex={Number(object.data.match_index || 9)} frame={frame} /></div>
        <SearchCursor x={portrait ? 50 : 20 + Math.min(70, frame * 1.8)} y={portrait ? 47 : 54} progress={Math.min(1, frame / 180)} />
        <ProgressBar x={50} y={portrait ? 69 : 82} width={portrait ? 76 : 62} progress={Math.min(1, frame / Math.max(1, scene.duration_frames - 1))} />
        {highlightProgress > 0.4 ? <HighlightBox x={portrait ? 62 : 70} y={portrait ? 50 : 57} width={portrait ? 24 : 15} height={portrait ? 8 : 12} progress={highlightProgress} /> : null}
      </React.Fragment>;
    }
    if (object.kind === 'btree') return <BTreeVisual key={object.id} frame={frame} duration={scene.duration_frames} portrait={portrait} scale={placement.scale} />;
    if (object.kind === 'comparison_panel') return <ComparisonPanel key={object.id} x={x} y={y} leftText={String(object.data.left || 'many records')} rightText={String(object.data.right || 'few branches')} progress={Math.min(1, frame / 24)} />;
    if (object.kind === 'database_cylinder') return <svg key={object.id} viewBox="0 0 1000 1000" style={{position: 'absolute', inset: 0, width: '100%', height: '100%', transform: `scale(${placement.scale})`}}><DatabaseCylinder x={x} y={y} color={object.color} width={260} height={170} /></svg>;
    return <div key={object.id} style={{position: 'absolute', left: `${x}%`, top: `${y}%`, transform: 'translate(-50%,-50%)'}}><AnimatedLabel text={object.label || object.kind} x={50} y={50} /></div>;
  })}</React.Fragment>;
};

const SceneRenderer: React.FC<{scene: Project['scenes'][number]; portrait: boolean; segments: Project['narration_segments']; identities: Project['character_identities']; lipSync: Project['lip_sync']}> = ({scene, portrait, segments, identities, lipSync}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const layout = computeSceneLayout(scene, portrait);
  const camera = scene.camera;
  const zoom = interpolate(frame, [0, Math.max(1, scene.duration_frames)], [camera.zoom_start, camera.zoom_end], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const panX = interpolate(frame, [0, Math.max(1, scene.duration_frames)], [camera.start.x, camera.end.x], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const globalFrame = scene.start_frame + frame;
  const activeSegment = segments.find((segment) => scene.narration_segment_ids.includes(segment.id) && globalFrame >= Math.round(segment.start_second * fps) && globalFrame < Math.round((segment.start_second + segment.duration_second) * fps));
  const nearestLip = lipSync.reduce<Project['lip_sync'][number] | undefined>((best, sample) => !best || Math.abs(sample.frame - globalFrame) < Math.abs(best.frame - globalFrame) ? sample : best, undefined);
  const mouthOpen = activeSegment && nearestLip?.speech_active ? nearestLip.mouth_open : 0;
  return <AbsoluteFill style={{background: scene.background_color, overflow: 'hidden'}}>
    <Environment name={scene.environment} color={scene.background_color} />
    <Sequence from={0} durationInFrames={scene.duration_frames}>
      <div style={{position: 'absolute', inset: 0, transform: `translateX(${panX}px) scale(${zoom})`, transformOrigin: '50% 50%'}}>
        {scene.text_elements.map((text) => <AnimatedText key={text.id} text={text.text} x={layout.title.x} y={layout.title.y} size={portrait ? Math.min(text.font_size, 42) : text.font_size} color={text.color} />)}
        <SceneObject scene={scene} layout={layout} portrait={portrait} />
        {scene.characters.filter((character) => character.visible && character.mode !== 'none' && scene.character_mode !== 'none' && layout.character[character.id]?.visible !== false).map((character) => {
          const placement = layout.character[character.id] ?? {x: character.position.x, groundY: character.anchor === 'feet' ? character.ground_y : character.position.y, scale: character.scale, visible: true};
          const identity = identities.find((item) => item.id === character.identity_id) ?? defaultCharacterIdentity;
          return <CharacterRig key={character.id} identity={identity} id={character.id} x={placement.x} groundY={placement.groundY} scale={placement.scale} expression={character.expression} pose={character.pose} actions={scene.actions} frame={frame} mouthOpen={mouthOpen} />;
        })}
        {scene.scene_type === 'developer_search' ? <SpeechBubble text="Where is record 42?" x={portrait ? 50 : 31} y={portrait ? 30 : 35} emphasis={frame > 40} /> : null}
        {scene.scene_type === 'ending' ? <ParticleBurst x={portrait ? 50 : 27} y={portrait ? 42 : 52} progress={Math.min(1, frame / 100)} /> : null}
      </div>
    </Sequence>
  </AbsoluteFill>;
};

export const Video: React.FC<{project: Project}> = ({project}) => {
  const frame = useCurrentFrame();
  const portrait = project.aspect_ratio === '9:16';
  const subtitle = project.subtitles.find((item) => frame >= item.start_frame && frame < item.end_frame);
  return <AbsoluteFill style={{fontFamily: 'Arial, sans-serif', background: '#101828'}}>
    {project.scenes.map((scene) => <Sequence key={scene.id} from={scene.start_frame} durationInFrames={scene.duration_frames}><SceneRenderer scene={scene} portrait={portrait} segments={project.narration_segments} identities={project.character_identities} lipSync={project.lip_sync} /></Sequence>)}
    {subtitle ? <SubtitleOverlay text={subtitle.text} portrait={portrait} /> : null}
  </AbsoluteFill>;
};

export function parseProject(input: unknown): Project {
  return ProjectSchema.parse(input);
}
