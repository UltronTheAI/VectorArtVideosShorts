import React from 'react';
import {interpolate} from 'remotion';
import type {CharacterIdentity} from './CharacterIdentity';

type Props = {identity: CharacterIdentity; expression: string; blink: boolean; mouthOpen: number; lookX: number; frame?: number};

/** Facial features are isolated so the rig can swap expressions without changing identity. */
export const CharacterFace: React.FC<Props> = ({identity, expression, blink, mouthOpen, lookX, frame = 12}) => {
  const surprised = expression === 'surprised' || expression === 'excited';
  const happy = expression === 'happy' || expression === 'celebrating';
  const worried = expression === 'worried' || expression === 'confused' || expression === 'frustrated' || expression === 'thinking';
  const angry = expression === 'angry';
  const mouthHeight = Math.max(2, mouthOpen * 20);
  const expressionMix = interpolate(frame, [0, 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const eyeOpen = blink ? 1 : surprised ? 11 : 8;
  const animatedEyeOpen = interpolate(expressionMix, [0, 1], [Math.min(eyeOpen, 4), eyeOpen]);
  return <>
    <ellipse cx="110" cy="82" rx="70" ry="62" fill={identity.skin_color} stroke="#172033" strokeWidth="5" />
    <path d={angry ? 'M62 62 Q78 48 92 52' : worried ? 'M62 57 Q78 48 92 57' : 'M62 55 Q78 61 92 55'} fill="none" stroke="#172033" strokeWidth="6" strokeLinecap="round" />
    <path d={angry ? 'M128 52 Q142 48 158 62' : worried ? 'M128 57 Q142 48 158 57' : 'M128 55 Q142 61 158 55'} fill="none" stroke="#172033" strokeWidth="6" strokeLinecap="round" />
    <ellipse cx={78 + lookX} cy="76" rx="8" ry={animatedEyeOpen} fill="#172033" />
    <ellipse cx={142 + lookX} cy="76" rx="8" ry={animatedEyeOpen} fill="#172033" />
    {happy ? <path d="M88 105 Q110 132 132 105" fill="none" stroke="#172033" strokeWidth="6" strokeLinecap="round" /> : <ellipse cx="110" cy="108" rx={mouthOpen > .15 ? 18 : 14} ry={mouthHeight} fill={mouthOpen > .15 ? '#F72585' : 'none'} stroke="#172033" strokeWidth="5" />}
    {happy ? <circle cx="58" cy="102" r="9" fill="#F58A9B" opacity=".35" /> : null}
    {happy ? <circle cx="162" cy="102" r="9" fill="#F58A9B" opacity=".35" /> : null}
  </>;
};
