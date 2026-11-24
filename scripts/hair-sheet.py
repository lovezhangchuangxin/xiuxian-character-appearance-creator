"""Extract and place 16 numbered hair pieces from a transparent 4 × 4 sheet."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import find_objects, label, maximum_filter

from eye_sheet import clean_alpha

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "src/character/numbered-hair.json"
PARTS = ("front", "back", "top")


def pieces_in_sheet(sheet):
    rgba = np.array(sheet)
    components, _ = label(rgba[..., 3] > 48, structure=np.ones((3, 3)))
    sizes = np.bincount(components.ravel())
    tiles = {}
    for key, slices in enumerate(find_objects(components), 1):
        if slices is None or sizes[key] < 400:
            continue
        y, x = slices
        row = min(3, (y.start + y.stop) * 2 // sheet.height)
        col = min(3, (x.start + x.stop) * 2 // sheet.width)
        index = row * 4 + col
        if index not in tiles or sizes[key] > sizes[tiles[index][0]]:
            tiles[index] = (key, y, x)
    if len(tiles) != 16:
        missing = [index + 1 for index in range(16) if index not in tiles]
        raise ValueError(f"Missing separate hair silhouettes in cells {missing}.")
    for index in range(16):
        key, y, x = tiles[index]
        height = slice(max(0, y.start - 3), y.stop + 3)
        width = slice(max(0, x.start - 3), x.stop + 3)
        area = rgba[height, width].copy()
        support = maximum_filter(components[height, width] == key, size=5)
        area[~support] = 0
        yield clean_alpha(Image.fromarray(area))


def placement(piece, index, body, part):
    aspect = piece.width / piece.height
    row, col = divmod(index, 4)
    if part == "front":
        width = (186 if body == "male" else 191) + (2, 0, -3, 3)[row]
        height = round(np.clip(width / aspect, 125, 212))
        alpha = np.asarray(piece.getchannel("A"))
        mid = alpha[:, round(piece.width * .39):round(piece.width * .61)] > 110
        center_depth = np.flatnonzero(mid.mean(axis=1) > .2)
        if center_depth.size:
            usable_height = 102 * piece.height / max(center_depth[-1], 1)
            height = min(height, round(usable_height))
        return [width, height, 0, -26]

    if part == "back":
        heights = ((426, 448, 405, 445), (200, 230, 251, 171),
                   (420, 360, 395, 338), (397, 408, 415, 435))
        height = heights[row][col] + (14 if body == "female" else 0)
        width = round(np.clip(height * aspect, 145, 255))
        alpha = np.asarray(piece.getchannel("A"))
        cap = np.where(alpha[:max(1, round(piece.height * .18))] > 96)[1]
        dx = round(np.clip(width * (.5 - np.mean(cap) / piece.width), -42, 42)) if cap.size else 0
        return [width, height, dx, 7]

    width = (71, 67, 76, 72)[row] + (0, 4, -3, 5)[col]
    height = round(np.clip(width / aspect, 28, 57))
    alpha = np.asarray(piece.getchannel("A"))
    center = alpha[:, round(piece.width * .35):round(piece.width * .65)] > 110
    connected = np.flatnonzero(center.mean(axis=1) > .25)
    join = connected[-1] / piece.height if connected.size else 1
    return [width, height, 0, round(-12 + (.5 - join) * height)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body", choices=("male", "female"), required=True)
    parser.add_argument("--part", choices=PARTS, required=True)
    parser.add_argument("--sheet", type=Path, required=True)
    args = parser.parse_args()
    with Image.open(args.sheet) as image:
        if image.mode != "RGBA" or image.getchannel("A").getextrema()[0] != 0:
            raise ValueError(f"Expected transparent source sheet: {args.sheet}")
        pieces = list(pieces_in_sheet(image))

    transforms = [placement(piece, index, args.body, args.part) for index, piece in enumerate(pieces)]
    destination = ROOT / "assets/sprites/hair" / args.body / args.part
    destination.mkdir(parents=True, exist_ok=True)
    for index, piece in enumerate(pieces, start=1):
        piece.save(destination / f"{index:02d}.png")

    catalog = json.loads(CATALOG.read_text(encoding="utf-8")) if CATALOG.is_file() else {}
    catalog.setdefault(args.body, {})[args.part] = transforms
    CATALOG.write_text(json.dumps(catalog, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
