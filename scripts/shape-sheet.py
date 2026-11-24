"""Register AI-generated jaw and cheek variations to the unchanged head anchors."""

import argparse
import json
from pathlib import Path

import numpy as np
from eye_sheet import CELL_SIZE, align_tile, clean_alpha
from PIL import Image

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


def register(original, edited, neck):
    aligned, matrix = align_tile(original, edited, ((18, 390, 495, 566),))
    aligned = clean_alpha(scale_to_base(original, aligned))
    w, h = CELL_SIZE
    y, x = np.ogrid[:h, :w]
    # Keep the ears, forehead and outfit seam on the original head.
    left = ramp(x, 75, 105)
    right = 1 - ramp(x, 402, 442)
    cheek = ramp(y, 383, 436)
    chin = 1 - ramp(y, neck - 19, neck - 2)
    mix = Image.fromarray((left * right * cheek * chin * 255).round().astype(np.uint8))

    # Blend in premultiplied space near the new silhouette to avoid dark fringes.
    shaped = Image.composite(aligned.convert("RGBa"), original.convert("RGBa"), mix)
    shaped = clean_alpha(shaped.convert("RGBA"))
    return shaped, matrix


def extend_neck(shape, neck):
    width = shape.width
    # Use a row below the jaw shadow and above the original undergarment.
    join = neck + 20
    source = shape.crop((0, join - 4, width, join))
    source = source.resize((width, 1), Image.Resampling.BOX)
    left, _, right, _ = source.getchannel("A").getbbox()
    center = (left + right) / 2
    source_rgba = np.asarray(source)[0]
    skin = np.median(source_rgba[source_rgba[:, 3] > 240, :3], axis=0)
    chest_light = np.clip(skin + [9, 12, 13], 0, 255)
    new = Image.new("RGBA", (width, SHAPE_HEIGHT))
    new.paste(shape.crop((0, 0, width, join)), (0, 0))
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
        # Let the jaw shadow ease into the lighter skin under the collar.
        inner = 1 - ramp(np.abs(np.arange(width) - center), 45 * scale, 95 * scale)
        weight = (inner * float(ramp(distance, 0, 115)))[None, :, None]
        pixels[..., :3] = (
            pixels[..., :3] * (1 - weight) + chest_light * weight
        ).round()
        # Fade away below even the deepest opening.
        opacity = 1 - float(ramp(y, SHAPE_HEIGHT - 42, SHAPE_HEIGHT - 1))
        pixels[..., 3] = (pixels[..., 3] * opacity).round()
        new.paste(Image.fromarray(pixels), (0, y))
    return clean_alpha(new)


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
        shape, transform = register(original, edited, neck)
        shape = extend_neck(shape, neck)
        name = f"{index + 1:02d}.png"
        shape.save(destination / name)
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
