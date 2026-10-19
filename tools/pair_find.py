"""선택 글씨(밝은 획) ↔ 배경 판의 평상시 글씨(어두운 획) 자리 찾기(10/20, 일본판 기준).
두 그림 모두 글자 획만 0/1로 뽑아(선택 글씨 = 밝은 심, 배경 = 주변보다 어두운 잉크) 겹치는 정도(정규화 상관)가 가장 큰 자리를 찾는다.
python tools/pair_find.py   → 표 출력(사람이 확인해서 gpt_pairs 설정에 씀)
"""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.signal import fftconvolve

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, 'work', 'gfx')


def rgba(i, kind='src'):
    p = os.path.join(G, 'src', i + '_jp.png') if kind == 'src' else os.path.join(G, 'done', i + '.png')
    return np.asarray(Image.open(p).convert('RGBA')).astype(np.float32)


def thin(im, dark):
    """가는 글자 획만(검은 글씨: 닫힘-밝기, 밝은 글씨: 밝기-열림), 0~1."""
    from scipy.ndimage import grey_closing, grey_opening
    L = gaussian_filter(im[..., :3].mean(2), 0.5) * (im[..., 3] / 255)
    t = (grey_closing(L, size=(7, 7)) - L) if dark else (L - grey_opening(L, size=(7, 7)))
    t = np.clip(t, 0, None)
    hi = np.percentile(t[t > 4], 97) if (t > 4).sum() > 20 else 1
    return np.clip(t / max(hi, 1), 0, 1)


def find(hl, bg, dark=True):
    H = thin(rgba(hl), dark=False)
    B = thin(rgba(bg), dark=dark)
    num = np.clip(fftconvolve(B, H[::-1, ::-1], 'valid'), 0, None)
    den = np.sqrt(np.clip(fftconvolve(B * B, np.ones_like(H), 'valid'), 1e-6, None) * (H * H).sum())
    sc = num / den
    y, x = np.unravel_index(np.argmax(sc), sc.shape)
    return int(x), int(y), round(float(sc[y, x]), 3)


PAIRS = {  # 선택 글씨: 배경 판
    'g061': 'g060', 'g059': 'g048', 'g052': 'g049', 'g053': 'g049',
    'g068': 'g054', 'g055': 'g054', 'g056': 'g054',
    'g081': 'g082', 'g087': 'g082', 'g086': 'g082', 'g088': 'g084', 'g089': 'g085',
    'g072': 'g037', 'g071': 'g037', 'g035': 'g037',
}

LIGHT = {'g082', 'g084', 'g085', 'g037'}   # 회색(밝은) 새김 글씨 판

if __name__ == '__main__':
    for h, b in PAIRS.items():
        print(h, '→', b, find(h, b, dark=b not in LIGHT))
