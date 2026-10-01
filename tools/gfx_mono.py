"""흑백 1비트 안내문(g090 컨트롤러 안내): 검정 바탕에 흰 갈무리14(픽셀 글꼴, 10/1 사용자 지정), 번짐 없이(원본처럼 0/255만).
원본 글줄의 세로 위치·가로 가운데를 재서 같은 자리에 한 줄씩 쓴다.
python gfx_mono.py g090"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, 'work', 'gfx')
FONT = os.path.join(ROOT, 'work', 'fonts', 'NotoSansKR-VF.ttf')
CFG = {'g090': {'lines': ['컨트롤러가 연결되어 있지 않은 것 같습니다.', '컨트롤러 소켓 1에 컨트롤러를 연결해 주세요.'], 'size': 15, 'font': 'Galmuri14.ttf'}}   # 갈무리14는 15에서 번짐 없이 딱 맞음


def rows_of(m):
    on = m.any(1)
    out, y = [], 0
    while y < len(on):
        if on[y]:
            y0 = y
            while y < len(on) and on[y]:
                y += 1
            out.append((y0, y))
        y += 1
    return out


def make(gid, c):
    jp = np.asarray(Image.open(os.path.join(G, 'src', gid + '_jp.png')).convert('RGB'))
    H, W = jp.shape[:2]
    m = jp.mean(2) > 128
    rows = rows_of(m)
    print(gid, '원본 글줄', rows)
    f = ImageFont.truetype(os.path.join(ROOT, 'work', 'fonts', c['font']) if c.get('font') else FONT, c['size'])
    if c.get('weight'):
        f.set_variation_by_axes([c['weight']])
    img = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(img)
    for (y0, y1), t in zip(rows, c['lines']):
        xs = np.where(m[y0:y1].any(0))[0]
        cx = (xs.min() + xs.max() + 1) / 2
        l, tp, r, b = f.getbbox(t)
        d.text((round(cx - (r - l) / 2 - l), round((y0 + y1) / 2 - (b - tp) / 2 - tp)), t, font=f, fill=255)
        print(' ', t, '폭', r - l, '/', W)
    a = (np.asarray(img) >= 110).astype(np.uint8) * 255   # 원본처럼 흑백 두 값만
    out = np.stack([a, a, a, np.full_like(a, 255)], 2)
    Image.fromarray(out, 'RGBA').save(os.path.join(G, 'done', gid + '.png'))


if __name__ == '__main__':
    for g in sys.argv[1:]:
        make(g, CFG[g])
