"""Install every cell of a registered 4 × 4 facial sheet in source order."""

import argparse
import json
from pathlib import Path
from shutil import copy2, rmtree

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "src/character/numbered-faces.json"


def read_batch(folder):
    report = json.loads((folder / "placements.json").read_text(encoding="utf-8"))
    body, part = report["body"], report["part"]
    if body not in ("male", "female") or part not in (
        "brows",
        "eyes",
        "noses",
        "mouths",
    ):
        raise ValueError(f"Unsupported batch: {body}/{part}")

    variants = sorted(report["variants"], key=lambda entry: entry["index"])
    if report["grid"] != 4 or [variant["index"] for variant in variants] != list(
        range(1, 17)
    ):
        raise ValueError(f"The batch must contain all 16 cells: {folder}")
    if report["reassembled_background_alpha"]["max_alpha"] != 0:
        raise ValueError(f"Nontransparent background in {folder}")

    destination = ROOT / "assets/sprites/faces" / body / part
    files = []
    offsets = []
    for variant in variants:
        filename = variant["file"]
        if Path(filename).name != filename:
            raise ValueError(f"Expected a sprite filename: {filename}")
        source = folder / filename
        x, y = variant["offset"]
        with Image.open(source) as sprite:
            if (
                sprite.format != "PNG"
                or sprite.mode != "RGBA"
                or sprite.getchannel("A").getextrema()[1] == 0
            ):
                raise ValueError(f"Expected a nonempty RGBA PNG: {source}")
            if (
                type(x) is not int
                or type(y) is not int
                or x < 0
                or y < 0
                or x + sprite.width > 512
                or y + sprite.height > 620
            ):
                raise ValueError(f"Invalid head placement: {source}")
        files.append((source, destination / f"{variant['index']:02}.png"))
        offsets.append([x, y])
    return body, part, files, offsets


def install_batches(folders):
    work = ROOT / ".feature-batch-install"
    try:
        work.mkdir()
    except FileExistsError as error:
        raise RuntimeError(
            f"A facial batch installation is active or needs recovery: {work}"
        ) from error

    recovery_required = False
    try:
        catalog = (
            json.loads(CATALOG.read_text(encoding="utf-8")) if CATALOG.is_file() else {}
        )
        files = {}
        for folder in folders:
            body, part, sprites, offsets = read_batch(folder)
            files.update((target, source) for source, target in sprites)
            catalog.setdefault(body, {})[part] = offsets
        manifest = work / "catalog.json"
        manifest.write_text(
            json.dumps(catalog, separators=(",", ":")) + "\n", encoding="utf-8"
        )
        files[CATALOG] = manifest

        staged = []
        for index, (target, source) in enumerate(files.items()):
            incoming = work / f"incoming-{index}"
            copy2(source, incoming)
            backup = None
            if target.exists():
                backup = work / "backup" / target.relative_to(ROOT)
                backup.parent.mkdir(parents=True, exist_ok=True)
                copy2(target, backup)
            staged.append((incoming, target, backup))

        attempted = []
        try:
            for incoming, target, backup in staged:
                target.parent.mkdir(parents=True, exist_ok=True)
                attempted.append((target, backup))
                incoming.replace(target)
        except BaseException:
            try:
                for target, backup in reversed(attempted):
                    if backup is None:
                        target.unlink(missing_ok=True)
                    else:
                        backup.replace(target)
            except BaseException as error:
                recovery_required = True
                raise RuntimeError(
                    f"Batch rollback failed. Remaining backups are in {work}"
                ) from error
            raise
    finally:
        if not recovery_required:
            rmtree(work)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batches", type=Path, nargs="+")
    args = parser.parse_args()
    install_batches(args.batches)


if __name__ == "__main__":
    main()
