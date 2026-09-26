from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from PIL import Image
from django.test import SimpleTestCase

from .expose_pdf import _image_bytes


class ExposeImageScalingTests(SimpleTestCase):
    def test_scaling_keeps_contain_bounds_and_aspect_ratio(self):
        with TemporaryDirectory() as directory:
            for name, size in (("landscape", (1600, 900)), ("portrait", (900, 1600)), ("square", (1000, 1000))):
                path = Path(directory) / f"{name}.png"
                Image.new("RGB", size, "white").save(path)
                scaled, data = _image_bytes(SimpleNamespace(path=str(path)), 487, 220)
                self.assertIsNotNone(data)
                self.assertLessEqual(scaled[0], 487)
                self.assertLessEqual(scaled[1], 220)
                self.assertAlmostEqual(scaled[0] / scaled[1], size[0] / size[1], places=2)

    def test_unreadable_image_is_skipped(self):
        scaled, data = _image_bytes(SimpleNamespace(path="/tmp/does-not-exist.jpg"), 487, 220)
        self.assertIsNone(scaled)
        self.assertIsNone(data)
