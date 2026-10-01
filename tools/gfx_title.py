"""타이틀 화면 g123(B안, 10/2 사용자 결정): 일본판 배경 + 북미판 로고 + 배경에 박힌 메뉴 글씨를 한글로.
게임은 일본판 자리에 강조 그림(g124 시작하기·g129 불러오기·g130 옵션)을 덮어 그리므로,
배경 글씨는 강조 그림의 한글과 똑같은 모양·자리(강조 그림 원점 = 일본어 글씨 위치로 찾은 값)에 어둡게 쓴다.
python gfx_title.py"""
import os, sys
import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lama import inpaint

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, 'work', 'gfx')
LOGO = (400, 18, 722, 192)                    # x0, y0, x1, y1 — 일본판·북미판 로고 차이(+여유)
MENU = (530, 250, 712, 384)                   # 배경 메뉴 글씨 영역
SPRITES = {'g124': (541, 243), 'g129': (532, 279), 'g130': (549, 313)}   # 강조 그림 원점(일본어 글씨 맞춤으로 찾음)
BAKED = np.array((78, 101, 106), np.float32)  # 원본 배경 글씨 색(측정)


def main():
    jp = np.asarray(Image.open(os.path.join(G, 'src', 'g123_jp.png')).convert('RGB')).copy()
    w = np.asarray(Image.open(os.path.join(G, 'src', 'g123_w.png')).convert('RGB'))
    x0, y0, x1, y1 = LOGO
    jp[y0:y1, x0:x1] = w[y0:y1, x0:x1]
    mx0, my0, mx1, my1 = MENU
    L = jp.astype(int).mean(2)
    m = np.zeros(L.shape, np.uint8)
    m[my0:my1, mx0:mx1] = (L[my0:my1, mx0:mx1] > 22)
    m = cv2.dilate(m, np.ones((7, 7), np.uint8))
    er = inpaint(jp, m)
    Image.fromarray(er).save(os.path.join(G, 'done', 'g123_erased.png'))
    o = er.astype(np.float32)
    for g, (ox, oy) in SPRITES.items():
        sp = np.asarray(Image.open(os.path.join(G, 'done', g + '.png')).convert('RGB')).astype(np.float32).mean(2)
        a = np.clip((sp - 150) / 80, 0, 1)                       # 강조 그림의 글자 획(빛 제외)
        soft = cv2.GaussianBlur(a, (0, 0), 0.6)
        h, ww = a.shape
        reg = o[oy:oy + h, ox:ox + ww]
        reg[:] = reg * (1 - soft[..., None]) + BAKED * soft[..., None]
    out = np.dstack([np.clip(o, 0, 255).astype(np.uint8), np.full(L.shape, 255, np.uint8)])
    Image.fromarray(out, 'RGBA').save(os.path.join(G, 'done', 'g123.png'))
    print('완료')


if __name__ == '__main__':
    main()
