"""Register AI-generated jaw and cheek variations to the unchanged head anchors."""

import argparse
import json
from pathlib import Path

import numpy as np
from eye_sheet import CELL_SIZE, align_tile, clean_alpha
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
NECK_CROP = {"male": 559, "female": 547}
SHAPE_HEIGHT = 840


def ramp(values, low, high):
    t = np.clip((values - low) / (high - low), 0, 1)
    return t * t * (3 - 2 * t)


def scale_to_base(original, aligned):
    sample = np.s_[407:426, 196:316, :3]
    base = np.array(original, dtype=np.float32)
    generated = np.array(aligned, dtype=np.float32)
    shift = np.median(base[sample] - generated[sample], axis=(0, 1))
    generated[:, :, :3] = np.clip(generated[:, :, :3] + shift, 0, 255)
    return Image.fromarray(generated.round().astype(np.uint8))


def jaw_row(image, neck):
    # Find the center jaw outline, below the mouth and above the source lapels.
    top = neck - 46
    sample = np.asarray(image)[top : neck + 27, 233:279, :3]
    luma = np.median(sample, axis=1) @ [0.2126, 0.7152, 0.0722]
    return top + int(np.argmin(luma))


def register(original, edited, neck):
    aligned, matrix = align_tile(original, edited, ((18, 390, 495, 566),))
    aligned = clean_alpha(scale_to_base(original, aligned))
    w, h = CELL_SIZE
    y, x = np.ogrid[:h, :w]
    # Keep the ears, forehead and outfit seam on the original head.
    left = ramp(x, 75, 105)
    right = 1 - ramp(x, 402, 442)
    cheek = ramp(y, 383, 436)
    # Blend below both outlines, so the old chin does not ghost through the new one.
    jaw = jaw_row(aligned, neck)
    transition = max(jaw, jaw_row(original, neck)) + 5
    chin = 1 - ramp(y, neck - 19, neck - 2)
    # Preserve the master neck sides while keeping the aligned chin through the center.
    neck_edge = original.getchannel("A").crop((0, neck + 19, w, neck + 20)).getbbox()
    neck_left, _, neck_right, _ = neck_edge
    inside_neck = ramp(x, neck_left + 4, neck_left + 20) * (
        1 - ramp(x, neck_right - 20, neck_right - 4)
    )
    aligned_chin = 1 - ramp(y, transition, transition + 9)
    chin = chin + inside_neck * np.maximum(0, aligned_chin - chin)
    mix = Image.fromarray((left * right * cheek * chin * 255).round().astype(np.uint8))

    # Blend in premultiplied space near the new silhouette to avoid dark fringes.
    shaped = Image.composite(aligned.convert("RGBa"), original.convert("RGBa"), mix)

    # The contour must resolve quickly to avoid doubling the jaw line. Keep its
    # shadow longer in the opaque neck interior without moving the silhouette.
    shade = inside_neck * (
        ramp(y, transition, transition + 9) - ramp(y, transition, transition + 28)
    )
    base_pixels = np.asarray(original, dtype=np.int16)
    aligned_pixels = np.asarray(aligned, dtype=np.int16)
    opaque_neck = (base_pixels[..., 3] >= 248) & (aligned_pixels[..., 3] >= 248)
    color_delta = aligned_pixels[..., :3] - base_pixels[..., :3]
    pixels = np.array(shaped.convert("RGBA"))
    pixels[..., :3] = np.clip(
        np.rint(pixels[..., :3] + (shade * opaque_neck)[..., None] * color_delta),
        0,
        255,
    ).astype(np.uint8)
    shaped = clean_alpha(Image.fromarray(pixels))
    join = max(neck + 20, transition + 10)
    return shaped, matrix, join, jaw


def extend_neck(shape, neck, join, jaw):
    width = shape.width
    # Use a row below the jaw shadow and above the original undergarment.
    source = shape.crop((0, join - 1, width, join))
    left, _, right, _ = source.getchannel("A").getbbox()
    radius = (right - left) / 2
    center = (left + right) / 2
    # Sample bare skin between the original undergarment's lapels.
    middle = round(center)
    chest = np.asarray(shape.crop((middle - 10, 600, middle + 10, 616)))
    chest_light = np.median(chest[..., :3], axis=(0, 1))
    # Feather the painted highlights before continuing them beyond the original neck.
    start = max(neck - 8, jaw + 4)
    patch = np.array(shape.crop((0, start, width, join)))
    alpha = patch[..., 3].astype(np.float32) / 255
    coverage = gaussian_filter(alpha, (4, 13))
    rgb = patch[..., :3].astype(np.float32)
    blurred = gaussian_filter(rgb * alpha[..., None], (4, 13, 0))
    blurred /= np.maximum(coverage[..., None], 0.001)
    edge = np.abs(np.arange(width) - center) / radius
    weight = (
        ramp(np.arange(join - start), 0, 18)[:, None] * (1 - ramp(edge, 0.75, 0.94))
    )[..., None]
    patch[..., :3] = (rgb * (1 - weight) + blurred * weight).round().astype(np.uint8)

    new = Image.new("RGBA", (width, SHAPE_HEIGHT))
    new.paste(shape.crop((0, 0, width, start)), (0, 0))
    new.paste(Image.fromarray(patch), (0, start))
    source = new.crop((0, join - 1, width, join))
    for y in range(join, SHAPE_HEIGHT):
        distance = y - join
        flare = float(ramp(distance, 15, 135))
        scale = 1 + 0.65 * flare
        scanline = source.transform(
            (width, 1),
            Image.Transform.AFFINE,
            (1 / scale, 0, center * (1 - 1 / scale), 0, 1, 0),
            Image.Resampling.BICUBIC,
        )
        pixels = np.array(scanline)
        # Replace the repeated highlights with a broad skin gradient while keeping
        # the side outlines and the exact sampled row at the join.
        edge = np.abs(np.arange(width) - center) / (radius * scale)
        tint = chest_light - ramp(edge, 0.15, 0.90)[:, None] * [13, 22, 24]
        weight = ((1 - ramp(edge, 0.73, 0.93)) * ramp(distance, 0, 58))[None, :, None]
        pixels[..., :3] = (pixels[..., :3] * (1 - weight) + tint * weight).round()
        # Fade away below even the deepest opening.
        opacity = 1 - float(ramp(y, SHAPE_HEIGHT - 42, SHAPE_HEIGHT - 1))
        pixels[..., 3] = (pixels[..., 3] * opacity).round()
        new.paste(Image.fromarray(pixels), (0, y))
    return clean_alpha(new)


def save_thumbnail(shape, body, name):
    destination = ROOT / "assets/thumbnails/faces" / body / "shapes"
    destination.mkdir(parents=True, exist_ok=True)
    # All variants share the same crop so cheek and jaw widths stay comparable.
    thumbnail = shape.crop((64, 380, 448, NECK_CROP[body] + 18))
    thumbnail.thumbnail((128, 64), Image.Resampling.LANCZOS)
    thumbnail.save(destination / f"{name}.webp", quality=86)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body", choices=NECK_CROP, required=True)
    parser.add_argument("--edited", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    original = Image.open(
        ROOT / "assets/references/masters/heads" / args.body / "blank.png"
    ).convert("RGBA")
    generated = Image.open(args.edited).convert("RGBA")
    neck = NECK_CROP[args.body]
    w, h = CELL_SIZE
    review = Image.new("RGBA", (w * 4, SHAPE_HEIGHT * 4), "#eee8dc")
    destination = ROOT / "assets/sprites/faces" / args.body / "shapes"
    args.output.mkdir(parents=True, exist_ok=True)
    destination.mkdir(parents=True, exist_ok=True)
    report = []
    for index in range(16):
        row, col = divmod(index, 4)
        bounds = tuple(
            round(a * dimension / 4)
            for a, dimension in (
                (col, generated.width),
                (row, generated.height),
                (col + 1, generated.width),
                (row + 1, generated.height),
            )
        )
        edited = generated.crop(bounds).resize((w, h), Image.Resampling.LANCZOS)
        if np.count_nonzero(np.asarray(edited.getchannel("A")) > 127) < 60_000:
            raise ValueError(f"Cell {index + 1} is missing its head silhouette.")
        shape, transform, join, jaw = register(original, edited, neck)
        shape = extend_neck(shape, neck, join, jaw)
        name = f"{index + 1:02d}.png"
        shape.save(destination / name)
        save_thumbnail(shape, args.body, name.removesuffix(".png"))
        review.alpha_composite(shape, (col * w, row * SHAPE_HEIGHT))
        report.append(
            {
                "id": name.removesuffix(".png"),
                "offset": [0, 0],
                "registration": transform,
            }
        )
    (args.output / "placements.json").write_text(json.dumps(report, indent=2) + "\n")
    review.convert("RGB").resize(
        (w * 2, SHAPE_HEIGHT * 2), Image.Resampling.LANCZOS
    ).save(args.output / "reassembled.png")


if __name__ == "__main__":
    main()
