import manifest from "@xiuxian/character-assets/manifest.json";

export type Body = keyof typeof manifest.bodies;
export type Slot = keyof (typeof manifest.bodies)["female"]["parts"];
export type Appearance = { body: Body; parts: Record<Slot, string>; dye: string | null };
type Rect = { x: number; y: number; width: number; height: number };
export type Part = {
  id: string;
  label: string;
  image: string | null;
  rect?: Rect;
  clip?: Rect;
  thumbnail?: string;
  dyeable?: boolean;
};

export const bodies = manifest.bodies;
export const slots = manifest.slots as { id: Slot; label: string }[];
export const layers = manifest.layers as Slot[];

export function options(slot: Slot, body: Body): Part[] {
  return bodies[body].parts[slot];
}

export function selectedPart(appearance: Appearance, slot: Slot) {
  const compatible = options(slot, appearance.body);
  return compatible.find((part) => part.id === appearance.parts[slot]) ?? compatible[0];
}

export function makeAppearance(body: Body, style: "calm" | "wandering" = "calm"): Appearance {
  return { body, parts: { ...bodies[body].presets[style] }, dye: null };
}

export const groups: { id: string; label: string; slots: Slot[] }[] = [
  { id: "face", label: "五官", slots: ["shape", "brows", "eyes", "nose", "mouth"] },
  { id: "hair", label: "发型", slots: ["frontHair", "backHair", "topHair"] },
  { id: "outfit", label: "服装", slots: ["outfit"] },
];

export const dyeColors = [
  { label: "原色", value: null, swatch: "#7d9294" },
  { label: "雾紫", value: "#a483b3", swatch: "#a483b3" },
  { label: "丹枫", value: "#b16a62", swatch: "#b16a62" },
  { label: "松黛", value: "#6c957f", swatch: "#6c957f" },
];
