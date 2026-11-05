import React from 'react';
import type {Action} from '../../schemas/project';
import type {CharacterIdentity} from './CharacterIdentity';
import {CharacterAnimator, animateCharacter} from './CharacterAnimator';
import {CharacterArms} from './CharacterArms';
import {CharacterHead} from './CharacterHead';
import {CharacterLegs} from './CharacterLegs';
import {CharacterTorso} from './CharacterTorso';

type Props = {identity: CharacterIdentity; id: string; x: number; groundY: number; scale: number; expression: string; pose?: string; actions: Action[]; frame: number; mouthOpen?: number};

export const CharacterRig: React.FC<Props> = ({identity,id,x,groundY,scale,expression,pose='standing',actions,frame,mouthOpen=0}) => {
  const animation = animateCharacter(actions, id, frame, mouthOpen);
  return <svg viewBox="0 0 220 330" width="220" height="330" aria-label={`${id} ${expression}`} style={{position:'absolute',left:`${x}%`,top:`${groundY}%`,overflow:'visible',transform:`translate(-50%,-100%) translate(${animation.shake}px,${animation.bob}px) rotate(${animation.rotate}deg) scale(${scale})`,transformOrigin:'50% 100%'}}>
    <CharacterLegs identity={identity} pose={pose} legLength={identity.body_proportions.leg_length || 1} />
    <CharacterTorso identity={identity} breathing={animation.breathing} torsoScale={identity.body_proportions.torso_scale || 1} />
    <CharacterArms identity={identity} action={animation.actionType} armLength={identity.body_proportions.arm_length || 1} />
    <CharacterHead identity={identity} expression={expression} blink={animation.blink} mouthOpen={animation.mouthOpen} lookX={animation.lookX} headTilt={animation.headTilt} frame={frame} headScale={identity.body_proportions.head_scale || 1} />
  </svg>;
};
