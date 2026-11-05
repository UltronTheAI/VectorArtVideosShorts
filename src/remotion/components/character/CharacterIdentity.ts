import type {Project} from '../../schemas/project';

export type CharacterIdentity = Project['character_identities'][number];

export const defaultCharacterIdentity: CharacterIdentity = {
  id: 'developer', skin_color: '#FFD6A5', hair_color: '#3A2E39', hair_style: 'short',
  shirt_color: '#4CC9F0', pants_color: '#263A63', shoe_color: '#172033',
  body_proportions: {head_scale: 1, torso_scale: 1, arm_length: 1, leg_length: 1},
};
