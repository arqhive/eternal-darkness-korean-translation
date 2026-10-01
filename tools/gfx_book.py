"""책 화면·버튼 그림 한글화(일본판과 영어판 그림이 같은 자리에 맞춰진 것).
지우기: 글자 구역 안에서 일본판이 영어판보다 어두운 픽셀(=일본어 글자) → 영어판 픽셀로 채움.
        영어판도 그 자리에 글자가 있으면(둘 다 어두움) 주변 결로 메움(cv2.inpaint).
        투명 바탕 그림(글자만 있는 조각)은 글자를 통째로 지우고 새로 씀.
배치: 구역마다 정렬(L·R·C), 글줄 수는 일본판과 같게, 연천 허목체, 글자색은 일본어 획에서 뽑음.
설정: work/gfx/book_cfg.json
  {id: {"regions": [[x0,y0,x1,y1,"L|R|C", ["줄", ...]], ...], "size": px, "color": [r,g,b] (생략 시 자동),
        "ref": "e|u" (기본 e), "stroke": 0}}
python gfx_book.py <id...>   → work/gfx/done/<id>.png, <id>_erased.png, review6/cmp_<id>.png
"""
import json
import os
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRC = os.path.join(ROOT, 'work', 'gfx', 'src')
OUT = os.path.join(ROOT, 'work', 'gfx', 'done')
REV = os.path.join(ROOT, 'work', 'gfx', 'review6')
FONT = os.path.join(ROOT, 'work', 'fonts', 'YeoncheonHeomok.ttf')
CFG = json.load(open(os.path.join(ROOT, 'work', 'gfx', 'book_cfg.json'), encoding='utf-8'))
THR = 16


def lum(a):
    return a[..., :3].astype(np.float32).mean(2)


def despeck(out, reg, maxa=4, thr=12):
    """구역 안 외딴 작은 점(maxa 픽셀 이하, 주변보다 thr 이상 어두움)을 바로 옆 색(중앙값)으로."""
    med = cv2.medianBlur(np.ascontiguousarray(out[..., :3]), 7)
    diff = med.astype(np.float32).mean(2) - lum(out)
    d = ((np.abs(diff) > thr).astype(np.uint8) & reg & (out[..., 3] == 255).astype(np.uint8))   # 어두운 점·밝은 점 모두
    n, lab, st, _ = cv2.connectedComponentsWithStats(d, 8)
    sp = np.isin(lab, [i for i in range(1, n) if st[i][4] <= maxa])
    sp = cv2.dilate(sp.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & (reg == 1)
    out[..., :3][sp] = med[sp]
    return int(sp.sum())


def erase(jp, ref, regions, clean=None, patch=False, allin=False, smooth=False, brighter=False, refclean=None, light=False, clear=False, board=False, board_t=16, glyph=0, inpaint_fill=False, wipe=(), keepbox=()):
    h, w = jp.shape[:2]
    reg = np.zeros((h, w), np.uint8)
    for r in regions:
        reg[max(0, r[1]):r[3], max(0, r[0]):r[2]] = 1
    if clear:   # 투명 바탕 조각(글자만 있는 그림): 구역 안 글자를 통째로 비움
        out = jp.copy()
        out[reg == 1] = 0
        return out, reg, (jp[..., 3] > 0) & (reg == 1)
    lj, lr = lum(jp), lum(ref)
    if board:   # 작은 나무판: 판 안에서 주변보다 어두운 획 = 글자 → 판 바탕색(획 밖을 부드럽게 이은 색) + 잔결
        out = jp.copy()
        src = jp[..., :3].astype(np.float32)
        bgv = cv2.medianBlur(np.ascontiguousarray(jp[..., :3]), 9).astype(np.float32)
        bgv = cv2.medianBlur(np.ascontiguousarray(jp[..., :3]), 11).astype(np.float32)
        dist = np.linalg.norm(src - bgv, axis=2)          # 색이 바탕과 다르면(어둡거나 푸른 회색) 글자 획
        rb = src[..., 0] - src[..., 2]; rbb = bgv[..., 0] - bgv[..., 2]   # 푸른 회색 기운(빨강-파랑 차가 바탕보다 작음)
        stroke = (((dist > board_t) | ((bgv.mean(2) - lj) > 9) | ((rbb - rb) > 6)) & (reg == 1)).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(stroke, 8)
        stroke = np.isin(lab, [i for i in range(1, n) if st[i][4] >= 2]).astype(np.uint8)
        opaque = (jp[..., 3] == 255).astype(np.uint8)
        stroke &= cv2.erode(opaque, np.ones((5, 5), np.uint8))   # 투명 가장자리 근처는 글자로 보지 않음
        em = (cv2.dilate(stroke, np.ones((3, 3), np.uint8)) & reg)
        keep = (1 - cv2.dilate(em, np.ones((3, 3), np.uint8))).astype(np.float32) * reg * opaque
        den = cv2.GaussianBlur(keep, (0, 0), 3)[..., None]
        lo = cv2.GaussianBlur(src * keep[..., None], (0, 0), 3) / (den + 1e-3)
        for sg in (6, 12, 24):   # 둘레에 남은 바탕이 적으면 더 넓게 이어 씀
            den2 = cv2.GaussianBlur(keep, (0, 0), sg)[..., None]
            lo2 = cv2.GaussianBlur(src * keep[..., None], (0, 0), sg) / (den2 + 1e-3)
            lo = np.where(den < 0.15, lo2, lo)
            den = np.maximum(den, den2)
        res = (src - lo)[keep > 0]
        sd = float(res.std()) if len(res) > 20 else 4.0
        rng = np.random.default_rng(7)
        noise = cv2.GaussianBlur(rng.normal(0, sd * 0.7, lj.shape).astype(np.float32), (0, 0), 0.6)
        fill = np.clip(lo + noise[..., None], 0, 255)
        # 판 결 살리기: 같은 줄에서 옆으로 떨어진(글자 없는) 자리의 잔결을 빌려 옴
        tex = np.clip(src - cv2.GaussianBlur(src, (0, 0), 2), -2.5 * sd, 2.5 * sd)   # 옆 획 둘레의 큰 차이가 밝은 줄로 옮겨 오지 않게
        ok = cv2.erode((keep > 0).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0   # 빌려 올 자리는 글자·가장자리에서 떨어진 판
        H, W = lj.shape
        ys, xs = np.where(em == 1)
        for dx in (-48, 48, -96, 96, -24, 24):
            xx = xs + dx
            v = (xx >= 0) & (xx < W)
            good = np.zeros(len(xs), bool)
            good[v] = ok[ys[v], xx[v]]
            sel = good & ~np.isnan(fill[ys, xs, 0])
            fill[ys[sel], xs[sel]] = np.clip(lo[ys[sel], xs[sel]] + tex[ys[sel], xx[sel]], 0, 255)
            ok_fill = sel
            ys, xs = ys[~sel], xs[~sel]
            if len(xs) == 0:
                break
        out[..., :3][em == 1] = fill[em == 1].astype(np.uint8)
        return out, reg, stroke.astype(bool)
    if refclean:   # 영어판에서 영어 글자만 지운 바탕(고른 바탕용)으로 일본어 구역을 덮음
        med = cv2.medianBlur(np.ascontiguousarray(ref[..., :3]), 11).astype(np.float32).mean(2)
        rt = ((med - lr) > 20) if refclean == 'dark' else ((lr - med) > 20)
        rt = (cv2.dilate(rt.astype(np.uint8), np.ones((5, 5), np.uint8)) & cv2.dilate(reg, np.ones((9, 9), np.uint8)))
        rc = cv2.inpaint(np.ascontiguousarray(ref[..., :3]), rt, 5, cv2.INPAINT_TELEA)
        out = jp.copy()
        out[..., :3][reg == 1] = rc[reg == 1]
        jt = (np.abs(lj - lr) > THR) & (reg == 1)
        return out, reg, jt
    if brighter:   # 같은 자리 영어판과 픽셀마다 더 밝은 쪽(한쪽에만 있는 글자는 사라짐), 둘 다 어두운 곳만 메움
        out = jp.copy()
        jt0 = ((((lj - lr) if light else (lr - lj)) > THR) & (reg == 1)).astype(np.uint8)
        near = cv2.dilate(jt0, np.ones((5, 5), np.uint8)).astype(bool)   # 일본어 획 둘레만 바꿈(영어 획 가장자리 빛이 새지 않게)
        pick = ((lr < lj) if light else (lr > lj)) & (reg == 1) & near
        out[..., :3][pick] = ref[..., :3][pick]
        lo_src = out[..., :3].astype(np.float32)
        lo = cv2.medianBlur(out[..., :3], 7).astype(np.float32)
        both = ((((lum(out) - lo.mean(2)) if light else (lo.mean(2) - lum(out))) > 14) & (reg == 1)).astype(np.uint8)
        both = cv2.dilate(both & near.astype(np.uint8), np.ones((3, 3), np.uint8)) & reg   # 일본어 획 둘레에서만 메움(판 테두리 보호)
        if both.any():
            rgb = cv2.inpaint(np.ascontiguousarray(out[..., :3]), both, 3, cv2.INPAINT_TELEA)
            out[..., :3][both == 1] = rgb[both == 1]
        jt = (((lj - lr) if light else (lr - lj)) > THR) & (reg == 1)
        return out, reg, jt
    if clean is not None:   # 깨끗한 바탕이 있으면: 바탕보다 어두운 덩어리 중 구역 안에 온전히 든 것 = 글자
        cf = clean[..., :3].astype(np.float32)
        d = lum(clean) - lj
        if glyph:   # 이 그림 자체의 둘레 밝기 기준(다른 페이지 바탕과 무관)
            d = cv2.medianBlur(np.ascontiguousarray(jp[..., :3]), 21).astype(np.float32).mean(2) - lj
        strong = (d > 18).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(strong, 8)
        txt = np.zeros_like(strong)
        for r in regions:
            for i in range(1, n):
                x, y, w, h, a = st[i]
                if x >= r[0] and y >= r[1] and x + w <= r[2] and y + h <= r[3]:
                    txt[lab == i] = 1
        if allin:   # 판 안쪽처럼 구역에 그림이 없으면: 구역 안 어두운 픽셀 전부 = 글자
            txt = strong & reg
        if glyph:   # 글자 크기 덩어리만(가운데가 구역 안, 높이·너비 작음) — 화살표처럼 긴 선은 제외
            txt = np.zeros_like(strong)
            for r in regions:
                for i in range(1, n):
                    x, y, w, h, a = st[i]
                    cx, cy = x + w / 2, y + h / 2
                    if r[0] <= cx < r[2] and r[1] <= cy < r[3] and h <= glyph and w <= glyph * 2.2:
                        txt[lab == i] = 1
        near = cv2.dilate(txt, np.ones((7, 7), np.uint8))
        faint = ((d > 6).astype(np.uint8) & near & reg)
        em = (cv2.dilate(txt | faint, np.ones((3, 3), np.uint8)) & reg).astype(bool)
        if patch:   # 같은 그림 안 가까운 빈 양피지를 떠 와서 채움(구역마다 가장 깨끗한 자리)
            cf = jp[..., :3].astype(np.float32).copy()
            jl = lj
            busy = ((cv2.GaussianBlur(jl, (0, 0), 8) - jl) > 10).astype(np.float32)   # 획·그림 같은 잔무늬
            H, W = jl.shape
            for r in regions:
                x0, y0, x1, y1 = r[0], r[1], r[2], r[3]
                best = None
                for dy in range(-240, 241, 6):
                    for dx in range(-240, 241, 6):
                        if dx == 0 and dy == 0:
                            continue
                        sx0, sy0, sx1, sy1 = x0 + dx, y0 + dy, x1 + dx, y1 + dy
                        if sx0 < 0 or sy0 < 0 or sx1 > W or sy1 > H:
                            continue
                        if not (sx1 <= x0 or sx0 >= x1 or sy1 <= y0 or sy0 >= y1):
                            continue
                        sc = busy[sy0:sy1, sx0:sx1].sum() + reg[sy0:sy1, sx0:sx1].sum() * 5 + 0.02 * (abs(dx) + abs(dy))
                        if best is None or sc < best[0]:
                            best = (sc, dx, dy)
                _, dx, dy = best
                cf[y0:y1, x0:x1] = jp[y0 + dy:y1 + dy, x0 + dx:x1 + dx, :3]
        if inpaint_fill:   # 둘레 바탕을 안쪽으로 이어 메우고(TELEA) 바탕과 같은 세기의 잔결을 얹음
            src = jp[..., :3].astype(np.float32)
            for x0, y0, x1, y1 in wipe:   # 사람이 지정한 잔여 조각 상자
                em[y0:y1, x0:x1] |= ((cv2.medianBlur(np.ascontiguousarray(jp[..., :3]), 15).astype(np.float32).mean(2) - lj)[y0:y1, x0:x1] > 10)
            emu = em.astype(np.uint8)
            rgb = cv2.inpaint(np.ascontiguousarray(jp[..., :3]), cv2.dilate(emu, np.ones((3, 3), np.uint8)), 6, cv2.INPAINT_TELEA).astype(np.float32)
            lo = cv2.GaussianBlur(src, (0, 0), 2)
            ring = (cv2.dilate(emu, np.ones((9, 9), np.uint8)) - cv2.dilate(emu, np.ones((3, 3), np.uint8))).astype(bool)
            sd = float((src - lo)[ring].std()) if ring.sum() > 20 else 4.0
            rng = np.random.default_rng(11)
            noise = cv2.GaussianBlur(rng.normal(0, sd * 0.9, emu.shape).astype(np.float32), (0, 0), 0.6)
            fill = np.clip(cv2.GaussianBlur(rgb, (0, 0), 1.2) + noise[..., None], 0, 255)
            if glyph:   # 긴 선(화살표·테두리) 덩어리는 원본 그대로 보호
                dd = (cv2.medianBlur(np.ascontiguousarray(jp[..., :3]), 21).astype(np.float32).mean(2) - lj) > 12
                n2, lab2, st2, _ = cv2.connectedComponentsWithStats(dd.astype(np.uint8), 8)
                longc = np.isin(lab2, [i for i in range(1, n2) if max(st2[i][2], st2[i][3]) > glyph * 2.2])
                em &= ~longc
            for kb in keepbox:   # 지우지 말 곳 — [x0,y0,x1,y1] 상자 또는 [x0,y0,x1,y1,폭] 선분(화살표)
                if len(kb) == 4:
                    em[kb[1]:kb[3], kb[0]:kb[2]] = False
                else:
                    ln = np.zeros(em.shape, np.uint8)
                    cv2.line(ln, (kb[0], kb[1]), (kb[2], kb[3]), 1, kb[4])
                    em[ln == 1] = False
            out = jp.copy()
            out[..., :3][em] = fill[em].astype(np.uint8)
            return out, reg, txt.astype(bool)
        if smooth:   # 판처럼 결이 고른 바탕: 글자 밖 픽셀을 부드럽게 이은 색 + 같은 세기의 잔결
            keep0 = (1 - cv2.dilate(em.astype(np.uint8), np.ones((5, 5), np.uint8))).astype(np.float32)
            src = jp[..., :3].astype(np.float32)
            lo = cv2.GaussianBlur(src * keep0[..., None], (0, 0), 4) / (cv2.GaussianBlur(keep0, (0, 0), 4)[..., None] + 1e-3)
            rng = np.random.default_rng(int(lo.sum()) % 99991)
            out = jp.copy()
            for r in regions:
                x0, y0 = max(0, r[0]), max(0, r[1])
                x1, y1 = min(jp.shape[1], r[2]), min(jp.shape[0], r[3])
                k = keep0[y0:y1, x0:x1] > 0
                res = (src - lo)[y0:y1, x0:x1][k]
                sd = res.std(0) if len(res) > 20 else np.array([4, 4, 4], np.float32)
                noise = rng.normal(0, 1, (y1 - y0, x1 - x0, 1)) * sd.mean() * 0.8
                noise = cv2.GaussianBlur(noise.astype(np.float32), (0, 0), 0.6)[..., None]
                patchv = np.clip(lo[y0:y1, x0:x1] + noise, 0, 255)
                m = em[y0:y1, x0:x1]
                out[y0:y1, x0:x1, :3][m] = patchv[m].astype(np.uint8)
            return out, reg, txt.astype(bool)
        keep = (1 - cv2.dilate(em.astype(np.uint8), np.ones((5, 5), np.uint8))).astype(np.float32)
        num = cv2.GaussianBlur((jp[..., :3].astype(np.float32) - cf) * keep[..., None], (0, 0), 6)
        den = cv2.GaussianBlur(keep, (0, 0), 6)[..., None] + 1e-3
        fill = np.clip(cf + num / den, 0, 255)
        out = jp.copy()
        out[..., :3][em] = fill[em].astype(np.uint8)
        return out, reg, txt.astype(bool)
    jtext = ((lr - lj) > THR) & (reg == 1)                     # 일본판만 어두움 = 일본어 글자
    if clean is not None:
        bgj = lum(clean)
        refbg = clean[..., :3].astype(np.float32)
    else:
        bgj = cv2.medianBlur(jp[..., :3], 15).astype(np.float32).mean(2)
        refbg = cv2.medianBlur(ref[..., :3], 15).astype(np.float32)
    near = cv2.dilate(jtext.astype(np.uint8), np.ones((5, 5), np.uint8)) == 1
    jdark = ((bgj - lj) > 8) & near & (reg == 1)               # 일본어 획 둘레 2px 안의 어두운 픽셀(영어와 겹친 곳 포함)
    em = (cv2.dilate((jtext | jdark).astype(np.uint8), np.ones((3, 3), np.uint8)) & reg).astype(bool)
    rtext = ((lum(np.dstack([refbg, np.full(refbg.shape[:2], 255)])) - lr) > THR)
    rtext = cv2.dilate(rtext.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    # 채움: 영어판에 글자 없는 자리는 영어판 픽셀, 있으면 깨끗한 바탕(+주변 밝기 보정)
    base = np.where(rtext[..., None], refbg, ref[..., :3].astype(np.float32))
    keep = (1 - cv2.dilate(em.astype(np.uint8), np.ones((5, 5), np.uint8))).astype(np.float32)
    diff = (jp[..., :3].astype(np.float32) - base) * keep[..., None]
    num = cv2.GaussianBlur(diff, (0, 0), 6)
    den = cv2.GaussianBlur(keep, (0, 0), 6)[..., None] + 1e-3
    fill = np.clip(base + np.where(rtext[..., None], num / den, 0), 0, 255)
    out = jp.copy()
    out[..., :3][em] = fill[em].astype(np.uint8)
    return out, reg, jtext


def ink(jp, mask, light=False):
    px = jp[..., :3][mask]
    if len(px) == 0:
        return (50, 35, 20)
    l = px.mean(1)
    if light or jp[..., 3].min() < 255:
        sel = px[l >= np.percentile(l, 85)]   # 밝은 글씨: 획 가운데(밝은 쪽)
    else:
        sel = px[l <= np.percentile(l, 10)]   # 원본 획 가운데 색
    return tuple(int(v) for v in np.median(sel, 0))


def text_rows(mask, r):
    """구역 안 일본어 획의 글줄(위·아래) 목록."""
    sub = mask[r[1]:r[3], r[0]:r[2]]
    prof = sub.sum(1)
    rows = np.where(prof > 0)[0]
    if len(rows) == 0:
        return []
    segs, start, prev = [], rows[0], rows[0]
    for y in rows[1:]:
        if y - prev > 2:
            segs.append((start, prev + 1)); start = y
        prev = y
    segs.append((start, prev + 1))
    return [(r[1] + a, r[1] + b) for a, b in segs if b - a >= 4]


def render(base, regions, size, color, jmask, stroke, outline=None, half=False, font=None, weight=None, glow=None, xscale=None):
    im = Image.fromarray(base, 'RGBA')
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    for r in regions:
        x0, y0, x1, y1, al, lines = r[:6]
        if len(r) > 6 and r[6]:   # 글줄 놓을 세로 범위를 따로 지정(지우는 구역은 그림자까지 넓고, 글줄은 원래 자리)
            ty0, ty1 = r[6]
            hh = (ty1 - ty0) / len(lines)
            rows = [(ty0 + i * hh, ty0 + (i + 1) * hh) for i in range(len(lines))]
        else:
            rows = text_rows(jmask, r)
        if len(rows) != len(lines) and not (len(r) > 6 and r[6]):          # 일본어 글줄과 수가 다르면 구역을 고르게 나눔
            hh = (y1 - y0) / len(lines)
            rows = [(y0 + i * hh, y0 + (i + 1) * hh) for i in range(len(lines))]
        for (ra, rb), t in zip(rows, lines):
            if not t:
                continue
            sz = r[9] if len(r) > 9 and r[9] else size   # 구역별 글자 크기 지정(보이는 높이 맞추기)
            while True:
                f = ImageFont.truetype(font or FONT, sz)
                if weight:
                    try:
                        f.set_variation_by_axes([weight])
                    except Exception:
                        pass
                l, tp, rr, b = f.getbbox(t)
                if rr - l <= (x1 - x0) or sz <= size * 0.8:
                    break
                sz -= 1
            l, tp, rr, b = f.getbbox(t)
            tmp = Image.new('RGBA', (rr - l + 6, b - tp + 6), (0, 0, 0, 0))
            d = ImageDraw.Draw(tmp)
            if outline:
                d.text((3 - l, 3 - tp), t, font=f, fill=tuple(outline) + (255,), stroke_width=1, stroke_fill=tuple(outline) + (255,))
            if stroke:
                d.text((3 - l, 3 - tp), t, font=f, fill=tuple(color) + (255,), stroke_width=stroke, stroke_fill=tuple(color) + (200,))
            d.text((3 - l, 3 - tp), t, font=f, fill=tuple(color) + (255,))
            if half:   # 반굵기: 가로로 1px 겹쳐 찍기
                d.text((4 - l, 3 - tp), t, font=f, fill=tuple(color) + (255,))
            if glow:   # 글자 둘레 빛·그림자: 글자 모양을 넓혀 흐리게 한 층을 밑에 깐다
                gc, gr, ga = glow[:3], glow[3], glow[4] if len(glow) > 4 else 255
                pad = gr * 3
                big = Image.new('RGBA', (tmp.width + pad * 2, tmp.height + pad * 2), (0, 0, 0, 0))
                big.alpha_composite(tmp, (pad, pad))
                a = np.asarray(big)[..., 3].astype(np.uint8)
                a = cv2.dilate(a, np.ones((gr * 2 - 1, gr * 2 - 1), np.uint8))
                a = cv2.GaussianBlur(a.astype(np.float32), (0, 0), gr * 0.8)
                a = np.clip(a * (ga / 255.0) * 1.6, 0, 255).astype(np.uint8)
                gl = np.zeros(a.shape + (4,), np.uint8); gl[..., :3] = gc; gl[..., 3] = a
                gimg = Image.fromarray(gl, 'RGBA'); gimg.alpha_composite(big)
                tmp = gimg.crop((pad - 3, pad - 3, big.width - pad + 3, big.height - pad + 3)) if False else gimg
                extra = pad
            else:
                extra = 0
            if xscale:   # 와이드 그림: 화면에서 가로로 늘어나므로 원본처럼 가로를 미리 눌러 씀
                tmp = tmp.resize((max(1, round(tmp.width * xscale)), tmp.height), Image.LANCZOS)
                extra = extra * xscale
            if tmp.width - 6 - extra * 2 > x1 - x0:
                tmp = tmp.resize((max(1, int((tmp.width - 6) * max(0.85, (x1 - x0) / (tmp.width - 6)))) + 6, tmp.height), Image.LANCZOS)
            tw = tmp.width - 6 - extra * 2
            x = x0 if al == 'L' else (x1 - tw if al == 'R' else (x0 + x1 - tw) / 2)
            if len(r) > 8 and r[8] is not None:   # 가로 중심 직접 지정
                x = r[8] - tw / 2
            cy = (ra + rb) / 2
            if al == 'J':   # 일본어 글자 덩어리의 가운데(가로·세로)에 맞춤
                ys, xs = np.where(jmask[int(ra):int(rb), x0:x1])
                if len(xs):
                    x = x0 + (xs.min() + xs.max() + 1) / 2 - tw / 2
                    cy = ra + (ys.min() + ys.max() + 1) / 2
            off = r[7] if len(r) > 7 else (0, 0)   # 사람이 지정한 미세 이동(px)
            layer.alpha_composite(tmp, (int(round(x - 3 - extra)) + off[0], int(round(cy - tmp.height / 2)) + off[1]))
    im.alpha_composite(layer)
    return np.asarray(im)


def sheet(gid, imgs, scale):
    w, h = imgs[0].shape[1], imgs[0].shape[0]
    s = Image.new('RGBA', (w * 3 + 40, h + 20), (40, 40, 48, 255))
    for i, a in enumerate(imgs):
        s.alpha_composite(Image.fromarray(a, 'RGBA'), (10 + i * (w + 10), 10))
    s = s.convert('RGB').resize((s.width * scale, s.height * scale), Image.LANCZOS if scale < 3 else Image.NEAREST)
    p = os.path.join(REV, 'cmp_%s.png' % gid)
    s.save(p)
    return p


def run(gid, c, jp):
    ref = np.asarray(Image.open(os.path.join(SRC, '%s_%s.png' % (gid, c.get('ref', 'e')))).convert('RGBA'))
    cl = np.asarray(Image.open(os.path.join(ROOT, 'work', 'gfx', c['clean'])).convert('RGBA')) if c.get('clean') else None
    light = c.get('light', False)
    er, reg, jmask = erase(jp, ref, c['regions'], cl, c.get('fill') == 'patch', c.get('all', False), c.get('fill') == 'smooth',
                           c.get('fill') == 'brighter', c.get('refclean'), light, c.get('clear', False), c.get('fill') == 'board', c.get('board_t', 16), c.get('glyph', 0), c.get('fill') == 'inpaint', c.get('wipe', []), c.get('keep', []))
    if not c.get('clear') and not light:
        despeck(er, cv2.dilate(reg, np.ones((c.get('speck_pad', 5),) * 2, np.uint8)) & cv2.erode((jp[..., 3] == 255).astype(np.uint8), np.ones((5, 5), np.uint8)), c.get('speck_max', 4), 8)
    for x0, y0, x1, y1 in c.get('mend', []):   # 구역 밖 원본 흔적(점·옅은 줄): 좌우 이웃 열 사이를 이어 메움
        lt, rt = er[y0:y1, x0 - 1, :3].astype(float), er[y0:y1, x1, :3].astype(float)
        for i, x in enumerate(range(x0, x1)):
            t = (i + 1) / (x1 - x0 + 1)
            er[y0:y1, x, :3] = (lt * (1 - t) + rt * t).round().astype(np.uint8)
    col = c.get('color') or ink(jp, jmask, light)
    out = render(er.copy(), c['regions'], c['size'], col, jmask, c.get('stroke', 0), c.get('outline'), c.get('half', False),
                 os.path.join(ROOT, 'work', 'fonts', c['font']) if c.get('font') else None, c.get('weight'), c.get('glow'), c.get('xscale'))
    return er, out, reg, col


def main():
    for gid in sys.argv[1:]:
        c = CFG[gid]
        jp0 = np.asarray(Image.open(os.path.join(SRC, gid + '_jp.png')).convert('RGBA')).copy()
        er, out, reg, col = run(gid, c, jp0)
        regall = reg.copy()
        nxt = c.get('next')
        while nxt:   # 한 그림에 성격이 다른 구역이 있으면 설정을 이어서 적용
            c2 = CFG[nxt]
            er2, out, reg2, col2 = run(gid, c2, out)
            er = np.where(reg2[..., None] == 1, er2, er)
            regall |= reg2
            nxt = c2.get('next')
        Image.fromarray(out, 'RGBA').save(os.path.join(OUT, gid + '.png'))
        Image.fromarray(er, 'RGBA').save(os.path.join(OUT, gid + '_erased.png'))
        outside = int(((er != jp0).any(2) & (regall == 0)).sum())
        sc = 2 if jp0.shape[1] > 200 else 6
        print(gid, '글자색', col, '구역 밖 변경', outside, '→', sheet(gid, [jp0, er, out], sc))


if __name__ == '__main__':
    main()
