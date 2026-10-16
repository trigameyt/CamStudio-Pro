import unittest
import numpy as np
from processor import ImageSettings, process_frame, viewport, source_point_from_output, output_content_bounds


class FramingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = np.full((90, 160, 3), (35, 100, 220), dtype=np.uint8)

    def test_rotation_90_no_stretch_and_black_bars(self):
        out = process_frame(self.src, ImageSettings(rotation=90), 160, 90)
        self.assertEqual(out.shape, (90, 160, 3))
        self.assertTrue(np.all(out[:, :45] == 0))
        self.assertGreater(out[:, 75].mean(), 30)
        self.assertTrue(np.all(out[:, 115:] == 0))

    def test_rotation_180_not_stretched(self):
        s = ImageSettings(rotation=180)
        out = process_frame(self.src, s, 160, 90)
        self.assertTrue(np.all(out[0, 0] == self.src[0, 0]))
        self.assertEqual(out.shape, self.src.shape)

    def test_fill_crops_not_stretches(self):
        s = ImageSettings(rotation=90, fit_mode='cover')
        out = process_frame(self.src, s, 160, 90)
        self.assertTrue(np.all(out[0, 0] == self.src[0, 0]))
        self.assertEqual(out.shape, (90, 160, 3))
        self.assertEqual(output_content_bounds(160, 90, s, 160, 90), (0, 0, 160, 90))

    def test_focus_moves_viewport(self):
        a = viewport(160, 90, ImageSettings(zoom=250, focus_x=.1))
        b = viewport(160, 90, ImageSettings(zoom=250, focus_x=.9))
        self.assertLess(a[0], b[0])
        self.assertEqual(a[2:], b[2:])

    def test_point_mapping_letterbox(self):
        s = ImageSettings(rotation=90, zoom=100)
        x, y = source_point_from_output(.5, .5, 160, 90, s, 160, 90)
        self.assertAlmostEqual(x, .5, delta=.02)
        self.assertAlmostEqual(y, .5, delta=.02)

    def test_zoom_pixel_sharpness(self):
        src=np.zeros((90,160,3),dtype=np.uint8)
        src[40:50,75:85]=[255,255,255]
        s=ImageSettings(zoom=300,fit_mode='cover',focus_x=.5,focus_y=.5)
        out=process_frame(src,s,160,90)
        self.assertGreater(float(out[45,80].mean()),200)
        s.focus_x=.85
        right=process_frame(src,s,160,90)
        self.assertLess(float(right[45,80].mean()),20)

if __name__=='__main__': unittest.main()
