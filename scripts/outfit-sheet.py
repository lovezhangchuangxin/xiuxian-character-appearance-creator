"""Place each outfit over the source body's neck and empty hands."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from eye_sheet import clean_alpha

ROOT = Path(__file__).resolve().parents[1]
SIZE = (1024, 1536)
FIT = {
    "male": {"neck": 218, "wrist": 723, "left": (256, 351), "right": (666, 770), "finger": 856},
    "female": {"neck": 324, "wrist": 766, "left": (294, 386), "right": (638, 737), "finger": 903},
}


def bounds_of(alpha):
    return alpha.point(lambda a: 255 if a > 72 else 0).getbbox()


def contour_collar(art, center):
    """Soften the straight cut across a closed collar while retaining the trim."""
    height = min(64, art.height)
    strip = art.crop((0, 0, art.width, height)).convert("RGBa")
    rgba = np.asarray(strip, dtype=np.float32)
    x = np.arange(art.width)
    near_center = np.abs(x - center) <= 25
    leading_rows = np.argmax(rgba[:, near_center, 3] > 100, axis=0)
    present = np.any(rgba[:, near_center, 3] > 100, axis=0)
    if not np.all(present) or np.quantile(leading_rows, .85) > 17:
        return art
    y = np.arange(height)[:, None]
    curve = np.maximum(0, 1 - ((x - center) / 43) ** 2) ** 2
    displacement = 7 * curve * (1 - y / (height - 1)) ** 2
    source_y = y - displacement
    lower = np.floor(np.maximum(0, source_y)).astype(int)
    fraction = np.maximum(0, source_y) - lower
    shifted = rgba[lower, x] * (1 - fraction[..., None]) + rgba[np.minimum(lower + 1, height - 1), x] * fraction[..., None]
    shifted[source_y < 0] = 0
    patch = Image.fromarray(shifted.round().astype(np.uint8), mode="RGBa").convert("RGBA")
    art.paste(patch, (0, 0))
    return art


def fitted(piece, fit):
    region = bounds_of(piece.getchannel("A"))
    if not region:
        raise ValueError("An outfit cell is empty.")
    art = piece.crop(region)
    if art.height <= piece.height // 2:
        raise ValueError("An outfit cell is missing part of its silhouette.")
    top = fit["neck"] + 4
    height = 1485 - top
    width = round(np.clip(art.width * height / art.height, 300, 680))
    art = art.resize((width, height), Image.Resampling.LANCZOS)
    a = np.asarray(art.getchannel("A"))
    _, neckline = np.where(a[:34] > 100)
    if neckline.size:
        left, right = np.quantile(neckline, [.08, .92])
        center = (left + right) / 2
    else:
        center = art.width / 2
    center = np.clip(center, width * .43, width * .57)
    art = contour_collar(art, center)
    x = round(512 - center)
    overlay = Image.new("RGBA", SIZE)
    overlay.alpha_composite(art, (x, top))
    return overlay


def runs(row):
    changes = np.flatnonzero(np.diff(np.r_[False, row, False]))
    return list(zip(changes[::2], changes[1::2]))


def wrist_position(overlay, fit, side):
    alpha = np.asarray(overlay.getchannel("A")) > 112
    top = fit["neck"]
    bottom = fit["wrist"]
    if side == "right":
        alpha = alpha[:, ::-1]
    detached = []
    for y in range(top + 200, min(bottom + 115, 950)):
        row = runs(alpha[y])
        if len(row) < 2:
            continue
        start, end = row[0]
        gap = row[1][0] - end
        if (142 < start < 418 and end <= 444 and 8 <= end - start <= 154 and gap >= 7):
            detached.append((int((start + end) // 2), y))

    if detached:
        # A cuff ends as its separated silhouette narrows to the last small run.
        bands = [[detached[0]]]
        for point in detached[1:]:
            if point[1] - bands[-1][-1][1] > 7:
                bands.append([])
            bands[-1].append(point)
        bands = [band for band in bands if len(band) > 13]
        if bands:
            band = min(bands, key=lambda group: abs(group[-1][1] - bottom))
            near_end = band[-12:]
            x = round(np.median([point[0] for point in near_end]))
            y = band[-1][1] - 5
            return ((1023 - x) if side == "right" else x, y)

    # For a sleeve that overlaps the skirt in projection, seek its outer edge.
    local = []
    for y in range(bottom - 115, bottom + 15):
        row = np.flatnonzero(alpha[y, 150:475])
        if row.size:
            local.append((int(row[0]) + 150, y))
    if not local:
        raise ValueError("Could not place the wrist on an outfit.")
    x, y = min(local, key=lambda point: (point[0] + abs(point[1] - bottom) * .23))
    x += 23
    return ((1023 - x) if side == "right" else x, y)


def preserve_skin(base, fit, side):
    left, right = fit[side]
    crop = base.crop((left, fit["wrist"] - 28, right, fit["finger"]))
    rgba = np.array(crop)
    red, green, blue = (rgba[..., i].astype(np.int16) for i in range(3))
    skin = np.clip((red - green - 9) / 10, 0, 1) * (green >= blue - 2)
    rgba[..., 3] = (rgba[..., 3] * skin).astype(np.uint8)
    return clean_alpha(Image.fromarray(rgba))


def finish(overlay, base, fit, override):
    worn = Image.new("RGBA", SIZE)
    wrists = {}
    for side in ("left", "right"):
        hand = preserve_skin(base, fit, side)
        wrist = bounds_of(hand.getchannel("A").crop((0, 0, hand.width, 25)))
        if not wrist:
            raise ValueError(f"Missing the {side} wrist in the base.")
        x, y = override.get(side) or wrist_position(overlay, fit, side)
        wrist_middle = (wrist[0] + wrist[2]) // 2
        worn.alpha_composite(hand, (x - wrist_middle, y - 32))
        wrists[side] = [x, y]
    worn.alpha_composite(overlay)
    return clean_alpha(worn), wrists


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body", choices=FIT, required=True)
    parser.add_argument("--sheets", type=Path, nargs=4, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wrists", type=Path)
    args = parser.parse_args()
    fit = FIT[args.body]
    overrides = json.loads(args.wrists.read_text()) if args.wrists else {}
    source = ROOT / "assets/sprites/bodies" / args.body / "white.png"
    base = Image.open(source).convert("RGBA")
    head = Image.open(ROOT / "assets/sprites/faces" / args.body / "shapes" / "01.png").convert("RGBA")
    head = head.resize((171, head.height // 3), Image.Resampling.BICUBIC)
    head_position = (427, 32 if args.body == "male" else 142)
    sheet_review = Image.new("RGBA", (1024, 1536), "#eee8dc")
    destination = ROOT / "assets/sprites/outfits" / args.body
    thumbnails = ROOT / "assets/thumbnails/outfits" / args.body
    args.output.mkdir(parents=True, exist_ok=True)
    thumbnails.mkdir(parents=True, exist_ok=True)
    report = []
    for batch, source in enumerate(args.sheets):
        with Image.open(source) as original:
            if original.mode != "RGBA" or original.getchannel("A").getextrema()[0] != 0:
                raise ValueError(f"The sheet must have a transparent background: {source}")
            width, height = original.width // 2, original.height // 2
            for row in range(2):
                for col in range(2):
                    seq = 4 * batch + row * 2 + col
                    name = f"{seq + 1:02d}"
                    cell = original.crop((col * width, row * height, (col + 1) * width, (row + 1) * height))
                    garment = fitted(clean_alpha(cell), fit)
                    wearing, wrists = finish(garment, base, fit, overrides.get(name, {}))
                    wearing.save(destination / f"{name}.png")
                    thumbnail = wearing.crop(wearing.getbbox())
                    thumbnail.thumbnail((72, 112), Image.Resampling.LANCZOS)
                    thumbnail.save(thumbnails / f"{name}.webp", quality=83)

                    panel = Image.new("RGBA", SIZE, "#eee8dc")
                    panel.alpha_composite(head, head_position)
                    panel.alpha_composite(wearing)
                    panel = panel.resize((256, 384), Image.Resampling.LANCZOS)
                    ImageDraw.Draw(panel).text((10, 12), name, fill="#334d43")
                    sheet_review.alpha_composite(panel, (256 * (seq % 4), 384 * (seq // 4)))
                    report.append({"id": name, "source": source.name, "wrist": wrists})
    (args.output / "placements.json").write_text(json.dumps(report, indent=2) + "\n")
    sheet_review.convert("RGB").save(args.output / "try-on.jpg", quality=94)


if __name__ == "__main__":
    main()
