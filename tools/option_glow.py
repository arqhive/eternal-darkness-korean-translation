"""타이틀 옵션 메뉴 강조 글씨(10/20): 커서가 올라가면 덮이는 빛나는 글씨 7장을 배경(g127, GPT판) 글씨와 똑같은 획으로 다시 만든다.
일본판은 강조 그림의 글자 획이 배경 글씨 획과 완전히 겹친다(사용자 확인). 예전 판은 gfx_glowbtn 이 다른 글꼴로 그려 어긋났다.

방법
  1) 일본판에서 강조 그림 원점을 배경 글씨와 맞춰 찾는다(ORIGIN, 획 상관 최대).
  2) 일본판 「배경 글씨 획 진하기 t」 → 「강조 그림 RGBA」 관계를 t 와 여러 크기로 흐린 t 의 선형 결합으로 배운다(빛 번짐 포함).
  3) 같은 관계를 GPT 배경의 한글 획 진하기에 적용해 강조 그림을 만든다. 그림 칸 크기·원점은 일본판 그대로.
python tools/option_glow.py           → 미리보기 work/review7/option_glow.png (바꾸지 않음)
python tools/option_glow.py --write   → work/gfx/done/<id>.png 교체(이전 것은 work/GPT/이전/)
"""
import os
import shutil
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, 'work', 'gfx')
# 강조 그림 원점(일본판 배경 g127 위, 획 상관으로 찾음)
ORIGIN = {'g158': (176, 111), 'g145': (173, 146), 'g149': (169, 192), 'g133': (169, 235),
          'g134': (164, 274), 'g135': (149, 320), 'g151': (159, 367)}
SIGMAS = (0.7, 1.5, 3, 6, 10)


def rgba(p):
    return np.asarray(Image.open(p).convert('RGBA')).astype(np.float32)


def stroke(bg, x, y, w, h):
    """배경 글씨 획 진하기 0~1: 어두운 바탕 위 밝은 획(배경 밝기를 넓게 빼고 정규화)."""
    L = bg[y:y + h, x:x + w, :3].mean(2)
    base = np.minimum(gaussian_filter(L, 12), np.percentile(L, 30))
    t = np.clip(L - base, 0, None)
    hi = np.percentile(t[t > 8], 95) if (t > 8).sum() > 20 else 1
    t = np.clip(t / max(hi, 1), 0, 1)
    return np.where(t < 0.15, 0, t)   # 배경 잡티(GPT 배경의 옅은 무늬)는 빼기


def feats(t):
    f = [t] + [gaussian_filter(t, s) for s in SIGMAS]   # 상수항 없음(검정 바탕은 0이어야 더하기 합성에서 티가 안 남)
    return np.stack(f, -1).reshape(-1, len(f))


def fit():
    bg = rgba(os.path.join(G, 'src', 'g127_jp.png'))
    X, Y = [], []
    for g, (x, y) in ORIGIN.items():
        sp = rgba(os.path.join(G, 'src', g + '_jp.png'))
        h, w = sp.shape[:2]
        t = stroke(bg, x, y, w, h)
        X.append(feats(t)); Y.append(sp[..., :3].reshape(-1, 3))   # 일본판 강조 그림은 불투명(알파 255), 검정 바탕 + 밝은 획·번짐
    X = np.concatenate(X); Y = np.concatenate(Y)
    from scipy.optimize import nnls
    return np.stack([nnls(X, Y[:, c])[0] for c in range(3)], 1)


def band(g, h):
    """칸 안에서 자기 메뉴 줄의 세로 범위(일본판 강조 그림에 밝은 글씨가 있는 줄 ±4px). 칸이 아랫줄까지 걸쳐 있어 그 줄 글씨를 빼려고."""
    sp = rgba(os.path.join(G, 'src', g + '_jp.png'))
    rows = np.nonzero((sp[..., :3].mean(2) > 120).any(1))[0]
    m = np.zeros(h, np.float32); m[max(rows.min() - 4, 0):rows.max() + 5] = 1
    return gaussian_filter(m, 1.5)[:, None]


def make(W, bg, g, x, y, w, h, gain=False):
    t = stroke(bg, x, y, w, h) * band(g, h)
    rgb = (feats(t) @ W).reshape(h, w, 3)
    if gain:   # 한글 획이 일본판보다 가늘어 심이 흰색까지 못 오름 → 밝은 부분 99%가 일본판처럼 255가 되게
        L = rgb.mean(2); rgb = rgb * (255 / max(np.percentile(L[L > 20], 99), 1))
    rgb = np.clip(rgb, 0, 255)
    return np.dstack([rgb, np.full((h, w), 255.0)]).round().astype(np.uint8)


def main():
    write = '--write' in sys.argv
    W = fit()
    jp = rgba(os.path.join(G, 'src', 'g127_jp.png')); ko = rgba(os.path.join(G, 'done', 'g127.png'))
    rows = []
    for g, (x, y) in ORIGIN.items():
        sp = rgba(os.path.join(G, 'src', g + '_jp.png')); h, w = sp.shape[:2]
        rec = make(W, jp, g, x, y, w, h)          # 일본판 재현(맞는지 확인용)
        new = make(W, ko, g, x, y, w, h, gain=True)
        err = np.abs(rec[..., :3].astype(np.float32) - sp[..., :3]).mean()
        print(g, '일본판 재현 오차 %.1f' % err)
        if write:
            dst = os.path.join(G, 'done', g + '.png')
            bak = os.path.join(ROOT, 'work', 'GPT', '이전'); os.makedirs(bak, exist_ok=True)
            if os.path.exists(dst):
                shutil.copy2(dst, os.path.join(bak, g + '_glowbtn.png'))
            Image.fromarray(new, 'RGBA').save(dst)
        # 미리보기: 배경 위에 덮은 모습(일본판 원본 | 일본판 재현 | 한글 예전 | 한글 새로)
        def over(bgimg, spr):   # 게임은 더하기 합성(검정 = 변화 없음)
            return np.clip(bgimg[y:y + h, x:x + w, :3] + spr[..., :3].astype(np.float32), 0, 255).astype(np.uint8)
        old = rgba(os.path.join(ROOT, 'work', 'GPT', '이전', g + '_glowbtn.png')) if write else rgba(os.path.join(G, 'done', g + '.png'))
        if old.shape[:2] != (h, w):
            old = np.zeros((h, w, 4), np.float32)
        cells = [jp[y:y + h, x:x + w, :3].astype(np.uint8), over(jp, sp), ko[y:y + h, x:x + w, :3].astype(np.uint8), over(ko, old), over(ko, new)]
        row = np.concatenate([np.pad(c, ((2, 2), (2, 2), (0, 0))) for c in cells], 1)
        rows.append(row)
    wmax = max(r.shape[1] for r in rows)
    sheet = np.concatenate([np.pad(r, ((0, 0), (0, wmax - r.shape[1]), (0, 0))) for r in rows], 0)
    os.makedirs(os.path.join(ROOT, 'work', 'review7'), exist_ok=True)
    Image.fromarray(sheet).resize((sheet.shape[1] * 2, sheet.shape[0] * 2), Image.NEAREST).save(os.path.join(ROOT, 'work', 'review7', 'option_glow.png'))


if __name__ == '__main__':
    main()
