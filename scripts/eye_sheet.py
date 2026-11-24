"""Prepare and extract coordinate-registered xianxia eye sheets."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

EYE_WINDOWS = {
    "male": ((82, 270, 227, 328), (272, 270, 427, 328)),
    "female": ((82, 275, 227, 341), (272, 275, 427, 341)),
}
CELL_SIZE = (512, 620)
ALPHA_NOISE_FLOOR = 8


def eye_mask(size, windows):
    mask = Image.new("L", size)
    draw = ImageDraw.Draw(mask)
    for left, top, right, bottom in windows:
        draw.rounded_rectangle((left, top, right - 1, bottom - 1), radius=6, fill=255)
    return mask


def clean_alpha(image):
    rgba = np.array(image.convert("RGBA"))
    rgba[rgba[..., 3] <= ALPHA_NOISE_FLOOR] = 0
    return Image.fromarray(rgba, "RGBA")


def background_report(edited, carrier):
    silhouette = carrier.getchannel("A").point(lambda alpha: 255 if alpha > ALPHA_NOISE_FLOOR else 0)
    # Exclude the antialiased boundary and allow a small amount of registration drift.
    silhouette = silhouette.resize(edited.size, Image.Resampling.NEAREST).filter(ImageFilter.MaxFilter(15))
    pixels = np.asarray(edited.getchannel("A"))[np.asarray(silhouette) == 0]
    return {
        "sampled_pixels": int(pixels.size),
        "zero_alpha_pixels": int(np.count_nonzero(pixels == 0)),
        "visible_alpha_pixels": int(np.count_nonzero(pixels > ALPHA_NOISE_FLOOR)),
        "max_alpha": int(pixels.max(initial=0)),
    }


def prepare(args):
    blank = Image.open(args.blank).convert("RGBA")
    complete = Image.open(args.complete).convert("RGBA")
    if blank.size != CELL_SIZE or complete.size != CELL_SIZE:
        raise ValueError("Both head references must use the aligned 512 × 620 crop.")
    width, height = complete.size
    mask = eye_mask(complete.size, EYE_WINDOWS[args.body]).filter(ImageFilter.GaussianBlur(2))
    tile = clean_alpha(Image.composite(blank, complete, mask))
    sheet = Image.new("RGBA", (width * args.columns, height * args.rows))
    for row in range(args.rows):
        for col in range(args.columns):
            sheet.paste(tile, (col * width, row * height))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)


def luma(image):
    rgba = np.asarray(image, dtype=np.float32) / 255
    alpha = rgba[..., 3]
    rgb = rgba[..., :3]
    return (rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722) * alpha + 0.9 * (1 - alpha)


def align_tile(original, edited, windows):
    """Fit scale and translation against stable edges outside the eye area."""
    width, height = original.size
    source = luma(original)
    target = luma(edited)
    grad_y, grad_x = np.gradient(source)
    weights = np.hypot(grad_x, grad_y)
    stable = weights > 0.033
    stable[:12] = stable[-24:] = False
    stable[:, :10] = stable[:, -10:] = False
    for left, top, right, bottom in windows:
        stable[top - 8:bottom + 8, left - 6:right + 6] = False
    y, x = np.nonzero(stable)
    if not len(x):
        raise ValueError("No stable head edges available for registration.")
    stride = max(1, len(x) // 3500)
    x, y = x[::stride], y[::stride]
    x_mid, y_mid = (width - 1) / 2, (height - 1) / 2
    expected = source[y, x]

    def score(transform):
        sx, sy, dx, dy = transform
        ref_x = np.clip(np.rint((x - x_mid) * sx + x_mid + dx).astype(int), 0, width - 1)
        ref_y = np.clip(np.rint((y - y_mid) * sy + y_mid + dy).astype(int), 0, height - 1)
        return np.minimum(abs(target[ref_y, ref_x] - expected), 0.26).mean()

    params = [1.0, 1.0, 0.0, 0.0]
    before = score(params)
    for scale_step, shift_step in ((0.06, 14), (0.03, 7), (0.012, 3), (0.004, 1)):
        for axis, step in ((2, shift_step), (3, shift_step), (0, scale_step), (1, scale_step)):
            candidate = params.copy()
            choices = []
            for offset in range(-2, 3):
                candidate[axis] = params[axis] + offset * step
                choices.append((score(candidate), abs(offset), candidate[axis]))
            params[axis] = min(choices)[2]

    sx, sy, dx, dy = params
    matrix = (sx, 0, x_mid * (1 - sx) + dx, 0, sy, y_mid * (1 - sy) + dy)
    aligned = edited.transform(original.size, Image.Transform.AFFINE, matrix, Image.Resampling.BICUBIC)
    return aligned, {
        "scale": [round(sx, 4), round(sy, 4)],
        "shift": [round(dx, 2), round(dy, 2)],
        "edge_error_before": round(float(before), 4),
        "edge_error_after": round(float(score(params)), 4),
    }


def largest_component(pixels):
    available = set(zip(*np.nonzero(pixels)))
    largest = []
    while available:
        todo = [available.pop()]
        component = []
        while todo:
            y, x = todo.pop()
            component.append((y, x))
            neighbors = {(y + dy, x + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)}
            connected = available.intersection(neighbors)
            available.difference_update(connected)
            todo.extend(connected)
        if len(component) > len(largest):
            largest = component
    result = np.zeros(pixels.shape, dtype=np.uint8)
    if largest:
        result[tuple(zip(*largest))] = 255
    return result


def eye_support(delta, art, windows):
    dark_ink = (np.min(delta, axis=2) < -0.18) & (np.mean(art, axis=2) < 0.66)
    support = np.zeros(dark_ink.shape, dtype=np.uint8)
    for left, top, right, bottom in windows:
        ink = largest_component(dark_ink[top:bottom, left:right])
        if not np.any(ink):
            raise ValueError("No eye ink detected in one of the eye windows.")
        support[top:bottom, left:right] = ink
    expanded = Image.fromarray(support).filter(ImageFilter.MaxFilter(17)).filter(ImageFilter.GaussianBlur(1.5))
    return np.asarray(expanded, dtype=np.float32) / 255


def extract_layer(original, edited, windows):
    base = np.asarray(original, dtype=np.float32)[..., :3] / 255
    art = np.asarray(edited, dtype=np.float32)[..., :3] / 255
    quiet_skin = art[132:205, 165:345] - base[132:205, 165:345]
    correction = np.median(quiet_skin, axis=(0, 1))
    delta = np.clip(art - correction, 0, 1) - base
    skin_noise = np.quantile(np.max(abs(quiet_skin - correction), axis=2), 0.95)
    low = max(6 / 255, float(skin_noise) + 3 / 255)
    high = low + 8 / 255
    strength = np.max(abs(delta), axis=2)
    coverage = np.clip((strength - low) / (high - low), 0, 1)
    coverage = coverage * coverage * (3 - 2 * coverage)
    mask = np.asarray(eye_mask(original.size, windows), dtype=np.float32) / 255
    support = coverage * mask * eye_support(delta, art, windows)
    output = delta_layer(base, delta, support)
    alpha8 = np.asarray(output.getchannel("A"))
    bounds = output.getbbox()
    if bounds is None:
        raise ValueError("Eye windows contain no extractable features.")
    return output.crop(bounds), bounds, {
        "skin_noise_p95": round(float(skin_noise * 255), 2),
        "opacity_threshold": round(low * 255, 2),
        "window_edge_pixels": int(sum(
            np.count_nonzero(alpha8[top:top + 3, left:right] > 24)
            + np.count_nonzero(alpha8[bottom - 3:bottom, left:right] > 24)
            + np.count_nonzero(alpha8[top:bottom, left:left + 3] > 24)
            + np.count_nonzero(alpha8[top:bottom, right - 3:right] > 24)
            for left, top, right, bottom in windows
        )),
    }


def delta_layer(base, delta, support):
    """Recover a foreground color and alpha that reconstruct the color delta."""
    required_alpha = np.maximum(delta / (1 - base + 1e-6), -delta / (base + 1e-6)).max(axis=2)
    alpha = np.minimum(1, required_alpha * 1.17)
    color = np.clip(base + delta / np.maximum(alpha[..., None], 1e-6), 0, 1)
    alpha8 = np.rint(alpha * support * 255).astype(np.uint8)
    rgba = np.empty((*alpha.shape, 4), dtype=np.uint8)
    rgba[..., :3] = np.where(alpha8[..., None] > 0, np.rint(color * 255), 0).astype(np.uint8)
    rgba[..., 3] = alpha8
    return Image.fromarray(rgba, "RGBA")


def extract(args):
    carrier = Image.open(args.carrier).convert("RGBA")
    edited = Image.open(args.edited).convert("RGBA")
    if carrier.width % args.columns or carrier.height % args.rows:
        raise ValueError("Carrier does not divide evenly into the requested grid.")
    width, height = carrier.width // args.columns, carrier.height // args.rows
    windows = EYE_WINDOWS[args.body]
    if (width, height) != CELL_SIZE:
        raise ValueError("Each carrier cell must use the aligned 512 × 620 crop.")
    args.output.mkdir(parents=True, exist_ok=True)
    output = Image.new("RGBA", carrier.size)
    metadata = {
        "body": args.body,
        "grid": [args.columns, args.rows],
        "cell_size": [width, height],
        "edited_size": list(edited.size),
        "edited_background_alpha": background_report(edited, carrier),
        "pairs": [],
        "rejected": [],
    }
    for row in range(args.rows):
        for col in range(args.columns):
            x, y = col * width, row * height
            original = carrier.crop((x, y, x + width, y + height))
            silhouette = original.getchannel("A")
            edited_cell = edited.crop((
                round(col * edited.width / args.columns),
                round(row * edited.height / args.rows),
                round((col + 1) * edited.width / args.columns),
                round((row + 1) * edited.height / args.rows),
            )).resize((width, height), Image.Resampling.LANCZOS)
            try:
                aligned, registration = align_tile(original, edited_cell, windows)
                layer, bounds, quality = extract_layer(original, aligned, windows)
            except ValueError as error:
                metadata["rejected"].append({"cell": [col, row], "reason": str(error)})
            else:
                name = f"eyes-{row * args.columns + col + 1:02}.png"
                layer.save(args.output / name)
                original.alpha_composite(layer, bounds[:2])
                metadata["pairs"].append({
                    "file": name,
                    "cell": [col, row],
                    "offset": list(bounds[:2]),
                    "size": list(layer.size),
                    "registration": registration,
                    "quality": quality,
                })
            original.putalpha(silhouette)
            output.paste(original, (x, y))
    output = clean_alpha(output)
    metadata["reassembled_background_alpha"] = background_report(output, carrier)
    (args.output / "placements.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    output.save(args.output / "reassembled-transparent.png")
    preview = Image.new("RGBA", output.size, "#eee8dc")
    preview.alpha_composite(output)
    preview.convert("RGB").save(args.output / "reassembled.png")


def add_grid_args(parser):
    parser.add_argument("--body", choices=EYE_WINDOWS, required=True)
    parser.add_argument("--columns", type=int, default=2)
    parser.add_argument("--rows", type=int, default=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(required=True)
    command = subcommands.add_parser("prepare")
    add_grid_args(command)
    command.add_argument("--blank", type=Path, required=True)
    command.add_argument("--complete", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command.set_defaults(run=prepare)
    command = subcommands.add_parser("extract")
    add_grid_args(command)
    command.add_argument("--carrier", type=Path, required=True)
    command.add_argument("--edited", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command.set_defaults(run=extract)
    args = parser.parse_args()
    if args.columns < 1 or args.rows < 1:
        parser.error("Sheet dimensions must be positive.")
    args.run(args)


if __name__ == "__main__":
    main()
