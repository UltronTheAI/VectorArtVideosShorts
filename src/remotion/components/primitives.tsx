import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Action} from '../schemas/project';

type XY = {x?: number; y?: number};
type PrimitiveProps = XY & {color?: string; opacity?: number};

export const AnimatedText: React.FC<PrimitiveProps & {text: string; size?: number}> = ({text,x=50,y=12,color='#fff',size=44,opacity=1}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config:{damping:16, stiffness:130}});
  return <div style={{position:'absolute',left:`${x}%`,top:`${y}%`,transform:`translate(-50%,-50%) scale(${interpolate(enter,[0,1],[.82,1])})`,opacity:opacity*interpolate(enter,[0,1],[0,1]),color,fontSize:size,fontWeight:800,textAlign:'center',maxWidth:'88%',lineHeight:1.08,letterSpacing:-1}}>{text}</div>;
};

const actionAt = (actions: Action[], target: string, frame: number) => actions.find((action) => action.target === target && frame >= action.start_frame && frame <= action.start_frame + action.duration_frames);
const actionProgress = (action: Action | undefined, frame: number) => action ? interpolate(frame,[action.start_frame,action.start_frame+action.duration_frames],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'}) : 0;

export const CharacterEyes: React.FC<{expression: string; blink?: boolean}> = ({expression,blink=false}) => <>
  <ellipse cx="78" cy="74" rx="7" ry={blink ? 1 : expression === 'surprised' ? 10 : 7} fill="#172033"/>
  <ellipse cx="142" cy="74" rx="7" ry={blink ? 1 : expression === 'surprised' ? 10 : 7} fill="#172033"/>
  {expression === 'angry' || expression === 'frustrated' ? <><path d="M64 58 L90 64" stroke="#172033" strokeWidth="7" strokeLinecap="round"/><path d="M130 64 L156 58" stroke="#172033" strokeWidth="7" strokeLinecap="round"/></> : null}
</>;
export const CharacterMouth: React.FC<{expression: string; speaking: boolean}> = ({expression,speaking}) => <path d={speaking ? 'M90 108 Q110 126 130 108' : expression === 'happy' ? 'M88 104 Q110 132 132 104' : expression === 'surprised' ? 'M104 104 Q110 118 116 104' : 'M94 108 Q110 112 126 108'} fill={expression === 'surprised' ? '#F72585' : 'none'} stroke="#172033" strokeWidth="6" strokeLinecap="round"/>;
export const CharacterFace: React.FC<{expression: string; speaking: boolean}> = ({expression,speaking}) => <><ellipse cx="110" cy="82" rx="70" ry="62" fill="#FFD6A5" stroke="#172033" strokeWidth="5"/><path d="M42 66 Q110 0 178 66 L170 40 Q110 -8 50 40Z" fill="#3A2E39"/><CharacterEyes expression={expression}/><CharacterMouth expression={expression} speaking={speaking}/></>;
export const CharacterBody: React.FC<{color: string}> = ({color}) => <path d="M47 160 Q110 128 173 160 L188 274 L32 274Z" fill={color} stroke="#172033" strokeWidth="6"/>;
export const CharacterArms: React.FC<{action?: string}> = ({action}) => <><path d={action === 'point' ? 'M52 180 Q28 162 4 120' : action === 'celebrate' ? 'M48 180 Q12 128 28 84' : 'M48 180 Q20 212 28 246'} fill="none" stroke="#FFD6A5" strokeWidth="22" strokeLinecap="round"/><path d={action === 'point' ? 'M168 180 Q194 162 220 120' : action === 'celebrate' ? 'M172 180 Q208 128 192 84' : 'M172 180 Q200 212 192 246'} fill="none" stroke="#FFD6A5" strokeWidth="22" strokeLinecap="round"/></>;
export const CharacterLegs: React.FC = () => <><path d="M78 270 L62 318" stroke="#172033" strokeWidth="24" strokeLinecap="round"/><path d="M142 270 L158 318" stroke="#172033" strokeWidth="24" strokeLinecap="round"/></>;

export const VectorCharacter: React.FC<{x:number;y:number;scale?:number;expression?:string;actions?:Action[];id:string;activeSpeech?:boolean}> = ({x,y,scale=1,expression='neutral',actions=[],id,activeSpeech=false}) => {
  const frame = useCurrentFrame();
  const action = actionAt(actions,id,frame);
  const type = action?.type;
  const progress = actionProgress(action,frame);
  const bob = type === 'bounce' || type === 'walk' ? Math.sin(progress * Math.PI * 4) * 8 : 0;
  const shake = type === 'shake' || expression === 'frustrated' ? Math.sin(progress * Math.PI * 12) * 5 : 0;
  const rotate = type === 'celebrate' ? Math.sin(progress * Math.PI * 2) * 5 : 0;
  const speaking = activeSpeech && Math.floor(frame / 5) % 2 === 0;
  return <svg viewBox="0 0 220 330" width="220" height="330" style={{position:'absolute',left:`${x}%`,top:`${y}%`,overflow:'visible',transform:`translate(-50%,-100%) translate(${shake}px,${bob}px) rotate(${rotate}deg) scale(${scale})`,transformOrigin:'50% 100%'}} aria-label={`${id} ${expression}`}>
    <CharacterLegs/><CharacterBody color="#4CC9F0"/><CharacterArms action={type}/><CharacterFace expression={expression} speaking={speaking}/>
  </svg>;
};

export const SpeechBubble: React.FC<{text:string;x:number;y:number;emphasis?:boolean}> = ({text,x,y,emphasis=false}) => <div style={{position:'absolute',left:`${x}%`,top:`${y}%`,transform:'translate(-50%,-50%)',padding:'14px 22px',borderRadius:18,background:'#FFFDF5',color:'#172033',fontSize:24,fontWeight:700,boxShadow:emphasis?'0 0 0 5px #FFD166':'0 8px 0 rgba(0,0,0,.16)',maxWidth:'34%',textAlign:'center'}}>{text}</div>;

export const DatabaseCylinder: React.FC<PrimitiveProps & {width?:number;height?:number}> = ({x=50,y=56,color='#4CC9F0',width=270,height=180}) => <g transform={`translate(${x * 10} ${y * 5})`} opacity=".98"><ellipse cx="0" cy="-55" rx={width/2} ry="28" fill={color} stroke="#fff" strokeWidth="5"/><path d={`M${-width/2} -55 V55 C${-width/2} 100 ${width/2} 100 ${width/2} 55 V-55`} fill={color} stroke="#fff" strokeWidth="5"/><ellipse cx="0" cy="55" rx={width/2} ry="28" fill={color} stroke="#fff" strokeWidth="5"/></g>;
export const DatabaseRecord: React.FC<{x:number;y:number;text:string;color?:string;opacity?:number}> = ({x,y,text,color='#fff',opacity=1}) => <div style={{position:'absolute',left:`${x}%`,top:`${y}%`,transform:'translate(-50%,-50%)',padding:'11px 15px',borderRadius:10,background:color,color:'#172033',fontSize:18,fontWeight:800,opacity}}>{text}</div>;
export const DatabaseTable: React.FC<{x:number;y:number;count:number;matchIndex:number;frame:number}> = ({x,y,count,matchIndex,frame}) => <div style={{position:'absolute',left:`${x}%`,top:`${y}%`,transform:'translate(-50%,-50%)',display:'grid',gridTemplateColumns:'repeat(4, 1fr)',gap:8,width:'58%'}}>{Array.from({length:count}).map((_,index)=>{const checked=frame >= index*8; const match=index===matchIndex; return <div key={index} style={{padding:'11px 6px',borderRadius:8,background:match&&checked?'#80ED99':checked?'#F72585':'#4CC9F0',color:'#172033',fontWeight:800,fontSize:16,textAlign:'center',transform:checked&&index%3===0?'scale(1.04)':'scale(1)',transition:'none'}}>{match?'id=42':`row ${index+1}`}</div>;})}</div>;
export const BTreeNode: React.FC<{x:number;y:number;label:string;active?:boolean;scale?:number}> = ({x,y,label,active=false,scale=1}) => <div style={{position:'absolute',left:`${x}%`,top:`${y}%`,transform:`translate(-50%,-50%) scale(${scale})`,padding:'14px 20px',borderRadius:14,background:active?'#FFD166':'#80ED99',color:'#172033',fontSize:20,fontWeight:900,boxShadow:active?'0 0 0 5px #F72585':'0 5px 0 rgba(0,0,0,.2)'}}>{label}</div>;
export const ConnectorPath: React.FC<{x1:number;y1:number;x2:number;y2:number;progress?:number;color?:string}> = ({x1,y1,x2,y2,progress=1,color='#fff'}) => <svg style={{position:'absolute',inset:0,width:'100%',height:'100%',pointerEvents:'none'}}><line x1={`${x1}%`} y1={`${y1}%`} x2={`${x1+(x2-x1)*progress}%`} y2={`${y1+(y2-y1)*progress}%`} stroke={color} strokeWidth="5" strokeLinecap="round"/></svg>;
export const SearchCursor: React.FC<{x:number;y:number;progress?:number}> = ({x,y,progress=1}) => <div style={{position:'absolute',left:`${x}%`,top:`${y}%`,transform:`translate(-50%,-50%) rotate(${progress*22-11}deg)`,fontSize:54,color:'#FFD166',fontWeight:900}}>⌕</div>;
export const HighlightBox: React.FC<{x:number;y:number;width:number;height:number;progress?:number}> = ({x,y,width,height,progress=1}) => <div style={{position:'absolute',left:`${x}%`,top:`${y}%`,width:`${width}%`,height:`${height}%`,transform:'translate(-50%,-50%)',border:'5px solid #FFD166',borderRadius:14,opacity:progress,boxShadow:'0 0 22px #FFD166'}}/>;
export const ProgressBar: React.FC<{x:number;y:number;width:number;progress:number;color?:string}> = ({x,y,width,progress,color='#FFD166'}) => <div style={{position:'absolute',left:`${x}%`,top:`${y}%`,width:`${width}%`,height:12,transform:'translate(-50%,-50%)',background:'rgba(255,255,255,.2)',borderRadius:12}}><div style={{height:'100%',width:`${Math.max(0,Math.min(1,progress))*100}%`,background:color,borderRadius:12}}/></div>;
export const ComparisonPanel: React.FC<{leftText:string;rightText:string;x:number;y:number;progress?:number}> = ({leftText,rightText,x,y,progress=1}) => <div style={{position:'absolute',left:`${x}%`,top:`${y}%`,transform:`translate(-50%,-50%) scale(${progress})`,display:'flex',gap:18,width:'78%'}}><div style={{flex:1,padding:24,borderRadius:18,background:'#F72585',fontSize:24,fontWeight:900,textAlign:'center'}}>{leftText}</div><div style={{flex:1,padding:24,borderRadius:18,background:'#80ED99',color:'#172033',fontSize:24,fontWeight:900,textAlign:'center'}}>{rightText}</div></div>;
export const AnimatedLabel: React.FC<{text:string;x:number;y:number;color?:string;progress?:number}> = ({text,x,y,color='#fff',progress=1}) => <div style={{position:'absolute',left:`${x}%`,top:`${y}%`,transform:`translate(-50%,-50%) translateY(${(1-progress)*18}px)`,opacity:progress,color,fontSize:22,fontWeight:800}}>{text}</div>;
export const ParticleBurst: React.FC<{x:number;y:number;progress:number;color?:string}> = ({x,y,progress,color='#FFD166'}) => <>{Array.from({length:8}).map((_,index)=><div key={index} style={{position:'absolute',left:`${x}%`,top:`${y}%`,width:10,height:10,borderRadius:'50%',background:color,transform:`translate(-50%,-50%) rotate(${index*45}deg) translateY(${-progress*70}px)`,opacity:1-progress}}/>)}</>;
export const SubtitleOverlay: React.FC<{text:string;portrait?:boolean}> = ({text,portrait=false}) => <div style={{position:'absolute',left:'7%',right:'7%',bottom:portrait?'12%':'6%',padding:'11px 17px',borderRadius:12,background:'rgba(0,0,0,.78)',color:'#fff',fontSize:portrait?'clamp(22px,4vw,36px)':'clamp(20px,2.7vw,34px)',fontWeight:700,textAlign:'center',lineHeight:1.15,whiteSpace:'normal'}}>{text}</div>;
