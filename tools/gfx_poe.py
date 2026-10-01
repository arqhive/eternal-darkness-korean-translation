"""포 인용문 화면(JPoe.tpl 0번, g170): 영어 손글씨·빛줄기·서명을 LaMa로 지우고 한글로 다시 그린다(10/2 사용자 결정).
빛줄기는 원본처럼 글자 층을 화면 가운데로 방사형(줌) 흐림해서 만든다.
python gfx_poe.py"""
import os, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lama import inpaint

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, 'work', 'gfx')
LOCAL = os.environ.get('LOCALAPPDATA', '')
HAND = os.path.join(LOCAL, 'Microsoft', 'Windows', 'Fonts', 'NanumPenScript-Regular.ttf')
SERIF = os.path.join(LOCAL, 'Microsoft', 'Windows', 'Fonts', 'NotoSerifKR-VF.ttf')
# 영어 원문(The Raven) 번역. 원본처럼 줄마다 오른쪽으로 들여 계단 모양
# 나눔펜에는 '…' 글리프가 없어 마침표 셋으로 씀
LINES = [('“그 어둠 속을 깊이 들여다보며,', 45, 88), ('오래도록 나는 그곳에 서 있었다,', 90, 140),
         ('의아해하며...', 175, 192), ('두려워하며...', 205, 244), ('의심하며...”', 240, 296)]
SIZE = 52
INK = (197, 238, 246)
SIGN = ('에드거 앨런 포', 470, 362)
CENTER = (300, 210)


def zoom_blur(layer, center, steps=24, scale=0.18):
    """방사형 흐림: 가운데를 기준으로 조금씩 키운 사본을 겹친다."""
    h, w = layer.shape[:2]
    acc = np.zeros_like(layer, np.float32)
    for i in range(steps):
        s = 1 + scale * i / steps
        M = cv2.getRotationMatrix2D(center, 0, s)
        acc += cv2.warpAffine(layer, M, (w, h), flags=cv2.INTER_LINEAR)
    return acc / steps


def main():
    src = np.asarray(Image.open(os.path.join(G, 'src', 'g170_jp.png')).convert('RGB'))
    L = src.astype(int).mean(2)
    # 지울 곳: 글자·서명·빛줄기(바탕보다 밝은 곳) + 둘레
    bg = cv2.GaussianBlur(src, (0, 0), 25).astype(int).mean(2)
    far = cv2.GaussianBlur(src, (0, 0), 80).astype(int).mean(2)
    m = ((L - far > 4) & (L > 22)) | (L > 90)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
    m = cv2.dilate(m, np.ones((15, 15), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)   # 빛줄기 덩어리 안 구멍 메우기
    keep = [i for i in range(1, n) if st[i][4] > 400]
    m = np.isin(lab, keep).astype(np.uint8)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    m = np.zeros_like(m); cv2.drawContours(m, cnts, -1, 1, -1)
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61)))   # 빛줄기 끝자락까지(남으면 LaMa가 줄기를 이어 그림)
    er = inpaint(src, m)
    Image.fromarray(er).save(os.path.join(G, 'done', 'g170_erased.png'))
    H, W = L.shape
    t = Image.new('L', (W, H), 0); d = ImageDraw.Draw(t)
    f = ImageFont.truetype(HAND, SIZE)
    for s, x, y in LINES:
        for dx in (0, 1):
            d.text((x + dx, y), s, font=f, fill=255)
    tm = np.asarray(t).astype(np.float32) / 255
    rays = np.maximum(zoom_blur(cv2.GaussianBlur(tm, (0, 0), 1.5), CENTER, 32, 0.45) * 1.4, zoom_blur(cv2.GaussianBlur(tm, (0, 0), 1.5), CENTER))
    rays = np.clip(rays * 2.2, 0, 1)
    o = er.astype(np.float32)
    ink = np.array(INK, np.float32)
    o = o * (1 - rays[..., None] * 0.55) + ink * rays[..., None] * 0.55
    glow = np.clip(cv2.GaussianBlur(tm, (0, 0), 3.0) * 1.2, 0, 1)[..., None]
    o = o * (1 - glow * 0.5) + ink * glow * 0.5
    o = o * (1 - tm[..., None]) + ink * tm[..., None]
    s2 = Image.new('L', (W, H), 0)
    fs = ImageFont.truetype(SERIF, 26)
    try:
        fs.set_variation_by_axes([400])
    except Exception:
        pass
    ImageDraw.Draw(s2).text((SIGN[1], SIGN[2]), SIGN[0], font=fs, fill=255, anchor='mm')
    sm = np.asarray(s2).astype(np.float32)[..., None] / 255
    o = o * (1 - sm) + np.array((197, 238, 238), np.float32) * sm
    out = np.dstack([np.clip(o, 0, 255).astype(np.uint8), np.full((H, W), 255, np.uint8)])
    Image.fromarray(out, 'RGBA').save(os.path.join(G, 'done', 'g170.png'))
    print('지운 픽셀', int(m.sum()))


if __name__ == '__main__':
    main()
