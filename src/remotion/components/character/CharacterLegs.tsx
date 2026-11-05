import React from 'react';
import type {CharacterIdentity} from './CharacterIdentity';

export const CharacterLegs: React.FC<{identity: CharacterIdentity; pose?: string; legLength?: number}> = ({identity, pose='standing', legLength=1}) => <g transform={`scale(1 ${legLength})`}>
  <path d={pose === 'seated' ? 'M78 270 L50 286' : 'M78 270 L62 318'} stroke={identity.pants_color} strokeWidth="24" strokeLinecap="round" />
  <path d={pose === 'seated' ? 'M142 270 L174 286' : 'M142 270 L158 318'} stroke={identity.pants_color} strokeWidth="24" strokeLinecap="round" />
  <path d={pose === 'seated' ? 'M42 286 L70 286' : 'M48 318 L76 318'} stroke={identity.shoe_color} strokeWidth="16" strokeLinecap="round" />
  <path d={pose === 'seated' ? 'M166 286 L194 286' : 'M144 318 L172 318'} stroke={identity.shoe_color} strokeWidth="16" strokeLinecap="round" />
</g>;
