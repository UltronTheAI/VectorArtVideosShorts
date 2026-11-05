import React from 'react';
import type {CharacterIdentity} from './CharacterIdentity';

export const CharacterArms: React.FC<{identity: CharacterIdentity; action?: string; armLength?: number}> = ({identity, action, armLength=1}) => {
  const raise = action === 'point' || action === 'celebrate' || action === 'wave' || action === 'surprised';
  const leftPath = raise ? 'M52 180 Q28 150 12 105' : action === 'frustrated' ? 'M48 180 Q20 210 34 245' : action === 'shrug' ? 'M48 180 Q22 160 18 145' : 'M48 180 Q20 208 28 246';
  const rightPath = action === 'point' || action === 'celebrate' || action === 'wave' || action === 'surprised' ? 'M168 180 Q194 150 208 105' : action === 'shrug' ? 'M172 180 Q198 160 202 145' : 'M172 180 Q200 208 192 246';
  return <g transform={`scale(1 ${armLength})`}>
    <path d={leftPath} fill="none" stroke={identity.skin_color} strokeWidth="22" strokeLinecap="round" />
    <path d={rightPath} fill="none" stroke={identity.skin_color} strokeWidth="22" strokeLinecap="round" />
  </g>;
};
