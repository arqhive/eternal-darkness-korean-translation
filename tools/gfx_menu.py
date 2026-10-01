"""타이틀 메뉴 배경(g127 옵션 목록, g128 메모리 카드): 로고는 북미판으로 교체(10/1 결정), 그림 속 메뉴 글자는 한글로.
지우기: 글자 상자 안 밝은 획(+번짐)을 잡아, 같은 자리에 북미판 글자가 없으면 북미판 픽셀로, 있으면 인페인팅.
python gfx_menu.py g127 g128"""
import os, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lama import inpaint as lama

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, 'work', 'gfx')
FONT = os.path.join(ROOT, 'work', 'fonts', 'YeoncheonHeomok.ttf')
LOGO = (405, 15, 727, 181)     # x0, y0, x1, y1 — 일본판·북미판 로고 차이 범위(+여유)
CFG = {
    'g127': {'size': 22, 'ink': (92, 118, 124), 'glow': None, 'th': 25, 'align': 'L', 'no_u': True, 'black': (0, 100, 430, 415),   # 검정 바탕(원본 이 상자는 글자 밖 전부 0): 북미판 글자 번짐이 섞이지 않게 둘레로만 메움
             # (상자 x0, y0, x1, y1, 글)
             'lines': [((174, 119, 360, 147), '설정 저장'), ((174, 159, 360, 187), '자막'),
                       ((174, 199, 360, 227), '와이드 화면'), ((174, 241, 360, 270), '진동'),
                       ((174, 285, 360, 314), '음량 조절'), ((174, 327, 360, 356), '밝기 조절'),
                       ((174, 372, 380, 400), '오디오 모드')]},
    'g128': {'size': 19, 'lama': True, 'ink': (196, 234, 236), 'glow': (120, 200, 210), 'outline': (10, 22, 26), 'th': 110, 'align': 'C',
             'lines': [((215, 46, 345, 70), '메모리 카드'), ((178, 76, 268, 100), '슬롯 A'), ((290, 76, 380, 100), '슬롯 B')]},
    # 메모리 카드 고르기 화면(로고 없음): 슬롯 이름만, g128과 같은 하늘빛 글자
    'g136': {'size': 26, 'ink': (196, 234, 236), 'glow': (120, 200, 210), 'outline': (10, 22, 26), 'th': 110, 'align': 'C', 'no_u': True, 'logo': None, 'fade': 229,   # 위 테두리 빛이 아래로 옅어지다 검정이 되도록
             'lines': [((106, 230, 226, 259), '슬롯 A'), ((426, 230, 546, 259), '슬롯 B')]},
}


def make(gid, c):
    j8 = np.array(Image.open(os.path.join(G, 'src', gid + '_jp.png')).convert('RGBA'))
    u8 = np.array(Image.open(os.path.join(G, 'src', gid + '_u.png')).convert('RGBA'))
    jr, ur = np.ascontiguousarray(j8[..., :3]), np.ascontiguousarray(u8[..., :3])
    out = jr.copy()
    lx0, ly0, lx1, ly1 = c.get('logo', LOGO) or (0, 0, 0, 0)
    out[ly0:ly1, lx0:lx1] = ur[ly0:ly1, lx0:lx1]
    Lj, Lu = jr.mean(2), ur.mean(2)
    # 글자+번짐 = 상자(여유 6px) 안에서 일본판이 북미판과 다른 곳(바탕은 두 판이 같음)
    diff = np.abs(jr.astype(int) - ur.astype(int)).sum(2) > 18
    box = np.zeros(Lj.shape, bool)
    for (x0, y0, x1, y1), _ in c['lines']:
        box[max(0, y0 - 6):y1 + 6, max(0, x0 - 6):x1 + 6] = True
    mask = cv2.dilate((diff & box).astype(np.uint8), np.ones((3, 3), np.uint8))
    # 북미판 쪽 글자(+번짐): 북미판이 일본판보다 밝은 곳
    utext = cv2.dilate(((Lu - Lj) > 6).astype(np.uint8), np.ones((5, 5), np.uint8))
    if c.get('no_u'):
        utext[:] = 1
    if c.get('lama'):   # 10/2: 글자+번짐 전체를 LaMa로(북미판 픽셀 섞지 않음)
        rest = mask.astype(np.uint8)
        out = lama(out, rest)
    else:
        take_u = (mask > 0) & (utext == 0)
        out[take_u] = ur[take_u]
        rest = ((mask > 0) & (utext > 0)).astype(np.uint8)
        out = cv2.inpaint(out, rest, 5, cv2.INPAINT_TELEA)
    if c.get('fade'):   # 글자 상자: 바로 위 줄(테두리 빛 끝자락)을 8px에 걸쳐 검정으로 옅게 이어 채움
        fy = c['fade']
        for (x0, y0, x1, y1), _ in c['lines']:
            xa, xb = max(0, x0 - 6), x1 + 6
            row = out[fy - 1, xa:xb].astype(np.float32)
            for y in range(fy, y1 + 8):
                k = max(0.0, 1 - (y - fy + 1) / 8)
                out[y, xa:xb] = (row * k).astype(np.uint8)
    if c.get('black'):   # 글자 밖이 원래 완전 검정인 상자: 남은 잔여물 없이 0으로
        bx0, by0, bx1, by1 = c['black']
        out[by0:by1, bx0:bx1] = 0
    Image.fromarray(np.dstack([out, j8[..., 3]]), 'RGBA').save(os.path.join(G, 'done', gid + '_erased.png'))
    # 글자
    H, W = out.shape[:2]
    f = ImageFont.truetype(FONT, c['size'])
    m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
    for (x0, y0, x1, y1), t in c['lines']:
        ys, xs = np.where(Lj[y0:y1, x0:x1] > max(c['th'], 60))
        cy = y0 + (ys.min() + ys.max() + 1) / 2
        if c['align'] == 'L':
            x = x0 + xs.min()
            d.text((x, cy), t, font=f, fill=255, anchor='lm')
        else:
            d.text((x0 + (xs.min() + xs.max() + 1) / 2, cy), t, font=f, fill=255, anchor='mm')
        d.text((0, 0), '', font=f)
    mm = np.asarray(m).astype(np.float32) / 255
    mm = np.maximum(mm, np.roll(mm, 1, 1))   # 반굵기
    o = out.astype(np.float32)
    if c.get('glow'):
        gl = np.clip(cv2.GaussianBlur(cv2.dilate(mm, np.ones((5, 5), np.uint8)), (0, 0), 2.5) * 0.7, 0, 1)[..., None]
        o = o * (1 - gl) + np.array(c['glow'], np.float32) * gl
    if c.get('outline'):
        ol = np.clip(cv2.dilate(mm, np.ones((3, 3), np.uint8)), 0, 1)[..., None]
        o = o * (1 - ol) + np.array(c['outline'], np.float32) * ol
    o = o * (1 - mm[..., None]) + np.array(c['ink'], np.float32) * mm[..., None]
    res = np.dstack([np.clip(o, 0, 255).astype(np.uint8), j8[..., 3]])
    Image.fromarray(res, 'RGBA').save(os.path.join(G, 'done', gid + '.png'))
    keep = np.zeros(Lj.shape, bool); keep[ly0:ly1, lx0:lx1] = True
    for (x0, y0, x1, y1), _ in c['lines']:
        keep[max(0, y0 - 4):y1 + 4, max(0, x0 - 4):x1 + 4] = True
    ch = np.abs(res.astype(int) - j8.astype(int)).sum(2) > 0
    print(gid, '로고·글자 상자 밖 변경', int((ch & ~keep).sum()), '인페인팅', int(rest.sum()))


if __name__ == '__main__':
    for g in sys.argv[1:]:
        make(g, CFG[g])
