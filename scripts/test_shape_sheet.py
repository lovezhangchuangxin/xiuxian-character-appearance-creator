import unittest
from pathlib import Path
from runpy import run_path
from unittest.mock import Mock, patch

from PIL import Image, ImageDraw

shape_sheet = run_path(str(Path(__file__).with_name("shape-sheet.py")))
extend_neck = shape_sheet["extend_neck"]
register = shape_sheet["register"]


class NeckHighlightsTest(unittest.TestCase):
    def test_extending_the_neck_softens_highlights_without_changing_the_head(self):
        art = Image.new("RGBA", (512, 620))
        drawing = ImageDraw.Draw(art)
        drawing.rectangle((172, 375, 340, 619), fill=(210, 160, 130, 255))
        drawing.rectangle((201, 547, 207, 566), fill=(250, 222, 200, 255))

        result = extend_neck(art, 547, 567, 531)

        self.assertEqual(
            result.crop((0, 0, 512, 539)).tobytes(),
            art.crop((0, 0, 512, 539)).tobytes(),
        )
        region = (0, 539, 512, 567)
        self.assertEqual(
            result.getchannel("A").crop(region).tobytes(),
            art.getchannel("A").crop(region).tobytes(),
        )
        self.assertLess(result.getpixel((204, 565))[0], art.getpixel((204, 565))[0])
        self.assertEqual(result.getpixel((204, 567)), result.getpixel((204, 566)))

    def test_centre_keeps_one_jaw_line_across_short_and_long_chins(self):
        skin = (241, 190, 166, 255)
        outline = (81, 47, 35, 255)
        master = Image.new("RGBA", (512, 620), skin)
        ImageDraw.Draw(master).line((201, 548, 307, 548), fill=outline, width=3)

        for row in (533, 578):
            with self.subTest(row=row):
                edited = Image.new("RGBA", (512, 620), skin)
                ImageDraw.Draw(edited).line((201, row, 307, row), fill=outline, width=3)
                with patch.dict(
                    register.__globals__,
                    {"align_tile": Mock(return_value=(edited, None))},
                ):
                    shaped, _, join, jaw = register(master, edited, 559)
                result = extend_neck(shaped, 559, join, jaw)

                self.assertEqual(result.getpixel((256, row)), outline)
                self.assertEqual(result.getpixel((256, 548)), skin)
                self.assertGreater(join, row + 4)

    def test_jaw_shadow_fades_after_the_contour_has_blended(self):
        skin = (241, 190, 166, 255)
        shadow = (211, 154, 133, 255)
        outline = (81, 47, 35, 255)
        master = Image.new("RGBA", (512, 620), skin)
        ImageDraw.Draw(master).line((201, 528, 307, 528), fill=outline, width=3)
        edited = Image.new("RGBA", (512, 620), skin)
        draw = ImageDraw.Draw(edited)
        draw.rectangle((205, 534, 304, 568), fill=shadow)
        draw.line((201, 531, 307, 531), fill=outline, width=3)

        with patch.dict(
            register.__globals__, {"align_tile": Mock(return_value=(edited, None))}
        ):
            shaped, _, _, _ = register(master, edited, 547)

        self.assertEqual(shaped.getpixel((256, 531)), outline)
        self.assertGreater(shaped.getpixel((256, 553))[0], shadow[0])
        self.assertLess(shaped.getpixel((256, 553))[0], skin[0])
        self.assertEqual(shaped.getpixel((256, 567)), skin)
        self.assertEqual(
            shaped.getchannel("A").tobytes(), master.getchannel("A").tobytes()
        )
