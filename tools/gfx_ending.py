"""엔딩 g125(To be Continued 화면): 아래쪽 일본어 세 줄을 지우고 한글 세 줄(송명)을 쓴다.
지우기: 같은 그림의 영어판은 같은 띠에 영어 글자가 있다 → 픽셀마다 일본판·영어판 중 글자 기운(주변 중앙값과의 차)이 적은 쪽을 고르고,
둘 다 글자인 곳만 인페인팅. 띠 밖은 일본판 그대로(제목만 영어판 '...'로, 일본판은 ',,,' 오기).
python gfx_ending.py"""
import os
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lama import inpaint as lama

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, 'work', 'gfx')
FONT = os.path.join(ROOT, 'work', 'fonts', 'SongMyung-Regular.ttf')
LINES = ['이번 전투에서는 이겼다.', '하지만 어둠과의 전쟁은', '아직 끝나려면 멀었다…']
BASES = [336, 364, 392]        # 글줄 기준선(10/1 행간 28px로 고르게, 가운데 줄은 원본 자리)
CX = 320
SIZE = 21
INK = (24, 28, 49)             # 원본 글자 속(검은 남보라, 10/1 사용자 지적으로 변경)
EDGE = (70, 60, 95)            # 글자 바로 둘레 어두운 테두리
GLOW = (156, 149, 189)         # 글자 바로 둘레 밝은 보랏빛(원본 측정)
BAND = (300, 410, 120, 540)    # y0, y1, x0, x1
TITLE = (60, 160, 130, 560)    # 제목 띠(영어판 '...' 가져옴)


def textness(a8):
    med = cv2.medianBlur(a8, 9).astype(np.float32)
    return cv2.GaussianBlur(np.abs(a8.astype(np.float32) - med).sum(2), (0, 0), 1.5)


def main():
    j8 = np.array(Image.open(os.path.join(G, 'src', 'g125_jp.png')).convert('RGBA'))
    e8 = np.array(Image.open(os.path.join(G, 'src', 'g125_e.png')).convert('RGBA'))
    jr, er = np.ascontiguousarray(j8[..., :3]), np.ascontiguousarray(e8[..., :3])
    out = jr.copy()
    y0, y1, x0, x1 = BAND
    band = np.zeros(jr.shape[:2], bool); band[y0:y1, x0:x1] = True
    # 두 판 모두 글자 둘레 빛 번짐이 띠를 거의 덮음 → 두 판이 다른 곳(=어느 쪽이든 글자·번짐)을 넓게 잡아 통째로 메움
    d = np.abs(jr.astype(int) - er.astype(int)).sum(2)
    M = ((d > 14) & band).astype(np.uint8)
    M = cv2.morphologyEx(M, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    M = cv2.dilate(M, np.ones((5, 5), np.uint8)) & band.astype(np.uint8)
    out = lama(out, M)   # 10/2 LaMa(전엔 TELEA + 잔결)
    ty0, ty1, tx0, tx1 = TITLE
    out[ty0:ty1, tx0:tx1] = er[ty0:ty1, tx0:tx1]
    erased = np.dstack([out, j8[..., 3]])
    Image.fromarray(erased, 'RGBA').save(os.path.join(G, 'done', 'g125_erased.png'))
    # 글자: 어두운 그늘(넓고 흐림) → 1px 테두리 → 밝은 획
    H, W = out.shape[:2]
    f = ImageFont.truetype(FONT, SIZE)
    m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
    for t, by in zip(LINES, BASES):   # 줄마다 글자 모양(받침·높은 글자)과 상관없이 같은 기준선 간격
        d.text((CX, by), t, font=f, fill=255, anchor='ms')
    m = np.asarray(m).astype(np.float32) / 255
    # 원본처럼: 글자 둘레 옅은 보랏빛 번짐(밝게) → 얇은 어두운 테두리 → 밝은 획
    # 원본처럼: 검은 남보라 획 + 바로 둘레 밝은 보랏빛 테두리 + 바깥으로 옅게 퍼지는 빛
    near = np.clip(cv2.GaussianBlur(cv2.dilate(m, np.ones((5, 5), np.uint8)), (0, 0), 1.2) * 1.1, 0, 1)
    far = np.clip(cv2.GaussianBlur(cv2.dilate(m, np.ones((9, 9), np.uint8)), (0, 0), 4.0) * 0.55, 0, 1)
    glow = np.maximum(near, far)[..., None]
    o = out.astype(np.float32)
    o = o * (1 - glow) + np.array(GLOW, np.float32) * glow
    o = o * (1 - m[..., None]) + np.array(INK, np.float32) * m[..., None]
    res = np.dstack([np.clip(o, 0, 255).astype(np.uint8), j8[..., 3]])
    Image.fromarray(res, 'RGBA').save(os.path.join(G, 'done', 'g125.png'))
    ch = np.abs(res.astype(int) - j8.astype(int)).sum(2) > 0
    keep = band.copy(); keep[ty0:ty1, tx0:tx1] = True
    print('띠·제목 밖 변경', int((ch & ~keep).sum()))


if __name__ == '__main__':
    main()
