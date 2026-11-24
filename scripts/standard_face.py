"""Export the four independently positioned layers of a standard face."""

import argparse
import json
from pathlib import Path

import numpy as np
from eye_sheet import CELL_SIZE, EYE_WINDOWS, delta_layer, extract_layer, eye_mask
from PIL import Image, ImageDraw, ImageFilter

FEATURE_REGIONS = {
    "male": {
        "brows": [(70, 235, 230, 277), (272, 235, 432, 277)],
        "noses": [(220, 308, 283, 423)],
        "mouths": [(199, 440, 305, 483)],
    },
    "female": {
        "brows": [(80, 232, 226, 273), (287, 232, 435, 273)],
        "noses": [(225, 338, 286, 423)],
        "mouths": [(212, 439, 307, 481)],
    },
}


def region_mask(rectangles):
    mask = Image.new("L", CELL_SIZE)
    draw = ImageDraw.Draw(mask)
    for bounds in rectangles:
        draw.rounded_rectangle(bounds, radius=7, fill=255)
    return np.asarray(mask.filter(ImageFilter.GaussianBlur(3)), dtype=np.float32) / 255


def separate(body, blank, complete):
    windows = EYE_WINDOWS[body]
    eye_base = Image.composite(
        blank,
        complete,
        eye_mask(CELL_SIZE, windows).filter(ImageFilter.GaussianBlur(2)),
    )
    eye, bounds, _ = extract_layer(eye_base, complete, windows)
    parts = {"eyes": (eye, bounds[:2])}
    base = np.asarray(blank, dtype=np.float32)[..., :3] / 255
    art = np.asarray(complete, dtype=np.float32)[..., :3] / 255
    raw_delta = art - base
    correction = np.median(raw_delta[132:205, 165:345], axis=(0, 1))
    delta = np.clip(art - correction, 0, 1) - base
    strength = np.max(abs(delta), axis=2)
    coverage = np.clip((strength - 3 / 255) / (6 / 255), 0, 1)
    coverage = coverage * coverage * (3 - 2 * coverage)
    for slot, regions in FEATURE_REGIONS[body].items():
        layer = delta_layer(base, delta, region_mask(regions) * coverage)
        bounds = layer.getbbox()
        if not bounds:
            raise ValueError(f"No visible pixels in {body}/{slot}")
        parts[slot] = (layer.crop(bounds), bounds[:2])
    return parts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body", choices=FEATURE_REGIONS, required=True)
    parser.add_argument("--blank", type=Path, required=True)
    parser.add_argument("--complete", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    blank = Image.open(args.blank).convert("RGBA")
    complete = Image.open(args.complete).convert("RGBA")
    if blank.size != CELL_SIZE or complete.size != CELL_SIZE:
        parser.error("Both images must use the aligned 512 × 620 head crop.")

    parts = separate(args.body, blank, complete)
    restored = blank.copy()
    placements = {}
    for slot, (layer, offset) in parts.items():
        target = args.output / slot / "standard.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        layer.save(target)
        restored.alpha_composite(layer, offset)
        placements[slot] = {"offset": offset, "size": layer.size}
    (args.output / "placements.json").write_text(
        json.dumps(placements, indent=2) + "\n", encoding="utf-8"
    )

    preview = Image.new("RGBA", (CELL_SIZE[0] * 2, CELL_SIZE[1]), "#eee8dc")
    preview.alpha_composite(complete)
    preview.alpha_composite(restored, (CELL_SIZE[0], 0))
    preview.convert("RGB").save(args.output / "comparison.png")


if __name__ == "__main__":
    main()
