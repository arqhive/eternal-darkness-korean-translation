"""책 탭(보라 글자 + 흰 빛) g064~g067.
바탕: 탭 12장(+소지품 탭 2장) 모두 같은 띠에 빛이 있어 빛 없는 바탕은 없다 → 원본 빛은 그대로 두고 보라 글자 획만 지워 빛으로 메운다(인페인팅).
글자: 허목체 보라 획, 그 밑에 글자 모양을 넓혀 흐린 흰 빛. 위치는 일본어 글자 덩어리 가운데.
python gfx_tab.py g064 ..."""
import os, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, 'work', 'gfx')
FONT = os.path.join(ROOT, 'work', 'fonts', 'YeoncheonHeomok.ttf')
TABS = ('g064', 'g065', 'g066', 'g067')
CFG = {'g064': '옵션', 'g065': '맵', 'g066': '스펠', 'g067': '저널', 'g083': '소지품'}   # 10/1 탭 이름 일본어 음차
SIZE = 24
INK = (115, 85, 195)        # 원본 보라 획 진한 쪽
GLOW = (238, 243, 252)      # 원본 빛 색
NUDGE = {'g066': (1, 1)}     # 사람이 지정한 미세 이동(px, 오른쪽·아래)


def load(g, t):
    return np.asarray(Image.open(os.path.join(G, 'src', '%s_%s.png' % (g, t))).convert('RGBA')).astype(np.float32)


def clean_bg():
    ims = [load(g, t) for g in TABS for t in ('jp', 'e', 'u')]
    st = np.stack([i[..., :3].mean(2) for i in ims])
    k = st.argmin(0)
    rgb = np.stack(ims)[..., :3]
    H, W = k.shape
    bg = rgb[k, np.arange(H)[:, None], np.arange(W)[None, :]]
    return bg, st.min(0)


def make(gid, bg, mn):
    """10/2 LaMa판: 탭 14장 최솟값 + 남은 빛만 LaMa로 메운 깨끗한 나무판(work/gfx/tab_clean_bg.png) 위에
    원본 빛판을 통째로 지우고, 한글 글자 모양에 맞춘 새 빛을 원본 빛 색으로 깐다."""
    jp = load(gid, 'jp')
    clean = np.asarray(Image.open(os.path.join(G, 'tab_clean_bg.png')).convert('RGB')).astype(np.float32)
    rgb = jp[..., :3]
    diff = np.abs(rgb - clean).sum(2)
    glow = cv2.dilate((diff > 18).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    glow[:, :7] = False; glow[:, -7:] = False
    out = jp.copy()
    out[..., :3][glow] = clean[glow]
    erased = out.copy()
    L = rgb.mean(2)
    pur = (rgb[..., 2] - rgb[..., 1] > 50) & (L > 60)
    ys, xs = np.where(pur)
    cx, cy = (xs.min() + xs.max() + 1) / 2, (ys.min() + ys.max() + 1) / 2
    inkc = np.median(rgb[pur & (rgb[..., 2] - rgb[..., 1] > np.percentile((rgb[..., 2] - rgb[..., 1])[pur], 50))], 0)
    whitish = (L > np.percentile(L[glow], 90)) & ~cv2.dilate(pur.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    glc = np.median(rgb[whitish], 0)
    H, W = L.shape
    f = ImageFont.truetype(FONT, SIZE)
    t = CFG[gid]
    l, tp, r, b = f.getbbox(t)
    m = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(m)
    ox, oy = round(cx - (r - l) / 2 - l), round(cy - (b - tp) / 2 - tp)
    ox, oy = ox + NUDGE.get(gid, (0, 0))[0], oy + NUDGE.get(gid, (0, 0))[1]
    for dx in (0, 1):   # 반굵기
        dr.text((ox + dx, oy), t, font=f, fill=255)
    m = np.asarray(m).astype(np.float32) / 255
    # 원본처럼: 글자 둘레 진한 빛판(넓게 덮음) + 바깥으로 옅게 퍼짐
    # 원본처럼 빛은 글자 획 둘레에 몰리고 바깥으로 옅게 퍼짐(10/2: 속이 꽉 찬 흰 덩어리 → 획 따라 가볍게)
    near = cv2.GaussianBlur(cv2.dilate(m, np.ones((5, 5), np.uint8)), (0, 0), 2.2)
    mid = cv2.GaussianBlur(cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 13))), (0, 0), 4.5)
    far = cv2.GaussianBlur(cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 21))), (0, 0), 8.0)
    ga = (1 - (1 - np.clip(near * 1.2, 0, 0.9)) * (1 - mid * 0.75) * (1 - far * 0.65))[..., None]   # 겹쳐 더하되 포화 없이 서서히 옅어짐
    # 빛 바깥쪽은 원본 빛판 가장자리 색(푸르스름), 안쪽은 흰빛
    edge = (glow & (L > 60) & (L < np.percentile(L[glow], 60)) & ~pur)
    edc = np.median(rgb[edge], 0) if edge.any() else glc
    w_in = np.clip((ga - 0.35) / 0.45, 0, 1)
    col = edc * (1 - w_in) + glc * w_in
    o = out[..., :3] * (1 - ga) + col * ga
    o = o * (1 - m[..., None]) + inkc * m[..., None]
    out[..., :3] = o
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(G, 'done', gid + '.png'))
    Image.fromarray(np.clip(erased, 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(G, 'done', gid + '_erased.png'))
    print(gid, t, '글자색', inkc.astype(int), '빛 색', glc.astype(int), '지운 픽셀', int(glow.sum()))


if __name__ == '__main__':
    bg, mn = clean_bg()
    for g in sys.argv[1:]:
        make(g, bg, mn)
