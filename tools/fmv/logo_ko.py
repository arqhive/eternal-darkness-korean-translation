"""오프닝 영상(fmv0001) 끝 로고 부제(일본어 두 줄 「エターナルダークネス ─招かれた13人─」)를 지우고 한글로 다시 그림.
입력은 2336번 키프레임부터 끝까지의 비어 있지 않은 프레임(yuv420p 512x272). tools/fmv_logo.py 가 부름.
- 나타나는 구간: 프레임마다 원본 글자 진하기를 재서 한글도 같은 진하기로.
- 사라지는 구간(화면이 회색으로 바램): 마지막 정지 프레임의 지운 바탕 × 밝기 비, 한글 진하기는 원본 글자 대비 회귀값.
  글자가 거의 안 보이면 원본 화면으로 되돌림."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, binary_dilation

W, H = 512, 272; FS = W * H * 3 // 2
BOX = (186, 252, 118, 400)          # y0,y1,x0,x1 (부제 두 줄을 넉넉히)
REF = 97                             # 부제가 나타나기 전 프레임
STEADY = range(150, 186)             # 부제가 다 나타나 있는 구간
ACTIVE = range(95, 10000)             # 부제가 실제로 보이는 구간(밖은 원본 그대로: 앞쪽 빛줄기에 진하기가 잘못 잡힘)
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'work', 'fonts', 'NotoSansKR-VF.ttf')
L1, L2 = '이터널 다크니스', '─ 초대받은 13인 ─'
L1PX, L1W, L2PX, L2W = 25, 212, 15, 200   # 글자 크기·전체 폭(512 기준, 원본 일본어 줄 폭에 맞춤)
SS = 4                               # 글자 그릴 때 배율(부드러운 가장자리)


def load(a):
    Y = a[:, :W * H].reshape(-1, H, W).astype(np.float32)
    U = a[:, W * H:W * H + W * H // 4].reshape(-1, H // 2, W // 2).astype(np.float32)
    V = a[:, W * H + W * H // 4:].reshape(-1, H // 2, W // 2).astype(np.float32)
    return a, Y, U, V


def ncsmooth(x, w, s):
    return gaussian_filter(x * w, s) / np.maximum(gaussian_filter(w, s), 1e-4)


def text_mask(Y):
    """일본어 글자 자리: 부제가 있는 구간 평균이 바탕(부제 전 프레임 밝기 비로 맞춘 것)보다 어두운 곳."""
    y0, y1, x0, x1 = BOX
    st = Y[list(STEADY)].mean(0)[y0:y1, x0:x1]; ref = Y[REF][y0:y1, x0:x1]
    r = st / np.maximum(ref, 1)
    m = np.zeros_like(st, bool)
    for _ in range(3):
        rs = ncsmooth(r, (~m).astype(np.float32), 5)
        m = st < ref * rs - 7
    m[:196 - y0] = False             # 위쪽은 영어 로고 아랫부분(건드리지 않음)
    return binary_dilation(m, iterations=2) & (np.arange(y1 - y0)[:, None] >= 194 - y0)


def background(Yt, ref, m):
    """글자 자리 바탕(부제 전 프레임 × 글자 밖에서 잰 밝기 비)."""
    r = Yt / np.maximum(ref, 1)
    rs = ncsmooth(r, (~m).astype(np.float32), 4)
    out = Yt.copy(); out[m] = (ref * rs)[m]
    return out


def unmix(Yt, bgr, aj, st, inkj):
    """원본 = 바탕×(1-a) + 글자색×a 를 거꾸로 풀어 바탕을 살림(a=일본어 덮임×그 프레임 진하기).
    덮임이 큰 곳(굵은 획 속)은 풀 수 없으니 bgr(부제 전 프레임 기반)로."""
    at = aj * st
    inv = (Yt - inkj * at) / np.maximum(1 - at, 0.05)
    w = np.clip((0.7 - at) / 0.3, 0, 1)
    return inv * w + bgr * (1 - w)


def draw_track(d, txt, f, cx, cy, width, alt=None):
    """글자마다 따로 그려 전체 폭이 width(배율 적용 px)가 되게 자간을 벌림."""
    txt = [u for u in __import__('re').findall(r'\d+|.', txt)]   # 숫자 묶음은 한 덩어리(1 3 으로 벌어지지 않게)
    fo = [alt[ch] if alt and ch in alt else f for ch in txt]   # 글자별 글꼴(「크」만 보통 굵기)
    ws = [d.textlength(ch, font=g) for ch, g in zip(txt, fo)]
    gap = (width - sum(ws)) / max(len(txt) - 1, 1)
    bb = d.textbbox((0, 0), ''.join(txt), font=f); x = cx - width / 2
    for ch, w, g in zip(txt, ws, fo):
        d.text((x, cy - (bb[1] + bb[3]) / 2), ch, font=g, fill=255); x += w + gap


def glyph_layer():
    """한글 두 줄의 덮임(0~1). 원본 글자 칸 폭에 맞춰 가운데 정렬."""
    y0, y1, x0, x1 = BOX; h, w = y1 - y0, x1 - x0
    big = Image.new('L', (w * SS, h * SS), 0); d = ImageDraw.Draw(big)
    f1 = ImageFont.truetype(FONT, L1PX * SS); f1.set_variation_by_axes([900])
    f2 = ImageFont.truetype(FONT, L2PX * SS); f2.set_variation_by_axes([500])
    cx = (258 - x0) * SS
    f1r = ImageFont.truetype(FONT, L1PX * SS); f1r.set_variation_by_axes([400])
    draw_track(d, L1, f1, cx, (206 - y0) * SS, L1W * SS, {'크': f1r})
    draw_track(d, L2, f2, cx, (236 - y0) * SS, L2W * SS)
    return np.asarray(big.resize((w, h), Image.LANCZOS), np.float32) / 255


def strength(Y, m, bgs):
    """프레임마다 원본 글자 진하기(부제가 다 나온 구간 = 1)."""
    y0, y1, x0, x1 = BOX
    c = np.array([((bg - Y[t, y0:y1, x0:x1])[m]).mean() for t, bg in enumerate(bgs)])
    full = np.median(c[list(STEADY)])
    return np.clip(c / full, 0, 1)


INK1, INK2 = 14.0, 40.0              # 줄1·줄2 글자 밝기(원본 측정)


def run(seg, ts=None):
    a, Y, U, V = load(seg)
    y0, y1, x0, x1 = BOX
    m = text_mask(Y); ref = Y[REF, y0:y1, x0:x1]
    bgs = [background(Y[t, y0:y1, x0:x1], ref, m) for t in range(len(Y))]
    s = strength(Y, m, bgs)
    st = np.mean([bgs[t] for t in STEADY], 0); ys = Y[list(STEADY)].mean(0)[y0:y1, x0:x1]
    inkj = np.where(np.arange(y1 - y0)[:, None] < (222 - y0), INK1, INK2)
    aj = np.clip((st - ys) / np.maximum(st - inkj, 1), 0, 1) * m
    g = glyph_layer()
    ink = np.where(np.arange(y1 - y0)[:, None] < (222 - y0), INK1, INK2)
    out = a.copy(); er = a.copy()
    FADE = STEADY[-1]                 # 이 프레임 뒤로는 화면 전체가 어두워지는 구간
    comp = {}
    for t in range(len(Y)):
        if t not in ACTIVE or t > FADE:
            continue
        bg = unmix(Y[t, y0:y1, x0:x1], bgs[t], aj, s[t], inkj)
        al = g * s[t]
        comp[t] = (bg, bg * (1 - al) + ink * al)
    yf = Y[FADE, y0:y1, x0:x1]
    clean = comp[FADE][0]               # 마지막 정지 프레임의 지운 바탕
    band = np.arange(y1 - y0)[:, None] >= 194 - y0
    R = binary_dilation(m, iterations=3) & band
    wm = (~m).astype(np.float32)
    AS = []
    for t in range(FADE + 1, len(Y)):
        yt = Y[t, y0:y1, x0:x1]
        rs = ncsmooth(yt / np.maximum(clean, 1), wm, 6)          # 바탕이 어두워지는 비율(글자 밖에서)
        bg = np.where(m, clean * rs, yt)                          # 글자 자리는 정지 프레임 바탕 × 비율로 통째로
        A = float(np.clip(np.polyfit(yf[R], yt[R], 1)[0], 0, 1)); AS.append(A)   # 글자 대비가 남은 비율
        al = g * s[FADE] * A
        ko = bg * (1 - al) + ink * rs * al
        wv = float(np.clip((A - 0.02) / 0.15, 0, 1))             # 글자가 거의 안 보이면 원본 화면으로 되돌림(바탕 추정 얼룩 방지)
        bg = bg * wv + yt * (1 - wv); ko = ko * wv + yt * (1 - wv)
        comp[t] = (np.where(band, bg, yt), np.where(band, ko, yt))
    for t in (ts if ts is not None else range(len(Y))):
        if t not in comp:
            continue
        for arr, img in ((er, comp[t][0]), (out, comp[t][1])):
            yy = arr[t, :W * H].reshape(H, W); yy[y0:y1, x0:x1] = np.clip(np.round(img), 0, 255)
    return a, er, out, s, m
