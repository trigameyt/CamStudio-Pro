import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import unittest
import numpy as np
from processor import ImageSettings, PRESETS, process_frame

class ProcessorTests(unittest.TestCase):
    def test_all_presets(self):
        src = np.zeros((24,32,3),np.uint8); src[:,:,2]=140
        for p in PRESETS.values():
            out=process_frame(src,p,320,180)
            self.assertEqual(out.shape,(180,320,3))
            self.assertEqual(out.dtype,np.uint8)
    def test_rotation_and_mirror(self):
        src=np.random.default_rng(1).integers(0,256,(120,160,3), dtype=np.uint8)
        out=process_frame(src,ImageSettings(rotation=90,mirror=True),320,180)
        self.assertEqual(out.shape,(180,320,3))
    def test_zoom_and_grid(self):
        src=np.zeros((70,70,3),np.uint8)
        out=process_frame(src,ImageSettings(zoom=300,show_grid=True),210,150)
        self.assertGreater(int(out.sum()),0)

if __name__=='__main__': unittest.main()
