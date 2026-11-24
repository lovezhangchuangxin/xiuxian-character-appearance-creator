import faceOffsets from "./numbered-faces.json" with { type: "json" };
import hairPlacements from "./numbered-hair.json" with { type: "json" };

export type Body = "female" | "male";
export type Slot =
  | "shape"
  | "brows"
  | "eyes"
  | "nose"
  | "mouth"
  | "frontHair"
  | "backHair"
  | "topHair"
  | "outfit";
type SpritePath<B extends Body> = `${"bodies" | "faces" | "hair" | "outfits"}/${B}/${string}.png`;
export type Part<B extends Body = Body> = {
  id: string;
  label: string;
  sprite?: SpritePath<B>;
  width?: number;
  height?: number;
  dx?: number;
  dy?: number;
  headOffset?: [x: number, y: number];
  dyeable?: boolean;
};
export type Appearance = { body: Body; parts: Record<Slot, string>; dye: string | null };

export const canvas = { width: 1024, height: 1536 };
export const headReference = { width: 512, height: 620, shapeHeight: 840, scale: 1 / 3 };
type BodyProfile<B extends Body> = {
  label: string;
  sprite: SpritePath<B>;
  center: number;
  crown: number;
  headOrigin: [x: number, y: number];
  neck: number;
  ground: number;
};
export const bodies: { [B in Body]: BodyProfile<B> } = {
  female: {
    label: "女",
    sprite: "bodies/female/white.png",
    center: 512,
    crown: 155,
    headOrigin: [1280 / 3, 425 / 3],
    neck: 324,
    ground: 1485,
  },
  male: {
    label: "男",
    sprite: "bodies/male/white.png",
    center: 511,
    crown: 45,
    headOrigin: [1280 / 3, 95 / 3],
    neck: 218,
    ground: 1485,
  },
};
export const slots: { id: Slot; label: string }[] = [
  { id: "shape", label: "脸型" },
  { id: "brows", label: "眉毛" },
  { id: "eyes", label: "眼睛" },
  { id: "nose", label: "鼻子" },
  { id: "mouth", label: "嘴巴" },
  { id: "frontHair", label: "前发" },
  { id: "backHair", label: "后发" },
  { id: "topHair", label: "发髻" },
  { id: "outfit", label: "服装" },
];
const none = { id: "none", label: "无" };
const underclothes = { id: "none", label: "内搭" };

type NumberedFace = keyof (typeof faceOffsets)["female"];

function numberedParts<B extends Body>(make: (id: string, index: number) => Part<B>): Part<B>[] {
  return Array.from({ length: 16 }, (_, index) => make(String(index + 1).padStart(2, "0"), index));
}

function shapes<B extends Body>(body: B): Part<B>[] {
  return numberedParts((id) => ({
    id,
    label: id,
    sprite: `faces/${body}/shapes/${id}.png`,
    headOffset: [0, 0],
  }));
}

function numberedFace<B extends Body>(body: B, part: NumberedFace): Part<B>[] {
  return faceOffsets[body][part].map(([x, y], index) => {
    const id = String(index + 1).padStart(2, "0");
    return { id, label: id, sprite: `faces/${body}/${part}/${id}.png`, headOffset: [x, y] };
  });
}

type HairPart = keyof (typeof hairPlacements)["female"];

function numberedHair<B extends Body>(body: B, part: HairPart): Part<B>[] {
  const pieces = numberedParts<B>((id, index) => {
    const [width, height, dx, dy] = hairPlacements[body][part][index];
    return { id, label: id, sprite: `hair/${body}/${part}/${id}.png`, width, height, dx, dy };
  });
  return [...pieces, none];
}

function numberedOutfits<B extends Body>(body: B): Part<B>[] {
  const dyeable = body === "female" ? ["01", "06", "11", "14"] : ["02", "06", "08", "16"];
  const outfits = numberedParts<B>((id) => ({
    id,
    label: id,
    sprite: `outfits/${body}/${id}.png`,
    dyeable: dyeable.includes(id),
  }));
  return [...outfits, underclothes];
}

const catalog: { [B in Body]: Record<Slot, Part<B>[]> } = {
  female: {
    shape: shapes("female"),
    brows: numberedFace("female", "brows"),
    eyes: numberedFace("female", "eyes"),
    nose: numberedFace("female", "noses"),
    mouth: numberedFace("female", "mouths"),
    frontHair: numberedHair("female", "front"),
    backHair: numberedHair("female", "back"),
    topHair: numberedHair("female", "top"),
    outfit: numberedOutfits("female"),
  },
  male: {
    shape: shapes("male"),
    brows: numberedFace("male", "brows"),
    eyes: numberedFace("male", "eyes"),
    nose: numberedFace("male", "noses"),
    mouth: numberedFace("male", "mouths"),
    frontHair: numberedHair("male", "front"),
    backHair: numberedHair("male", "back"),
    topHair: numberedHair("male", "top"),
    outfit: numberedOutfits("male"),
  },
};

export const groups: { id: string; label: string; slots: Slot[]; view: "portrait" | "full" }[] = [
  {
    id: "face",
    label: "五官",
    slots: ["shape", "brows", "eyes", "nose", "mouth"],
    view: "portrait",
  },
  { id: "hair", label: "发型", slots: ["frontHair", "backHair", "topHair"], view: "portrait" },
  { id: "outfit", label: "服装", slots: ["outfit"], view: "full" },
];

export const dyeColors = [
  { label: "原色", value: null, swatch: "#7d9294" },
  { label: "雾紫", value: "#a483b3", swatch: "#a483b3" },
  { label: "丹枫", value: "#b16a62", swatch: "#b16a62" },
  { label: "松黛", value: "#6c957f", swatch: "#6c957f" },
];

export function options(slot: Slot, body: Body) {
  return catalog[body][slot];
}

export function selectedPart(appearance: Appearance, slot: Slot) {
  const compatible = options(slot, appearance.body);
  return compatible.find((part) => part.id === appearance.parts[slot]) ?? compatible[0];
}

export function makeAppearance(body: Body, style: "calm" | "wandering" = "calm"): Appearance {
  const wandering = style === "wandering";
  const styleIds = {
    shape: wandering ? "09" : "01",
    mouth: wandering ? "05" : "01",
    frontHair: wandering ? "05" : "01",
    backHair: wandering ? "09" : "01",
  };
  const parts =
    body === "female"
      ? {
          ...styleIds,
          brows: wandering ? "09" : "01",
          eyes: wandering ? "10" : "01",
          nose: wandering ? "05" : "01",
          topHair: wandering ? "05" : "none",
          outfit: wandering ? "09" : "01",
        }
      : {
          ...styleIds,
          brows: wandering ? "05" : "01",
          eyes: wandering ? "10" : "06",
          nose: wandering ? "09" : "01",
          topHair: wandering ? "07" : "01",
          outfit: wandering ? "12" : "01",
        };
  return { body, parts, dye: null };
}
