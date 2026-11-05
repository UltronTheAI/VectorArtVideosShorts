import {interpolate} from 'remotion';
import type {Action} from '../../schemas/project';

export function actionFor(actions: Action[], target: string, frame: number): Action | undefined {
  return actions.find((action) => action.target === target && frame >= action.start_frame && frame <= action.start_frame + action.duration_frames);
}

export function animateCharacter(actions: Action[], target: string, frame: number, mouthOpen: number) {
  const action = actionFor(actions, target, frame);
  const progress = action ? interpolate(frame, [action.start_frame, action.start_frame + action.duration_frames], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 0;
  const actionType = action?.type;
  const blink = (frame % 173 >= 0 && frame % 173 <= 5) || (frame % 227 >= 0 && frame % 227 <= 4);
  const breathing = Math.sin(frame / 38) * 2;
  const bob = actionType === 'bounce' || actionType === 'walk' || actionType === 'jump' || actionType === 'celebrate' ? Math.sin(progress * Math.PI * 4) * 7 : breathing;
  const shake = actionType === 'shake' || actionType === 'frustrated' ? Math.sin(progress * Math.PI * 10) * 4 : 0;
  const rotate = actionType === 'celebrate' ? Math.sin(progress * Math.PI * 2) * 5 : actionType === 'nod' ? Math.sin(progress * Math.PI * 2) * 3 : actionType === 'walk' ? Math.sin(progress * Math.PI * 2) * 2 : 0;
  const lookX = actionType === 'point' || actionType === 'look' ? 7 : actionType === 'frustrated' ? -4 : actionType === 'think' ? -6 : 0;
  const headTilt = actionType === 'frustrated' ? -5 : actionType === 'surprised' ? 4 : actionType === 'think' ? -3 : 0;
  const speaking = mouthOpen > 0.04;
  return {actionType, blink, breathing, bob, shake, rotate, lookX, headTilt, mouthOpen: speaking ? mouthOpen : 0, progress};
}
