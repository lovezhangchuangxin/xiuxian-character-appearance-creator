const assetFiles = import.meta.glob<string>(
  ["../../../../assets/sprites/**/*.png", "../../../../assets/thumbnails/outfits/**/*.webp"],
  { eager: true, import: "default", query: "?url&no-inline" },
);

export function spriteUrl(path: string) {
  return assetFiles[`../../../../assets/${path}`];
}
