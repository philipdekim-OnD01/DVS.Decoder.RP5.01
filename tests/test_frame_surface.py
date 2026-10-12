import unittest
import numpy as np
from frame_surface import FrameSurface, W, H

def options(**changes):
    values = {'Display mode': 'Time Surface', 'Time Surface τ (ms)': 25,
              'Event lifetime (ms)': 60, 'Accumulation (ms)': 35, 'Point size': 1,
              'Contrast / gain (%)': 100, 'Sub-sampling': '1', 'Polarity': 'ON + OFF',
              'Hot pixel filter': False, 'Hot pixel active frames/s': 20,
              'Noise filter': False, 'Dilation': False, 'Flip X': False, 'Flip Y': False,
              'roi': (0, W-1, 0, H-1), 'colors': {name: np.array(color, np.float32)
               for name, color in {'ON': (255,255,255), 'OFF': (0,191,255), 'BG': (0,0,0)}.items()}}
    values.update(changes); return values

class SurfaceTests(unittest.TestCase):
    def test_polarity_roi_flip_and_unassigned(self):
        raw = np.zeros(W*H, np.uint8); raw[20*W+30] = 255
        raw[20*W+31] = 64; raw[20*W+32] = 128
        surface = FrameSurface(); opt = options()
        surface.accept(raw, 1, opt); rgb = surface.render(1, opt)
        self.assertEqual(tuple(rgb[20,30]), (255,255,255))
        self.assertEqual(tuple(rgb[20,31]), (0,191,255))
        self.assertFalse(rgb[20,32].any())
        opt['Polarity'] = 'ON only'; self.assertFalse(surface.render(1,opt)[20,31].any())
        opt['Flip X'] = opt['Flip Y'] = True
        self.assertTrue((surface.render(1,opt)[H-21,W-31] == 255).all())
        opt['roi'] = (100,200,100,200); self.assertFalse(surface.render(1,opt).any())

    def test_short_decay_and_no_repeat_refresh(self):
        raw = np.zeros(W*H,np.uint8); raw[50*W+50] = 255
        surface=FrameSurface(); opt=options(); surface.accept(raw,1,opt)
        self.assertTrue(80 < int(surface.render(1.025,opt)[50,50,0]) < 100)
        self.assertFalse(surface.render(1.080,opt).any())

    def test_temporal_neighbor_preserves_thin_edges(self):
        surface=FrameSurface(); opt=options(**{'Noise filter':True})
        raw=np.zeros(W*H,np.uint8); raw[20*W+20]=255
        surface.accept(raw,1,opt); self.assertFalse(surface.render(1,opt).any())
        raw.fill(0); raw[20*W+21]=64
        surface.accept(raw,1.02,opt); self.assertTrue(surface.render(1.02,opt)[20,21].any())
        raw.fill(0); raw[20*W+40]=255
        surface.accept(raw,1.03,opt); self.assertFalse(surface.render(1.03,opt)[20,40].any())

    def test_dilation_does_not_mutate_event_history(self):
        raw=np.zeros(W*H,np.uint8); raw[20*W+20]=255
        surface=FrameSurface(); opt=options(**{'Dilation':True})
        surface.accept(raw,1,opt); before=surface.timestamps.copy()
        self.assertTrue((surface.render(1,opt)[20:23,20:23] == 255).all())
        np.testing.assert_array_equal(surface.timestamps,before)

    def test_hot_pixel_counts_input_frames_only(self):
        raw=np.zeros(W*H,np.uint8); raw[20*W+20]=255
        surface=FrameSurface(); opt=options(**{'Hot pixel filter':True, 'Hot pixel active frames/s':2})
        for t in (1,1.2,1.4,1.6,2.1): surface.accept(raw,t,opt)
        self.assertTrue(surface.hot_mask[20*W+20])
        self.assertFalse(surface.render(2.1,opt).any())

if __name__ == '__main__': unittest.main()
