"""PC 공용 LaMa(%LOCALAPPDATA%/lama/lama_inpaint.py, big-lama.pt) 연결. inpaint(rgb_uint8, mask_bool_or_uint8) → rgb_uint8"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.environ.get('LOCALAPPDATA', ''), 'lama'))
import lama_inpaint as _L   # noqa: E402


def inpaint(rgb, mask):
    m = (np.asarray(mask) > 0).astype(np.uint8) * 255
    return _L.inpaint(np.ascontiguousarray(rgb[..., :3]).astype(np.uint8), m)
