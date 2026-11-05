import type {Project} from './schemas/project';

export type LayoutPoint = {x: number; y: number};
export type LayoutBox = {x: number; y: number; width: number; height: number};

export type SceneLayout = {
  title: LayoutPoint;
  focalPoint: LayoutPoint;
  character: Record<string, {x: number; groundY: number; scale: number; visible: boolean}>;
  objects: Record<string, {x: number; y: number; scale: number}>;
  diagramScale: number;
  subtitleSafeZone: LayoutBox;
};

type Scene = Project['scenes'][number];

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const overlaps = (a: LayoutBox, b: LayoutBox) => a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y;

/** Deterministic, orientation-aware placement rules for legacy and new plans. */
export function computeSceneLayout(scene: Scene, portrait: boolean): SceneLayout {
  const noCharacter = scene.character_mode === 'none' || scene.layout_template === 'full_screen_diagram';
  const layout: SceneLayout = {
    title: {x: portrait ? 50 : scene.text_elements[0]?.position.x ?? 50, y: portrait ? 9 : scene.text_elements[0]?.position.y ?? 12},
    focalPoint: {x: scene.focal_point?.x ?? 50, y: scene.focal_point?.y ?? 50},
    character: {},
    objects: {},
    diagramScale: portrait ? 0.84 : 1,
    subtitleSafeZone: portrait ? {x: 5, y: 78, width: 90, height: 17} : {x: 5, y: 84, width: 90, height: 11},
  };

  for (const character of scene.characters) {
    if (noCharacter || !character.visible || character.mode === 'none') continue;
    const baseX = character.position.x;
    const baseGround = character.anchor === 'feet' ? character.ground_y : character.position.y;
    layout.character[character.id] = portrait
      ? {x: scene.layout_template === 'reaction_closeup' ? 50 : clamp(baseX, 28, 72), groundY: scene.layout_template === 'reaction_closeup' ? 77 : clamp(baseGround, 67, 78), scale: scene.layout_template === 'reaction_closeup' ? Math.min(character.scale * 1.22, 1.35) : Math.min(character.scale * 0.92, 1.12), visible: true}
      : {x: clamp(baseX, 16, 34), groundY: clamp(baseGround, 68, 86), scale: Math.min(character.scale, 1.12), visible: true};
  }

  for (const object of scene.visual_objects) {
    let x = object.position.x;
    let y = object.position.y;
    let scale = 1;
    if (scene.scene_type === 'developer_search' && object.kind === 'computer_monitor') { x = portrait ? 50 : 70; y = portrait ? 45 : 48; scale = portrait ? 0.82 : 1; }
    else if (scene.scene_type === 'full_scan' && object.kind === 'database_table') { x = portrait ? 50 : 61; y = portrait ? 47 : 57; scale = portrait ? 0.82 : 1; }
    else if ((scene.scene_type === 'index_intro' || scene.scene_type === 'indexed_search') && object.kind === 'btree') { x = portrait ? 50 : 60; y = portrait ? 45 : 54; scale = portrait ? 0.9 : 1; }
    else if (scene.scene_type === 'comparison' && object.kind === 'comparison_panel') { x = 50; y = portrait ? 48 : 58; scale = portrait ? 0.82 : 1; }
    else if (scene.scene_type === 'ending' && object.kind === 'database_cylinder') { x = portrait ? 50 : 67; y = portrait ? 47 : 55; scale = portrait ? 0.78 : 1; }
    layout.objects[object.id] = {x, y, scale};
  }

  // Collision priority: subtitle safe zone > face > primary diagram > body.
  // The solver makes only small deterministic adjustments, then removes a
  // character if preserving readability is impossible.
  const primary = scene.visual_objects[0];
  if (primary && !noCharacter) {
    const primaryPlacement = layout.objects[primary.id];
    const primaryBox: LayoutBox = {x: primaryPlacement?.x ?? 50, y: primaryPlacement?.y ?? 50, width: portrait ? 58 : 38, height: portrait ? 28 : 30};
    for (const character of scene.characters) {
      const placement = layout.character[character.id];
      if (!placement || !placement.visible) continue;
      const faceBox: LayoutBox = {x: placement.x - 11 * placement.scale, y: placement.groundY - 31 * placement.scale, width: 22 * placement.scale, height: 18 * placement.scale};
      const bodyBox: LayoutBox = {x: placement.x - 15 * placement.scale, y: placement.groundY - 27 * placement.scale, width: 30 * placement.scale, height: 27 * placement.scale};
      if (overlaps(faceBox, layout.subtitleSafeZone)) placement.groundY = portrait ? 74 : 80;
      if (overlaps(faceBox, primaryBox) || overlaps(bodyBox, primaryBox)) {
        const alternateX = placement.x < 50 ? 23 : 77;
        const alternateFace: LayoutBox = {x: alternateX - 11 * placement.scale, y: placement.groundY - 31 * placement.scale, width: 22 * placement.scale, height: 18 * placement.scale};
        if (overlaps(alternateFace, primaryBox)) placement.visible = false;
        else placement.x = alternateX;
      }
    }
  }
  const titleBox: LayoutBox = {x: 8, y: 3, width: 84, height: portrait ? 12 : 14};
  for (const object of scene.visual_objects) {
    const placement = layout.objects[object.id];
    if (!placement) continue;
    const objectBox: LayoutBox = {x: placement.x - (portrait ? 28 : 20), y: placement.y - (portrait ? 14 : 12), width: portrait ? 56 : 40, height: portrait ? 28 : 24};
    if (overlaps(objectBox, titleBox)) placement.y = portrait ? 34 : 36;
  }
  return layout;
}
