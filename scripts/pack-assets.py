"""Build a versioned asset archive or regenerate its example reference images."""

import argparse
import json
from hashlib import sha256
from io import BytesIO
from math import ceil
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "packages/character-assets"
EXAMPLES = PACKAGE / "examples"
REFERENCE_SIGNATURES = EXAMPLES / "references.json"


def reference_inputs(manifest, example):
    part_options = manifest["bodies"][example["body"]]["parts"]
    if set(example["parts"]) != set(part_options):
        raise ValueError(f"Invalid example selection {example['id']}")

    layers = []
    for slot in manifest["layers"]:
        choice = next(
            (
                part
                for part in part_options[slot]
                if part["id"] == example["parts"][slot]
            ),
            None,
        )
        if choice is None:
            raise ValueError(f"Invalid example selection {example['id']}: {slot}")
        if choice["image"] is not None:
            layer = {"image": choice["image"], "rect": choice["rect"]}
            if "clip" in choice:
                layer["clip"] = choice["clip"]
            layers.append(layer)
    return {"canvas": manifest["canvas"], "layers": layers}


def render_reference(inputs, images):
    size = (inputs["canvas"]["width"], inputs["canvas"]["height"])
    result = Image.new("RGBA", size)
    for layer in inputs["layers"]:
        rect = layer["rect"]
        with Image.open(BytesIO(images[layer["image"]]), formats=["PNG"]) as sprite:
            sx = sprite.width / rect["width"]
            sy = sprite.height / rect["height"]
            image = sprite.convert("RGBA").transform(
                size,
                Image.Transform.AFFINE,
                (sx, 0, -rect["x"] * sx, 0, sy, -rect["y"] * sy),
                resample=Image.Resampling.BILINEAR,
            )
        if "clip" in layer:
            clip = layer["clip"]
            left = max(0, ceil(clip["x"] - 0.5))
            top = max(0, ceil(clip["y"] - 0.5))
            right = min(size[0], ceil(clip["x"] + clip["width"] - 0.5))
            bottom = min(size[1], ceil(clip["y"] + clip["height"] - 0.5))
            if left < right and top < bottom:
                result.alpha_composite(
                    image.crop((left, top, right, bottom)), (left, top)
                )
        else:
            result.alpha_composite(image)
    return result


def reference_signature(inputs, images, reference):
    geometry = json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()
    digest = sha256(geometry)
    for layer in inputs["layers"]:
        digest.update(sha256(images[layer["image"]]).digest())
    digest.update(sha256(reference).digest())
    return digest.hexdigest()


def example_files(manifest, examples, images, refresh):
    previous = (
        {} if refresh else json.loads(REFERENCE_SIGNATURES.read_text(encoding="utf-8"))
    )
    signatures = {}
    references = {}
    for example in examples:
        name = example["id"]
        if name in signatures:
            raise ValueError(f"Duplicate example {name}")
        inputs = reference_inputs(manifest, example)
        path = EXAMPLES / "references" / f"{name}.png"
        if refresh:
            output = BytesIO()
            render_reference(inputs, images).save(output, format="PNG")
            content = output.getvalue()
        elif path.is_file():
            content = path.read_bytes()
        else:
            raise ValueError(f"Missing reference {name}. Run pnpm refs:assets.")
        signatures[name] = reference_signature(inputs, images, content)
        relative_path = f"examples/references/{name}.png"
        references[relative_path] = content
        example.update(
            packId=manifest["packId"],
            packVersion=manifest["packVersion"],
            reference=relative_path,
        )
    if refresh:
        for path, content in references.items():
            (PACKAGE / path).write_bytes(content)
        REFERENCE_SIGNATURES.write_text(
            json.dumps(signatures, indent=2) + "\n", encoding="utf-8"
        )
    elif previous != signatures:
        changed = sorted(
            name
            for name in previous.keys() | signatures.keys()
            if previous.get(name) != signatures.get(name)
        )
        raise ValueError(
            f"Stale references: {', '.join(changed)}. Run pnpm refs:assets."
        )
    return references


def publish_archive(archive_path, destination):
    try:
        destination.hardlink_to(archive_path)
    except FileExistsError:
        with ZipFile(archive_path) as candidate, ZipFile(destination) as current:
            paths = candidate.namelist()
            if sorted(paths) != sorted(current.namelist()) or any(
                candidate.read(path) != current.read(path) for path in paths
            ):
                raise ValueError(
                    f"{destination.name} already exists with different content. "
                    "Bump the asset package version before releasing new content."
                ) from None


def main(refresh):
    manifest_bytes = (PACKAGE / "dist/manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    examples = json.loads((EXAMPLES / "cases.json").read_text(encoding="utf-8"))

    images = set()
    for body in manifest["bodies"].values():
        for choices in body["parts"].values():
            images.update(
                part[key]
                for part in choices
                for key in ("image", "thumbnail")
                if part.get(key)
            )

    image_bytes = {}
    for path in sorted(images):
        content = (ROOT / "assets" / path).read_bytes()
        if path.startswith("thumbnails/"):
            try:
                with Image.open(BytesIO(content), formats=["WEBP"]) as thumbnail:
                    thumbnail.load()
            except OSError as exc:
                raise ValueError(f"Cannot decode WebP: {path}") from exc
        image_bytes[path] = content

    references = example_files(manifest, examples, image_bytes, refresh)
    if refresh:
        print(f"Refreshed {len(references)} reference images.")
        return

    files = {
        "manifest.schema.json": PACKAGE / "manifest.schema.json",
        "README.md": PACKAGE / "README.md",
        "LICENSE": ROOT / "LICENSE",
        "examples/index.html": EXAMPLES / "index.html",
    }
    contents = {path: source.read_bytes() for path, source in files.items()}
    contents.update(image_bytes)
    contents.update(references)
    contents["manifest.json"] = manifest_bytes
    contents["examples/appearances.json"] = (
        json.dumps(examples, ensure_ascii=False, indent=2) + "\n"
    ).encode()

    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    destination = dist / f"{manifest['packId']}-{manifest['packVersion']}.zip"
    with TemporaryDirectory(dir=dist) as temp:
        archive_path = Path(temp) / destination.name
        with ZipFile(archive_path, "w") as archive:
            for path, content in sorted(contents.items()):
                archive.writestr(ZipInfo(path), content, ZIP_DEFLATED)
        publish_archive(archive_path, destination)

    print(
        f"Packed {len(images)} runtime images and {len(examples)} examples to {destination}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-references", action="store_true")
    try:
        main(parser.parse_args().refresh_references)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")
