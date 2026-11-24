import { dyeColors, options, type Appearance, type Slot } from "./catalog";

// Version 1 keeps this field order even if the editor reorganizes its controls.
const codeSlots = [
  "shape",
  "brows",
  "eyes",
  "nose",
  "mouth",
  "frontHair",
  "backHair",
  "topHair",
  "outfit",
] as const satisfies readonly Slot[];
const pattern = /^XX1-([FM])((?:-[0-9]{2}){9})-(0|[0-9a-f]{6})$/i;
export const savedAppearanceKey = "xiuxian.appearance.v1";

export function encodeAppearance(appearance: Appearance) {
  const body = appearance.body === "female" ? "F" : "M";
  const parts = codeSlots.map((slot) =>
    appearance.parts[slot] === "none" ? "00" : appearance.parts[slot],
  );
  return ["XX1", body, ...parts, appearance.dye?.slice(1) ?? "0"].join("-");
}

export function decodeAppearance(input: string): Appearance | null {
  const match = pattern.exec(input.trim());
  if (!match) return null;

  const [, bodyCode, partCodes, dyeCode] = match;
  const body = bodyCode.toUpperCase() === "F" ? "female" : "male";
  const ids = partCodes.slice(1).split("-");
  const entries = codeSlots.map(
    (slot, index) => [slot, ids[index] === "00" ? "none" : ids[index]] as const,
  );
  for (const [slot, id] of entries) {
    if (!options(slot, body).some((part) => part.id === id)) return null;
  }

  const parts = Object.fromEntries(entries) as Appearance["parts"];
  const dye = dyeCode === "0" ? null : `#${dyeCode.toLowerCase()}`;
  const outfit = options("outfit", body).find((part) => part.id === parts.outfit);
  if (dye !== null && (!outfit?.dyeable || !dyeColors.some((color) => color.value === dye)))
    return null;
  return { body, parts, dye };
}
