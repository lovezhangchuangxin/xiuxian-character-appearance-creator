"""Make single-feature sheets and extract aligned facial sprites for the editor."""

import argparse
import json
from pathlib import Path

import numpy as np
from eye_sheet import (
    CELL_SIZE,
    align_tile,
    background_report,
    clean_alpha,
    delta_layer,
    extract_layer,
    eye_mask,
    largest_component,
)
from PIL import Image, ImageDraw, ImageFilter

WINDOWS = {
    "male": {
        "eyes": ((75, 274, 231, 346), (273, 274, 435, 346)),
        "brows": ((66, 214, 233, 277), (270, 214, 439, 277)),
        "noses": ((215, 312, 293, 428),),
        "mouths": ((187, 431, 321, 487),),
    },
    "female": {
        "eyes": ((74, 275, 233, 354), (269, 275, 440, 354)),
        "brows": ((69, 212, 230, 274), (284, 212, 446, 274)),
        "noses": ((215, 339, 292, 431),),
        "mouths": ((198, 429, 320, 489),),
    },
}


def cubic(points):
    for t in np.linspace(0, 1, 33):
        u = 1 - t
        yield tuple(
            u**3 * a + 3 * u**2 * t * b + 3 * u * t**2 * c + t**3 * d
            for a, b, c, d in zip(*points, strict=True)
        )


def draw_guide(path, part, sex):
    """Draw eye/brow shape diagrams as conditioning references, never runtime art."""
    guide = Image.new("RGB", (720, 440), "#f5efe3")
    draw = ImageDraw.Draw(guide)
    ink = "#385750"
    for row in range(4):
        for col in range(4):
            x, y = col * 180, row * 110
            draw.rectangle((x + 1, y + 1, x + 178, y + 108), outline="#bfb6a3")
            center = y + 56
            outer, inner = ((0, 0), (0, 0), (-7, 4), (6, -3))[row]
            upper = (
                (16, 5, 10, 11)[row] + (col - 1) * 1.1 + (1 if sex == "female" else 0)
            )
            lower = (11, 8, 8, 8)[row] + col * 0.8
            width = 54 + col * 2
            for mirror in (False, True):

                def reflect(points, x=x, mirror=mirror):
                    return [(x + (179 - sx if mirror else sx), sy) for sx, sy in points]

                x0 = 13 - col
                x1 = x0 + width
                a = (x0, center + outer)
                b = (x1, center + inner)
                if part == "eyes":
                    top = cubic(
                        (a, (x0 + 14, center - upper), (x1 - 15, center - upper), b)
                    )
                    bottom = cubic(
                        (a, (x0 + 13, center + lower), (x1 - 15, center + lower), b)
                    )
                    draw.line(reflect(top), fill=ink, width=4)
                    draw.line(reflect(bottom), fill=ink, width=2)
                else:
                    peak = center - (1, 8, 11, 13)[row] - col
                    if row == 0:
                        curve = list(
                            cubic((a, (x0 + 14, peak), (x1 - 16, peak - 2), b))
                        )
                    elif row == 1:
                        curve = list(
                            cubic(
                                (
                                    (x0, center + 2),
                                    (x0 + 5, peak - 5),
                                    (x1 - 19, center - 6),
                                    (x1, center + 5),
                                )
                            )
                        )
                    elif row == 2:
                        curve = list(
                            cubic(
                                (
                                    (x0, center + 7),
                                    (x0 + 9, peak - 12),
                                    (x1 - 18, peak - 6),
                                    (x1, center + 3),
                                )
                            )
                        )
                    else:
                        curve = [
                            (x0, center + 8),
                            (x0 + 16, peak),
                            (x0 + 26, peak + 1),
                            (x1, center + 5),
                        ]
                    draw.line(reflect(curve), fill=ink, width=3 + col, joint="curve")
    path.parent.mkdir(parents=True, exist_ok=True)
    guide.save(path)


def prepare(args):
    blank = Image.open(args.blank).convert("RGBA")
    complete = Image.open(args.complete).convert("RGBA")
    if blank.size != CELL_SIZE or complete.size != CELL_SIZE:
        raise ValueError("Both references must use the 512 × 620 head crop.")
    width, height = CELL_SIZE
    mask = eye_mask(CELL_SIZE, WINDOWS[args.body][args.part]).filter(
        ImageFilter.GaussianBlur(2)
    )
    tile = clean_alpha(Image.composite(blank, complete, mask))
    sheet = Image.new("RGBA", (width * args.grid, height * args.grid))
    for row in range(args.grid):
        for col in range(args.grid):
            sheet.paste(tile, (col * width, row * height))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    if args.guide:
        draw_guide(args.guide, args.part, args.body)


def extract_non_eye(original, aligned, windows, part):
    base = np.asarray(original, dtype=np.float32)[..., :3] / 255
    art = np.asarray(aligned, dtype=np.float32)[..., :3] / 255
    sky = art[126:195, 164:345] - base[126:195, 164:345]
    correction = np.median(sky, axis=(0, 1))
    delta = np.clip(art - correction, 0, 1) - base
    noise = float(np.quantile(np.max(abs(sky - correction), axis=2), 0.95))
    low = max(3 / 255, min(12 / 255, noise + 2 / 255))
    strength = np.max(abs(delta), axis=2)
    weight = np.clip((strength - low) / (9 / 255), 0, 1)
    support = (
        np.asarray(
            eye_mask(CELL_SIZE, windows).filter(ImageFilter.GaussianBlur(2)),
            dtype=np.float32,
        )
        / 255
    )
    if part == "brows":
        ink = (np.min(delta, axis=2) < -0.13) & (np.mean(art, axis=2) < 0.75)
        seed = np.zeros(ink.shape, dtype=np.uint8)
        for x0, y0, x1, y1 in windows:
            component = largest_component(ink[y0:y1, x0:x1])
            if np.count_nonzero(component) < 20:
                raise ValueError("A brow is missing or outside its window.")
            seed[y0:y1, x0:x1] = component
        support *= (
            np.asarray(
                Image.fromarray(seed)
                .filter(ImageFilter.MaxFilter(9))
                .filter(ImageFilter.GaussianBlur(1)),
                dtype=np.float32,
            )
            / 255
        )
    output = delta_layer(base, delta, weight * weight * (3 - 2 * weight) * support)
    bounds = output.getbbox()
    if bounds is None or output.getchannel("A").getextrema()[1] < 28:
        raise ValueError("No usable ink or shadow in the feature window.")
    return output.crop(bounds), bounds, {"skin_noise_p95": round(noise * 255, 2)}


def extract(args):
    carrier = Image.open(args.carrier).convert("RGBA")
    edited = Image.open(args.edited).convert("RGBA")
    width, height = CELL_SIZE
    if carrier.size != (width * args.grid, height * args.grid):
        raise ValueError("Carrier dimensions do not match the requested grid.")
    windows = WINDOWS[args.body][args.part]
    if args.part == "brows":
        windows = tuple(
            (left, top - 18, right, bottom) for left, top, right, bottom in windows
        )
    output = Image.new("RGBA", carrier.size)
    metadata = {
        "body": args.body,
        "part": args.part,
        "grid": args.grid,
        "edited_size": list(edited.size),
        "edited_background_alpha": background_report(edited, carrier),
        "variants": [],
        "rejected": [],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    for row in range(args.grid):
        for col in range(args.grid):
            x, y = col * width, row * height
            original = carrier.crop((x, y, x + width, y + height))
            silhouette = original.getchannel("A")
            cell = tuple(
                round(n * side / args.grid)
                for n, side in (
                    (col, edited.width),
                    (row, edited.height),
                    (col + 1, edited.width),
                    (row + 1, edited.height),
                )
            )
            edited_tile = edited.crop(cell).resize(CELL_SIZE, Image.Resampling.LANCZOS)
            index = row * args.grid + col + 1
            try:
                aligned, registration = align_tile(original, edited_tile, windows)
                if args.part == "eyes":
                    layer, bounds, quality = extract_layer(original, aligned, windows)
                else:
                    layer, bounds, quality = extract_non_eye(
                        original, aligned, windows, args.part
                    )
            except ValueError as error:
                metadata["rejected"].append({"index": index, "reason": str(error)})
            else:
                name = f"{args.part}-{index:02}.png"
                layer.save(args.output / name)
                original.alpha_composite(layer, bounds[:2])
                metadata["variants"].append(
                    {
                        "index": index,
                        "file": name,
                        "offset": list(bounds[:2]),
                        "size": list(layer.size),
                        "registration": registration,
                        "quality": quality,
                    }
                )
            original.putalpha(silhouette)
            output.paste(original, (x, y))
    output = clean_alpha(output)
    metadata["reassembled_background_alpha"] = background_report(output, carrier)
    (args.output / "placements.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    output.save(args.output / "reassembled-transparent.png")
    preview = Image.new("RGBA", output.size, "#eee8dc")
    preview.alpha_composite(output)
    preview.convert("RGB").resize(
        (width // 2 * args.grid, height // 2 * args.grid), Image.Resampling.LANCZOS
    ).save(args.output / "reassembled.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(required=True)
    for name, run in (("prepare", prepare), ("extract", extract)):
        command = sub.add_parser(name)
        command.add_argument("--body", choices=WINDOWS, required=True)
        command.add_argument("--part", choices=WINDOWS["male"], required=True)
        command.add_argument("--grid", type=int, choices=(2, 4), required=True)
        command.add_argument("--output", type=Path, required=True)
        command.set_defaults(run=run)
    sub.choices["prepare"].add_argument("--blank", type=Path, required=True)
    sub.choices["prepare"].add_argument("--complete", type=Path, required=True)
    sub.choices["prepare"].add_argument("--guide", type=Path)
    sub.choices["extract"].add_argument("--carrier", type=Path, required=True)
    sub.choices["extract"].add_argument("--edited", type=Path, required=True)
    args = parser.parse_args()
    if getattr(args, "guide", None) and (
        args.part not in ("eyes", "brows") or args.grid != 4
    ):
        parser.error("Shape guides are for 4 × 4 eye and brow sheets.")
    args.run(args)


if __name__ == "__main__":
    main()
