const files = import.meta.glob<string>('../../assets/sprites/**/*.png', {
  eager: true,
  import: 'default',
  query: '?url&no-inline',
})

export function spriteUrl(path: string) {
  return files[`../../assets/sprites/${path}`]
}

const outfitPreviews = import.meta.glob<string>('../../assets/thumbnails/outfits/**/*.webp', {
  eager: true,
  import: 'default',
  query: '?url&no-inline',
})

export function partPreviewUrl(path: string) {
  if (path.startsWith('outfits/')) {
    return outfitPreviews[`../../assets/thumbnails/${path.replace(/\.png$/, '.webp')}`]
  }
  return spriteUrl(path)
}
