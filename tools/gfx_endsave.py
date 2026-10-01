"""엔딩 저장 확인 g162(360×356): 글자가 판 대부분을 덮어 영어판도 같은 자리 → LaMa로 금 간 바탕을 되살리고
한글을 원본 꼴(하늘빛 흰 글자 + 1px 어두운 테두리 + 청록 빛)로 쓴다.
python gfx_endsave.py"""
import os, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lama import inpaint as lama   # 10/2 LaMa로 교체(전엔 gfx_quilt)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, 'work', 'gfx')
FONT = os.path.join(ROOT, 'work', 'fonts', 'YeoncheonHeomok.ttf')
# 영어 원문 번역, 일본판 높임(존댓말). 선택지는 본문 메모리 카드 번역과 같은 말
PARA = ['2천 년 넘게 세상을 지배해 온', '어둠을 마침내 물리치셨습니다.', '이로써 인류는 새로운 시대를',
        '맞이하게 될 것입니다.', '이 위대한 순간을 인류 역사의', '한 페이지에 기록하시겠습니까?']
PARA_Y = (36, 229)            # 일본어 본문 다섯 줄이 차지한 세로 범위
CHOICES = [('예 (저장하고 계속하기)', 287), ('아니요 (저장하지 않고 계속하기)', 335)]
CX = 180
SIZE, CSIZE = 24, 23
INK = (172, 218, 222)         # 원본 글자 속(측정)
EDGE = (16, 20, 24)           # 1~2px 어두운 테두리(측정)
GLOW = (60, 88, 90)           # 3~7px 청록 빛(측정)
CINK = (246, 250, 246)        # 선택지는 흰 글자 + 어두운 테두리, 빛 없음(측정)


def main():
    j = np.array(Image.open(os.path.join(G, 'src', 'g162_jp.png')).convert('RGBA'))
    rgb = np.ascontiguousarray(j[..., :3])
    L = rgb.astype(int).mean(2)
    bgmed = cv2.medianBlur(rgb, 21).astype(int).mean(2)
    m = ((L > 48) | (L - bgmed > 18)).astype(np.uint8)
    m[:, :2] = 0
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    m = np.isin(lab, [i for i in range(1, n) if st[i][4] >= 4]).astype(np.uint8)
    m = cv2.morphologyEx(cv2.dilate(m, np.ones((7, 7), np.uint8)), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    out = lama(rgb, m)
    Image.fromarray(np.dstack([out, j[..., 3]]), 'RGBA').save(os.path.join(G, 'done', 'g162_erased.png'))
    H, W = L.shape
    t = Image.new('L', (W, H), 0); d = ImageDraw.Draw(t)
    f = ImageFont.truetype(FONT, SIZE); fc = ImageFont.truetype(FONT, CSIZE)
    y0, y1 = PARA_Y
    gap = (y1 - y0) / len(PARA)
    for i, line in enumerate(PARA):
        d.text((CX, y0 + gap * (i + 0.5)), line, font=f, fill=255, anchor='mm')
    tc = Image.new('L', (W, H), 0); dc = ImageDraw.Draw(tc)
    for line, cy in CHOICES:
        dc.text((CX, cy), line, font=fc, fill=255, anchor='mm')
    def thick(img):
        a = np.asarray(img).astype(np.float32) / 255
        a = np.maximum(a, np.roll(a, 1, 1))   # 반굵기(원본 획이 굵음)
        return np.maximum(a, np.roll(a, 1, 0) * 0.6)
    mm, mc = thick(t), thick(tc)
    edge = np.clip(cv2.dilate(mm, np.ones((3, 3), np.uint8)), 0, 1)[..., None]
    glow = np.clip(cv2.GaussianBlur(cv2.dilate(mm, np.ones((7, 7), np.uint8)), (0, 0), 3.0) * 1.1, 0, 1)[..., None]
    o = out.astype(np.float32)
    o = o * (1 - glow) + np.array(GLOW, np.float32) * glow
    o = o * (1 - edge) + np.array(EDGE, np.float32) * edge
    o = o * (1 - mm[..., None]) + np.array(INK, np.float32) * mm[..., None]
    ec = np.clip(cv2.dilate(mc, np.ones((3, 3), np.uint8)), 0, 1)[..., None]
    o = o * (1 - ec) + np.array(EDGE, np.float32) * ec
    o = o * (1 - mc[..., None]) + np.array(CINK, np.float32) * mc[..., None]
    Image.fromarray(np.dstack([np.clip(o, 0, 255).astype(np.uint8), j[..., 3]]), 'RGBA').save(os.path.join(G, 'done', 'g162.png'))
    widths = [int(f.getlength(x)) for x in PARA] + [int(fc.getlength(x)) for x, _ in CHOICES]
    print('줄 폭', widths, '/', W)


if __name__ == '__main__':
    main()
