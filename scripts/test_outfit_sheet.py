import unittest
from pathlib import Path
from runpy import run_path

from PIL import Image

contour_collar = run_path(str(Path(__file__).with_name("outfit-sheet.py")))[
    "contour_collar"
]


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
