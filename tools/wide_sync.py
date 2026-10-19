"""16:9 인벤토리 그림을 새 4:3 그림에서 만들고, 빛나는 선택 글씨의 몇 픽셀 어긋남을 바로잡는다(10/20, 사용자 화면 확인).

일본판 확인(10/20)
  - 16:9 배경 g108(JWideInJ 305x465)·g110(JWideInv 320x480) = 4:3 배경 g082(419x465)를 그 크기로 줄인 그림(늘려 비교하면 평균 차이 4, 이동 0).
  - JWideInJ 의 노란 글씨·조합/모드 판은 4:3(JBookInJ)와 같은 데이터.
  - JWideInv 의 노란 글씨(64x32)는 4:3 노란 글씨를 같은 크기로 (dx, dy) 만큼 옮겨 자른 것, 조합·모드 판(g111·g112)은 4:3 판(g084·g085)을 그대로 자른 것.
  - 사용자 화면(4:3·16:9 모두)에서 자막 「한국어」·「모노」가 어긋남 → GPT 결과의 위 칸(판)·아래 칸(선택 글씨) 자리가 1~2px 다름.
    일본판은 모두 (0, 0)에서 겹침. 한글판 어긋남만큼 선택 글씨를 옮긴다(HL_SHIFT, tools/pair_find 가는 획 상관으로 잼).
python tools/wide_sync.py [--check]
"""
import os
import shutil
import sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, 'work', 'gfx', 'done')
BAK = os.path.join(ROOT, 'work', 'GPT', '이전')

WIDE_BG = {'g108': (305, 465), 'g110': (320, 480)}
WIDE_HL = {'g109': ('g081', 4, 1), 'g114': ('g087', 7, 1), 'g113': ('g086', 5, 1),
           'g115': ('g088', 4, 1), 'g116': ('g089', 4, 1)}           # 16:9 글씨 = 4:3 글씨[dy:, dx:] 의 64x32
WIDE_PLATE = {'g111': ('g084', 85), 'g112': ('g085', 88)}            # 4:3 판을 폭만 잘라서
HL_SHIFT = {}   # 10/20 사용자 결정: GPT 원래 자리 유지(한글은 획이 복잡해 옮기면 오히려 어긋남). 예전 값: g061 (-2,-1) g059 (2,1) g052 (2,1) g053 (2,-1) g068 (2,1) g055 (2,1) g056 (-2,2)


def load(i):
    return np.asarray(Image.open(os.path.join(G, i + '.png')).convert('RGBA'))


def save(i, a):
    p = os.path.join(G, i + '.png')
    b = os.path.join(BAK, i + '_와이드이전.png')
    if not os.path.exists(b):
        shutil.copy2(p, b)
    Image.fromarray(a, 'RGBA').save(p)


def crop(a, dx, dy, w, h):
    out = np.zeros((h, w, 4), np.uint8)
    src = a[dy:dy + h, dx:dx + w]
    out[:src.shape[0], :src.shape[1]] = src
    return out


def shift(a, dx, dy, black):
    h, w = a.shape[:2]
    out = np.zeros_like(a)
    if black:
        out[..., 3] = 255
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    out[yd, xd] = a[ys, xs]
    return out


def main():
    os.makedirs(BAK, exist_ok=True)
    # 1) 빛나는 선택 글씨 어긋남(먼저 해야 아래 16:9 글씨와 무관 — 16:9 는 노란 글씨만)
    for i, (dx, dy) in HL_SHIFT.items():
        save(i, shift(load(i), dx, dy, black=True))
        print('옮김', i, (dx, dy))
    # 2) 16:9 배경
    g082 = Image.open(os.path.join(G, 'g082.png')).convert('RGBA')
    for i, (w, h) in WIDE_BG.items():
        save(i, np.asarray(g082.resize((w, h), Image.LANCZOS)))
        print('16:9 배경', i, (w, h))
    # 3) 16:9 노란 글씨·판
    for i, (n, dx, dy) in WIDE_HL.items():
        save(i, crop(load(n), dx, dy, 64, 32))
        print('16:9 글씨', i, '←', n, (dx, dy))
    for i, (n, w) in WIDE_PLATE.items():
        a = load(n)
        save(i, crop(a, 0, 0, w, a.shape[0]))
        print('16:9 판', i, '←', n)


if __name__ == '__main__':
    main()
