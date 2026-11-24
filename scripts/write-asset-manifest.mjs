import { mkdirSync, renameSync, writeFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import Ajv2020 from "ajv/dist/2020.js";
import schema from "../packages/character-assets/manifest.schema.json" with { type: "json" };
import metadata from "../packages/character-assets/package.json" with { type: "json" };

const output = new URL("../packages/character-assets/dist/", import.meta.url);
const layers = [
  "backHair",
  "shape",
  "outfit",
  "topHair",
  "brows",
  "eyes",
  "nose",
  "mouth",
  "frontHair",
];

export function writeManifest({
  bodies,
  canvas,
  headReference,
  makeAppearance,
  options,
  slots,
  sizes,
}) {
  function partEntry(part, slot, profile) {
    const { id, label, sprite } = part;
    const image = sprite ?? (slot === "outfit" ? profile.sprite : null);
    if (!image) return { id, label, image: null };

    const size = sizes.get(image);
    let rect = { x: 0, y: 0, width: size.width, height: size.height };
    if (part.headOffset) {
      const [x, y] = part.headOffset;
      const { scale } = headReference;
      rect = {
        x: profile.headOrigin[0] + x * scale,
        y: profile.headOrigin[1] + y * scale,
        width: size.width * scale,
        height: size.height * scale,
      };
    } else if (slot !== "outfit") {
      const width = part.width ?? size.width;
      const height = part.height ?? size.height;
      rect = {
        x: profile.center + (part.dx ?? 0) - width / 2,
        y: profile.crown + (part.dy ?? 0),
        width,
        height,
      };
    }

    const entry = { id, label, image: `sprites/${image}`, rect };
    if (slot === "outfit" && sprite) {
      entry.thumbnail = `thumbnails/${sprite.replace(/\.png$/, ".webp")}`;
      if (part.dyeable) entry.dyeable = true;
    }
    if (!sprite) {
      entry.clip = {
        x: 0,
        y: profile.neck,
        width: canvas.width,
        height: canvas.height - profile.neck,
      };
    }
    return entry;
  }

  const manifest = {
    schemaVersion: 2,
    packId: "xiuxian-character-assets",
    packVersion: metadata.version,
    canvas,
    slots,
    layers,
    bodies: Object.fromEntries(
      Object.entries(bodies).map(([body, profile]) => {
        const parts = Object.fromEntries(
          slots.map(({ id }) => [
            id,
            options(id, body).map((part) => partEntry(part, id, profile)),
          ]),
        );
        const crowns = options("frontHair", body).map((part, index) => {
          const { rect } = parts.frontHair[index];
          // Overlap the root with the visible cap or bare scalp.
          return rect ? rect.y + rect.height * part.hairAnchor + 12 : profile.crown + 9;
        });
        const referenceCrown = crowns[0];
        options("topHair", body).forEach((part, index) => {
          const { rect } = parts.topHair[index];
          if (rect) rect.y = Math.round(referenceCrown - rect.height * part.hairAnchor);
        });
        const topHairOffsets = Object.fromEntries(
          parts.frontHair.map(({ id }, index) => [id, Math.round(crowns[index] - referenceCrown)]),
        );
        return [
          body,
          {
            label: profile.label,
            views: {
              full: { x: profile.center, y: profile.ground - 753, width: 720, height: 1595 },
              portrait: { x: profile.center, y: profile.crown + 101, width: 350, height: 365 },
            },
            presets: {
              calm: makeAppearance(body, "calm").parts,
              wandering: makeAppearance(body, "wandering").parts,
            },
            parts,
            topHairOffsets,
          },
        ];
      }),
    ),
  };

  const validator = new Ajv2020({ allErrors: true });
  if (!validator.validate(schema, manifest)) {
    throw new Error(validator.errorsText(validator.errors));
  }

  mkdirSync(output, { recursive: true });
  const temporary = new URL(`${randomUUID()}.json`, output);
  writeFileSync(temporary, JSON.stringify(manifest, null, 2) + "\n");
  renameSync(temporary, new URL("manifest.json", output));
}
