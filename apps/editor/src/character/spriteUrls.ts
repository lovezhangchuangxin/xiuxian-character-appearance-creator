const assetFiles = import.meta.glob<string>(
  ["../../../../assets/sprites/**/*.png", "../../../../assets/thumbnails/**/*.webp"],
  { eager: true, import: "default", query: "?url&no-inline" },
);

export function spriteUrl(path: string) {
  return assetFiles[`../../../../assets/${path}`];
}

export function shapeThumbnailUrl(image: string) {
  return spriteUrl(image.replace(/^sprites\//, "thumbnails/").replace(/\.png$/, ".webp"));
}
