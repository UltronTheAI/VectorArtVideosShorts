import React from 'react';
import type {CharacterIdentity} from './CharacterIdentity';
import {CharacterFace} from './CharacterFace';

type Props = {identity: CharacterIdentity; expression: string; blink: boolean; mouthOpen: number; lookX: number; headTilt: number; frame?: number; headScale?: number};

export const CharacterHead: React.FC<Props> = ({identity, expression, blink, mouthOpen, lookX, headTilt, frame = 12, headScale = 1}) => {
  return <g transform={`translate(110 82) rotate(${headTilt}) scale(${headScale}) translate(-110 -82)`}>
    <CharacterFace identity={identity} expression={expression} blink={blink} mouthOpen={mouthOpen} lookX={lookX} frame={frame} />
    <path d={identity.hair_style === 'long' ? 'M40 70 Q55 0 110 10 Q170 0 180 72 L165 45 Q110 22 55 45Z' : 'M42 66 Q110 0 178 66 L170 40 Q110 -8 50 40Z'} fill={identity.hair_color} />
  </g>;
};
