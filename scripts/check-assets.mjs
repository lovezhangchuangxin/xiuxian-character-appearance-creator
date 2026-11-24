import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { sep } from "node:path";
import { crc32, inflateSync } from "node:zlib";
import ts from "typescript";
import { writeManifest } from "./write-asset-manifest.mjs";

const spriteRoot = new URL("../assets/sprites/", import.meta.url);
const thumbnailRoot = new URL("../assets/thumbnails/", import.meta.url);
const catalogUrl = new URL("../packages/character-assets/source/catalog.ts", import.meta.url);
const { outputText } = ts.transpileModule(readFileSync(catalogUrl, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
const linkedOutput = outputText.replace(
  /\.\/numbered-(?:faces|hair)\.json/g,
  (path) => new URL(path, catalogUrl).href,
);
const moduleUrl = "data:text/javascript;base64," + Buffer.from(linkedOutput).toString("base64");
const { bodies, canvas, headReference, makeAppearance, options, slots } = await import(moduleUrl);

const errors = [];
const registrations = new Map();
const facePlacements = [];
const numbered = Array.from({ length: 16 }, (_, index) => String(index + 1).padStart(2, "0"));
for (const [body, profile] of Object.entries(bodies)) {
  register(profile.sprite, body, "bodies");
  const presets = ["calm", "wandering"].map((style) => makeAppearance(body, style));
  for (const { id: slot } of slots) {
    const parts = options(slot, body);
    const ids = new Set(parts.map((part) => part.id));
    if (ids.size !== parts.length) errors.push(`${body}/${slot} has duplicate part IDs`);
    for (const { parts: choices } of presets) {
      if (!ids.has(choices[slot]))
        errors.push(`${body}/${slot} preset references "${choices[slot]}"`);
    }
    const isFaceSlot = ["shape", "brows", "eyes", "nose", "mouth"].includes(slot);
    const numberedSprites = parts.filter((part) => part.id !== "none");
    if (
      numberedSprites.length !== numbered.length ||
      numberedSprites.some(
        (part, index) =>
          part.id !== numbered[index] ||
          part.label !== numbered[index] ||
          !part.sprite?.endsWith(`/${numbered[index]}.png`),
      )
    ) {
      errors.push(`${body}/${slot} must expose numbered sprites 01–16 in sheet order`);
    }
    for (const part of parts) {
      if (!part.sprite) continue;
      register(part.sprite, body);
      if (slot === "outfit" || slot === "shape") {
        const path = part.sprite.replace(/\.png$/, ".webp");
        const url = new URL(path, thumbnailRoot);
        if (!existsSync(url)) {
          errors.push(`Missing thumbnail: thumbnails/${path}`);
        } else if (!hasWebpContainer(readFileSync(url))) {
          errors.push(`Invalid or incomplete WebP: thumbnails/${path}`);
        }
      }
      if (isFaceSlot && !part.headOffset) {
        errors.push(`Missing reference coordinates: ${part.sprite}`);
      }
      if (part.headOffset) {
        if (
          !isFaceSlot ||
          [part.width, part.height, part.dx, part.dy].some((value) => value !== undefined)
        ) {
          errors.push(`Head placement conflicts with other layout fields: ${part.sprite}`);
        }
        facePlacements.push({ path: part.sprite, offset: part.headOffset, slot });
      }
    }
  }
}

function register(path, body, requiredCategory) {
  const [category, owner, ...file] = path.split("/");
  if (
    owner !== body ||
    (requiredCategory && category !== requiredCategory) ||
    !["bodies", "faces", "hair", "outfits"].includes(category) ||
    file.length === 0 ||
    !file.every((segment) => /^[a-z0-9][a-z0-9-]*(\.png)?$/.test(segment)) ||
    !path.endsWith(".png")
  ) {
    errors.push(`Invalid ${body} sprite path: ${path}`);
    return;
  }
  registrations.set(path, { body, category });
}

function hasWebpContainer(buffer) {
  return (
    buffer.length >= 20 &&
    buffer.toString("ascii", 0, 4) === "RIFF" &&
    buffer.toString("ascii", 8, 12) === "WEBP" &&
    buffer.readUInt32LE(4) === buffer.length - 8
  );
}

function pngInfo(buffer) {
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  if (
    buffer.length < 33 ||
    !buffer.subarray(0, 8).equals(signature) ||
    buffer.readUInt32BE(8) !== 13 ||
    buffer.toString("ascii", 12, 16) !== "IHDR"
  )
    return null;

  const width = buffer.readUInt32BE(16);
  const height = buffer.readUInt32BE(20);
  const [depth, color, compression, filter, interlace] = buffer.subarray(24, 29);
  const formats = {
    0: [1, [1, 2, 4, 8, 16]],
    2: [3, [8, 16]],
    3: [1, [1, 2, 4, 8]],
    4: [2, [8, 16]],
    6: [4, [8, 16]],
  };
  const format = formats[color];
  if (!width || !height || !format?.[1].includes(depth) || compression || filter || interlace > 1)
    return null;
  const [channels] = format;

  let hasAlpha = color === 4 || color === 6;
  let palette = 0;
  let previous = "";
  let ended = false;
  const imageData = [];
  for (let offset = 8; offset + 12 <= buffer.length;) {
    const size = buffer.readUInt32BE(offset);
    const type = buffer.toString("ascii", offset + 4, offset + 8);
    const crcOffset = offset + 8 + size;
    if (
      crcOffset + 4 > buffer.length ||
      crc32(buffer.subarray(offset + 4, crcOffset)) !== buffer.readUInt32BE(crcOffset)
    )
      return null;
    if (type === "IHDR" && offset !== 8) return null;
    if (type === "PLTE") {
      if (
        imageData.length ||
        palette ||
        color === 0 ||
        color === 4 ||
        !size ||
        size % 3 ||
        size > 768
      )
        return null;
      palette = size / 3;
      if (color === 3 && palette > 2 ** depth) return null;
    }
    if (type === "tRNS") {
      const validSize =
        (color === 0 && size === 2) ||
        (color === 2 && size === 6) ||
        (color === 3 && size > 0 && size <= palette);
      if (imageData.length || hasAlpha || !validSize) return null;
      hasAlpha = true;
    }
    if (type === "IDAT") {
      if ((color === 3 && !palette) || (imageData.length && previous !== "IDAT")) return null;
      imageData.push(buffer.subarray(offset + 8, crcOffset));
    }
    if (type === "IEND") {
      ended = size === 0 && crcOffset + 4 === buffer.length;
      break;
    }
    previous = type;
    offset = crcOffset + 4;
  }
  if (!ended || !imageData.length) return null;

  // Each scanline starts with a filter byte. Adam7 images store seven smaller passes.
  const passes = interlace
    ? [
        [0, 0, 8, 8],
        [4, 0, 8, 8],
        [0, 4, 4, 8],
        [2, 0, 4, 4],
        [0, 2, 2, 4],
        [1, 0, 2, 2],
        [0, 1, 1, 2],
      ]
    : [[0, 0, 1, 1]];
  const scanlines = [];
  for (const [x, y, dx, dy] of passes) {
    if (x >= width || y >= height) continue;
    const stride = 1 + Math.ceil((Math.ceil((width - x) / dx) * channels * depth) / 8);
    scanlines.push([stride, Math.ceil((height - y) / dy)]);
  }
  const size = scanlines.reduce((total, [stride, rows]) => total + stride * rows, 0);
  try {
    const compressed = Buffer.concat(imageData);
    const { buffer: pixels, engine } = inflateSync(compressed, {
      maxOutputLength: size,
      info: true,
    });
    if (pixels.length !== size || engine.bytesWritten !== compressed.length) return null;
    let offset = 0;
    for (const [stride, rows] of scanlines) {
      for (let row = 0; row < rows; row++, offset += stride) {
        if (pixels[offset] > 4) return null;
      }
    }
  } catch {
    return null;
  }
  return { width, height, hasAlpha };
}

const contentByHash = new Map();
const sizes = new Map();
for (const [path, { category }] of registrations) {
  const url = new URL(path, spriteRoot);
  if (!existsSync(url)) {
    errors.push(`Missing sprite: ${path}`);
    continue;
  }
  const content = readFileSync(url);
  const info = pngInfo(content);
  if (!info) {
    errors.push(`Invalid or incomplete PNG: ${path}`);
  } else if (!info.hasAlpha) {
    errors.push(`Expected a PNG with an alpha channel: ${path}`);
  } else if (
    ["bodies", "outfits"].includes(category) &&
    (info.width !== canvas.width || info.height !== canvas.height)
  ) {
    errors.push(`Expected ${canvas.width} × ${canvas.height} canvas: ${path}`);
  }
  if (info) sizes.set(path, info);
  const hash = createHash("sha256").update(content).digest("hex");
  const existing = contentByHash.get(hash);
  if (existing) errors.push(`Duplicate runtime sprite: ${existing} and ${path}`);
  contentByHash.set(hash, path);
}

for (const {
  path,
  offset: [x, y],
  slot,
} of facePlacements) {
  const size = sizes.get(path);
  if (!size) continue;
  if (
    slot === "shape" &&
    (x !== 0 ||
      y !== 0 ||
      size.width !== headReference.width ||
      size.height !== headReference.shapeHeight)
  ) {
    errors.push(`Expected the full continuous head and neck canvas: ${path}`);
    continue;
  }
  if (
    ![x, y].every(Number.isInteger) ||
    x < 0 ||
    y < 0 ||
    x + size.width > headReference.width ||
    y + size.height > (slot === "shape" ? headReference.shapeHeight : headReference.height)
  ) {
    errors.push(`Head crop runs outside the reference canvas: ${path}`);
  }
}

for (const file of readdirSync(spriteRoot, { recursive: true })) {
  const path = file.split(sep).join("/");
  if (path.endsWith(".png") && !registrations.has(path))
    errors.push(`Unregistered sprite: ${path}`);
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exitCode = 1;
} else {
  writeManifest({ bodies, canvas, headReference, makeAppearance, options, slots, sizes });
  console.log(`Checked ${registrations.size} runtime sprites and both presets for each body type.`);
}
