"""작은 질감 바탕 슬롯 이름(g165 슬롯 A, g166 슬롯 B): gfx_pick2로 바탕을 되살리고 어두운 글자 + 청록 빛을 원본 색으로 쓴다.
python gfx_slotsmall.py g165 g166"""
import os, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gfx_pick2 import lama_fill

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, 'work', 'gfx')
FONT = os.path.join(ROOT, 'work', 'fonts', 'YeoncheonHeomok.ttf')
CFG = {'g165': {'text': '슬롯 A', 'size': 19}, 'g166': {'text': '슬롯 B', 'size': 19}}


def make(gid, c):
    j8 = np.array(Image.open(os.path.join(G, 'src', gid + '_jp.png')).convert('RGBA'))
    e8 = np.array(Image.open(os.path.join(G, 'src', gid + '_e.png')).convert('RGBA'))
    jr, er = np.ascontiguousarray(j8[..., :3]), np.ascontiguousarray(e8[..., :3])
    out, _ = lama_fill(jr, er)   # 10/2 LaMa(전엔 두 판 고르기)
    Image.fromarray(np.dstack([out, j8[..., 3]]), 'RGBA').save(os.path.join(G, 'done', gid + '_erased.png'))
    L = jr.astype(int).mean(2)
    glc = np.median(jr[L >= np.percentile(L, 95)], 0)          # 원본 빛(밝은 쪽)
    d = np.abs(jr.astype(int) - er.astype(int)).sum(2) > 30
    ys, xs = np.where(d)
    cx, cy = (xs.min() + xs.max() + 1) / 2, (ys.min() + ys.max() + 1) / 2
    inkc = np.median(jr[d & (L < np.percentile(L[d], 12))], 0)   # 원본 글자 획(어두운 쪽)
    H, W = L.shape
    t = Image.new('L', (W, H), 0)
    ImageDraw.Draw(t).text((cx, cy), c['text'], font=ImageFont.truetype(FONT, c['size']), fill=255, anchor='mm')
    m = np.asarray(t).astype(np.float32) / 255
    m = np.maximum(m, np.roll(m, 1, 1))
    gl = np.clip(cv2.GaussianBlur(cv2.dilate(m, np.ones((5, 5), np.uint8)), (0, 0), 1.8) * 1.2, 0, 1)[..., None] * 0.9
    o = out.astype(np.float32) * (1 - gl) + glc * gl
    o = o * (1 - m[..., None]) + inkc * m[..., None]
    Image.fromarray(np.dstack([np.clip(o, 0, 255).astype(np.uint8), j8[..., 3]]), 'RGBA').save(os.path.join(G, 'done', gid + '.png'))
    print(gid, '빛 색', glc.astype(int), '글자색', inkc.astype(int), '가운데', cx, cy)


if __name__ == '__main__':
    for g in sys.argv[1:]:
        make(g, CFG[g])
