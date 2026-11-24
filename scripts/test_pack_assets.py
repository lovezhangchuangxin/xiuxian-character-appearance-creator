import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from PIL import Image


class AssetArchiveTest(unittest.TestCase):
    def setUp(self):
        workdir = TemporaryDirectory()
        self.addCleanup(workdir.cleanup)
        self.root = Path(workdir.name)
        self.package = self.root / "packages/character-assets"
        self.script = self.root / "scripts/pack-assets.py"
        self.script.parent.mkdir()
        shutil.copyfile(Path(__file__).with_name("pack-assets.py"), self.script)

        image_path = "sprites/outfits/female/01.png"
        thumbnail_path = "thumbnails/outfits/female/01.webp"
        for path in (image_path, thumbnail_path):
            destination = self.root / "assets" / path
            destination.parent.mkdir(parents=True)
            Image.new("RGBA", (2, 2), "#932b31").save(destination)

        self.part = {
            "id": "01",
            "image": image_path,
            "thumbnail": thumbnail_path,
            "rect": {"x": 0, "y": 0, "width": 2, "height": 2},
        }
        self.manifest = {
            "packId": "test-assets",
            "packVersion": "1.0.0",
            "canvas": {"width": 4, "height": 4},
            "layers": ["outfit"],
            "bodies": {"female": {"parts": {"outfit": [self.part]}}},
        }
        (self.package / "dist").mkdir(parents=True)
        self.write_manifest()
        (self.package / "examples/references").mkdir(parents=True)
        (self.package / "examples/cases.json").write_text(
            json.dumps([{"id": "female", "body": "female", "parts": {"outfit": "01"}}]),
            encoding="utf-8",
        )

        for path in (
            "packages/character-assets/manifest.schema.json",
            "packages/character-assets/README.md",
            "packages/character-assets/examples/index.html",
            "LICENSE",
        ):
            (self.root / path).write_text("test fixture\n", encoding="utf-8")

        self.archive = self.root / "dist/test-assets-1.0.0.zip"
        refreshed = self.run_pack("--refresh-references")
        self.assertEqual(refreshed.returncode, 0, refreshed.stderr)

    def write_manifest(self):
        (self.package / "dist/manifest.json").write_text(
            json.dumps(self.manifest), encoding="utf-8"
        )

    def run_pack(self, *args):
        return subprocess.run(
            [sys.executable, str(self.script), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_repack_keeps_existing_zip_if_identical_and_rejects_changed_content(self):
        packed = self.run_pack()
        self.assertEqual(packed.returncode, 0, packed.stderr)
        original = self.archive.read_bytes()

        repeated = self.run_pack()
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(self.archive.read_bytes(), original)

        (self.package / "README.md").write_text("updated docs\n", encoding="utf-8")
        changed = self.run_pack()
        self.assertNotEqual(changed.returncode, 0)
        self.assertIn("already exists with different content", changed.stderr)
        self.assertEqual(self.archive.read_bytes(), original)

    def test_rejects_stale_reference_after_geometry_change_until_regenerated(self):
        self.part["rect"]["x"] = 1
        self.write_manifest()
        stale = self.run_pack()
        self.assertNotEqual(stale.returncode, 0)
        self.assertIn("Stale references: female. Run pnpm refs:assets.", stale.stderr)
        self.assertFalse(self.archive.exists())

        refreshed = self.run_pack("--refresh-references")
        self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
        packed = self.run_pack()
        self.assertEqual(packed.returncode, 0, packed.stderr)
        with ZipFile(self.archive) as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn("examples/references/female.png", archive.namelist())

    def test_rejects_undecodable_thumbnail(self):
        path = self.part["thumbnail"]
        (self.root / "assets" / path).write_bytes(b"not a WebP")
        packed = self.run_pack()
        self.assertNotEqual(packed.returncode, 0)
        self.assertIn(f"Cannot decode WebP: {path}", packed.stderr)
        self.assertFalse(self.archive.exists())
