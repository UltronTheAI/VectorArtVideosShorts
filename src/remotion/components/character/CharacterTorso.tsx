import React from 'react';
import type {CharacterIdentity} from './CharacterIdentity';

export const CharacterTorso: React.FC<{identity: CharacterIdentity; breathing: number; torsoScale?: number}> = ({identity, breathing, torsoScale = 1}) => <g transform={`translate(110 220) scale(${torsoScale}) translate(-110 ${-220 + breathing})`}>
  <path d="M47 160 Q110 128 173 160 L188 274 L32 274Z" fill={identity.shirt_color} stroke="#172033" strokeWidth="6" />
  <path d="M84 164 Q110 180 136 164" fill="none" stroke="rgba(255,255,255,.5)" strokeWidth="6" />
</g>;
