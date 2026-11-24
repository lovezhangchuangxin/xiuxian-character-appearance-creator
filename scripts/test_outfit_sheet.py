import unittest
from pathlib import Path
from runpy import run_path

from PIL import Image

outfit_sheet = run_path(str(Path(__file__).with_name("outfit-sheet.py")))
contour_collar = outfit_sheet["contour_collar"]
redraw_collar = outfit_sheet["redraw_collar"]


class CollarContourTest(unittest.TestCase):
    def test_closed_collar_samples_transparency_along_fractional_edge(self):
        cloth = (88, 76, 64, 255)
        art = Image.new("RGBA", (96, 96), cloth)

        collar = contour_collar(art, 48)

        self.assertEqual(collar.getpixel((48, 0)), (0, 0, 0, 0))
        self.assertGreater(sum(collar.getchannel("A").histogram()[1:-1]), 0)
        self.assertEqual(collar.getpixel((48, 30)), cloth)

    def test_open_collar_keeps_original_pixels(self):
        art = Image.new("RGBA", (96, 96))
        art.paste((88, 76, 64, 255), (0, 25, 96, 96))

        self.assertEqual(contour_collar(art.copy(), 48).tobytes(), art.tobytes())

    def test_redrawn_opening_preserves_the_lapels_and_cloth_below(self):
        cloth = (88, 76, 64, 255)
        art = Image.new("RGBA", (96, 96), cloth)
        opening = [(25, 10), (25, 28), (48, 56), (70, 28), (70, 10)]

        opened = redraw_collar(art.copy(), opening, "open")
        inner = redraw_collar(art.copy(), opening, "inner")

        for fitted in (opened, inner):
            self.assertEqual(fitted.getpixel((48, 30))[3], 0)
            self.assertEqual(fitted.getpixel((12, 32)), cloth)
            self.assertEqual(fitted.getpixel((48, 64)), cloth)
            self.assertGreater(sum(fitted.getchannel("A").histogram()[1:-1]), 0)
        self.assertEqual(
            opened.getchannel("A").tobytes(), inner.getchannel("A").tobytes()
        )
        self.assertNotEqual(opened.tobytes(), inner.tobytes())
