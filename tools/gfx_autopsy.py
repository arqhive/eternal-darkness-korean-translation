"""부검 그림(JBkAutoJ) 한글화: 일본어 글줄 찾기 → 깨끗한 양피지로 지우기 → 한글 배치.
python gfx_autopsy.py lines <id...>        글줄 상자 찾기(확인용 그림)
python gfx_autopsy.py make <id...>         지우기·배치, 비교 시트(원본|지운 뒤|한글)
번역문: work/gfx/autopsy_ko.json  {id: [줄, 줄, ...]}  (일본어 글줄 순서와 1:1, 빈 문자열이면 그 줄 비움)
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
CLEAN = os.path.join(ROOT, 'work', 'gfx', 'autopsy_clean_paper.png')
FONT = os.path.join(ROOT, 'work', 'fonts', os.environ.get('AUTOPSY_FONT', 'YeoncheonHeomok.ttf'))
FSCALE = float(os.environ.get('AUTOPSY_FSCALE', '1.05'))
TAG = os.environ.get('AUTOPSY_TAG', '')
SPREAD = float(os.environ.get('AUTOPSY_SPREAD', '1.12'))   # 구역 안 줄 간격 배율(첫 줄 기준)
THR = 18
MARGIN = 4   # 지우는 범위 = 글자 구역 + 4px(경계에 걸친 획 끝)
USX = json.load(open(os.path.join(ROOT, 'work', 'gfx', 'autopsy_us_text.json'), encoding='utf-8'))
BOXES = json.load(open(os.path.join(ROOT, 'work', 'gfx', 'autopsy_boxes.json'), encoding='utf-8'))
REG = json.load(open(os.path.join(ROOT, 'work', 'gfx', 'autopsy_regions.json'), encoding='utf-8'))


def load(gid):
    return np.asarray(Image.open(os.path.join(SRC, gid + '_jp.png')).convert('RGB')).astype(np.int16)


def dark_mask(img, clean):
    return (clean.astype(np.int16) - img).mean(2) > THR


def find_lines(img, clean, regions, gid_override=None):
    """글자 구역(사람이 정함) 안에 온전히 들어오는 어두운 덩어리 = 글자 획. 구역 밖으로 이어지는 덩어리(그림)는 제외.
    구역마다 행 투영으로 글줄을 나눈다. 반환: 글줄 상자, 글자 획 마스크"""
    m = dark_mask(img, clean).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    small = np.zeros_like(m)
    boxes = []
    for rx0, ry0, rx1, ry1 in regions:
        reg = np.zeros_like(m)
        for i in range(1, n):
            x, y, w, h, a = st[i]
            if x >= rx0 and y >= ry0 and x + w <= rx1 and y + h <= ry1 and h <= 30:
                reg[lab == i] = 1
        small |= reg
        prof = reg.sum(1)
        rows = np.where(prof > 0)[0]
        if len(rows) == 0:
            continue
        segs = []; start = prev = rows[0]
        for r in rows[1:]:
            if r - prev > 2:
                segs.append((start, prev + 1)); start = r
            prev = r
        segs.append((start, prev + 1))
        segs2 = []
        for a, b in segs:   # 두 줄이 붙어 잡히면(높이 > 26) 투영 골에서 자른다
            while b - a > 26:
                cut = a + 14 + int(np.argmin(prof[a + 14:a + 24]))
                segs2.append((a, cut)); a = cut
            segs2.append((a, b))
        for a, b in segs2:
            if b - a < 6:
                continue
            cs = np.where(reg[a:b].sum(0) > 0)[0]
            boxes.append([int(cs.min()), int(a), int(cs.max() + 1), int(b)])
    if gid_override and gid_override in BOXES:   # 그림과 붙어 자동으로 못 잡는 글줄은 사람이 정한 상자
        boxes = BOXES[gid_override]
    return boxes, small   # 구역 순서(읽는 순서)대로


def ink_color(img, mask):
    px = img[mask.astype(bool)]
    if len(px) == 0:
        return (60, 40, 25)
    dark = px[px.mean(1) <= np.percentile(px.mean(1), 10)]   # 원본 획 가운데 색
    return tuple(int(v) for v in np.median(dark, 0))


def us_layer(gid, img, clean, regions):
    """북미판 그림을 일본판 위치에 맞춰(특징점 닮음 변환) '그림 농도' 층을 만든다. 북미판 영어 글자 덩어리는 뺀다."""
    p = os.path.join(REV, 'aff_%s.npy' % gid)
    if not os.path.exists(p):
        return None
    M = np.load(p)
    u = np.asarray(Image.open(os.path.join(SRC, gid + '_u.png')).convert('RGB')).astype(np.float32)
    cf = clean.astype(np.float32)
    R = np.clip(u / np.maximum(cf, 1), 0, 1.05)
    h, w = img.shape[:2]
    Rw = cv2.warpAffine(R, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=(1, 1, 1))
    dU = ((cf - u).mean(2) > 25).astype(np.uint8)
    dUw = cv2.warpAffine(dU, M, (w, h), flags=cv2.INTER_NEAREST)
    dJ = ((cf - img).mean(2) > 25)
    tr = np.zeros((h, w), np.uint8)
    for x0, y0, x1, y1 in regions:
        tr[max(0, y0 - 4):y1 + 4, max(0, x0 - 4):x1 + 4] = 1
    grp = cv2.dilate(dUw, np.ones((5, 9), np.uint8))
    n, lab = cv2.connectedComponents(grp, 8)
    for i in range(1, n):
        c = (lab == i)
        out = c & (dUw == 1) & (tr == 0)
        if out.sum() == 0 or (out & dJ).sum() / out.sum() < 0.35:   # 구역 안에만 있거나 일본판 그림과 안 겹침 → 북미판 영어 글자   # 일본판 그림과 안 겹침 → 북미판 영어 글자
            Rw[c] = 1.0
    for x0, y0, x1, y1 in USX.get(gid, []):   # 자동 판별이 놓친 북미판 영어 글자 자리
        Rw[y0:y1, x0:x1] = 1.0
    return Rw


def erase(img, clean, small, gid=None, regions=()):
    Rw = us_layer(gid, img, clean, regions) if gid else None
    if Rw is None:
        em = cv2.dilate(small, np.ones((3, 3), np.uint8))   # 글자 획 + 번짐 1px
        target = clean.astype(np.float32)
    else:
        reg = np.zeros(small.shape, np.uint8)
        for x0, y0, x1, y1 in regions:
            reg[max(0, y0 - MARGIN):y1 + MARGIN, max(0, x0 - MARGIN):x1 + MARGIN] = 1
        d = (clean.astype(np.int16) - img).mean(2)
        strong = ((d > THR).astype(np.uint8) & reg)
        near = cv2.dilate(strong, np.ones((7, 7), np.uint8))
        faint = ((d > 6).astype(np.uint8) & near & reg)          # 획 둘레 3px 안의 옅은 번짐
        em = cv2.dilate(strong | faint, np.ones((3, 3), np.uint8)) & reg
        target = clean.astype(np.float32) * Rw
    keep = (1 - cv2.dilate(em, np.ones((5, 5), np.uint8))).astype(np.float32)
    diff = (img - target).astype(np.float32)
    num = cv2.GaussianBlur(diff * keep[..., None], (0, 0), 6)
    den = cv2.GaussianBlur(keep, (0, 0), 6)[..., None] + 1e-3
    fill = np.clip(target + num / den, 0, 255)
    out = img.astype(np.float32).copy()
    out[em == 1] = fill[em == 1]
    # 외딴 작은 점(남은 글자 조각·종이 먼지) 지우기: 12px 이하, 큰 덩어리(그림)에서 6px 넘게 떨어진 것
    d2 = ((clean.astype(np.float32) - out).mean(2) > 10).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(d2, 8)
    d3 = ((clean.astype(np.float32) - out).mean(2) > 22).astype(np.uint8)   # 그림 = 진한 큰 덩어리
    n3, lab3, st3, _ = cv2.connectedComponentsWithStats(d3, 8)
    big = np.isin(lab3, [i for i in range(1, n3) if st3[i][4] > 40]).astype(np.uint8)
    bigz = cv2.dilate(big, np.ones((13, 13), np.uint8))
    sp = np.zeros_like(d2)
    for i in range(1, n):
        if st[i][4] <= 12:
            c = lab == i
            if not bigz[c].any():
                sp[c] = 1
    sp = cv2.dilate(sp, np.ones((3, 3), np.uint8)) & (1 - big)
    keep2 = (1 - cv2.dilate(sp | em, np.ones((5, 5), np.uint8))).astype(np.float32)
    cf = clean.astype(np.float32)   # 외딴 점은 깨끗한 양피지로(북미판 층에 같은 점이 있을 수 있음)
    num2 = cv2.GaussianBlur((out - cf) * keep2[..., None], (0, 0), 6)
    den2 = cv2.GaussianBlur(keep2, (0, 0), 6)[..., None] + 1e-3
    fill2 = np.clip(cf + num2 / den2, 0, 255)
    out[sp == 1] = fill2[sp == 1]
    erase.specks = int(sp.sum())
    return out.astype(np.uint8), em


def draw_lines(base, boxes, texts, color, regions):
    """줄마다 원본 글줄 왼쪽 끝·세로 가운데에 맞춤. 크기는 장 안에서 통일(원본 글줄 높이 중앙값 기준).
    오른쪽은 글자 구역 끝까지 쓸 수 있고, 넘치면 그 줄만 크기 80%까지 → 가로 85%까지 압축."""
    im = Image.fromarray(base).convert('RGBA')
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    hs = sorted(b[3] - b[1] for b in boxes)
    base_size = int(os.environ.get('AUTOPSY_SIZE', '20'))   # 부검 그림 14장 공통 글자 크기(px)
    for (x0, y0, x1, y1), t in zip(boxes, texts):
        if not t:
            continue
        cx, cyy = (x0 + x1) / 2, (y0 + y1) / 2
        reg = min(regions, key=lambda r: 0 if (r[0] <= cx < r[2] and r[1] <= cyy < r[3]) else 1 + abs(r[1] - y0))
        limit = min(reg[2], im.width - 3) - x0
        size = base_size
        while True:
            f = ImageFont.truetype(FONT, size)
            l, tp, r, b = f.getbbox(t)
            if r - l <= limit or size <= base_size * 0.8:
                break
            size -= 1
        l, tp, r, b = f.getbbox(t)
        tmp = Image.new('RGBA', (r - l + 6, b - tp + 6), (0, 0, 0, 0))
        dd = ImageDraw.Draw(tmp)
        dd.text((3 - l, 3 - tp), t, font=f, fill=color + (255,))
        dd.text((4 - l, 3 - tp), t, font=f, fill=color + (255,))   # 반굵기(가로 1px 겹쳐 찍기), 책 화면과 같은 설정
        if tmp.width - 6 > limit:
            sc = max(0.85, limit / (tmp.width - 6))
            tmp = tmp.resize((int(tmp.width * sc), tmp.height), Image.LANCZOS)
        first = min((b for b in boxes if reg[0] <= (b[0] + b[2]) / 2 < reg[2] and reg[1] - 4 <= (b[1] + b[3]) / 2 < reg[3] + 4), key=lambda b: b[1])
        fc = (first[1] + first[3]) / 2
        cy = fc + ((y0 + y1) / 2 - fc) * SPREAD
        layer.alpha_composite(tmp, (x0 - 3, int(cy - tmp.height / 2)))
    im.alpha_composite(layer)
    return np.asarray(im.convert('RGB'))


def sheet(gid, a, b, c, scale=2):
    ims = [Image.fromarray(x) for x in (a, b, c)]
    w, h = ims[0].size
    s = Image.new('RGB', (w * 3 + 40, h + 20), (25, 25, 30))
    for i, im in enumerate(ims):
        s.paste(im, (10 + i * (w + 10), 10))
    s = s.resize((s.width * scale, s.height * scale), Image.LANCZOS)
    os.makedirs(REV, exist_ok=True)
    p = os.path.join(REV, 'cmp_%s%s.png' % (gid, TAG))
    s.save(p)
    return p


def main():
    cmd, ids = sys.argv[1], sys.argv[2:]
    clean = np.asarray(Image.open(CLEAN).convert('RGB')).astype(np.int16)
    if cmd == 'lines':
        for gid in ids:
            img = load(gid)
            boxes, small = find_lines(img, clean, REG[gid], gid)
            vis = Image.fromarray(img.astype(np.uint8)).convert('RGB')
            d = ImageDraw.Draw(vis)
            for i, b in enumerate(boxes):
                d.rectangle(b, outline=(255, 0, 0)); d.text((b[0] - 12, b[1]), str(i), fill=(255, 255, 0))
            vis.resize((vis.width * 2, vis.height * 2)).save(os.path.join(REV, 'lines_%s.png' % gid))
            print(gid, len(boxes), boxes)
        return
    ko = json.load(open(os.path.join(ROOT, 'work', 'gfx', 'autopsy_ko.json'), encoding='utf-8'))
    os.makedirs(OUT, exist_ok=True)
    for gid in ids:
        img = load(gid)
        boxes, small = find_lines(img, clean, REG[gid], gid)
        texts = ko[gid]
        assert len(texts) == len(boxes), (gid, len(texts), len(boxes))
        col = ink_color(img, small)
        er, em = erase(img, clean, small, gid, REG[gid])
        out = draw_lines(er, boxes, texts, col, REG[gid])
        Image.fromarray(out).save(os.path.join(OUT, gid + TAG + '.png'))
        Image.fromarray(er).save(os.path.join(OUT, gid + '_erased.png'))
        region = np.zeros(em.shape, bool)
        for x0, y0, x1, y1 in REG[gid]:
            region[max(0, y0 - MARGIN):y1 + MARGIN, max(0, x0 - MARGIN):x1 + MARGIN] = True
        outside = int(((er != img.astype(np.uint8)).any(2) & ~region).sum())
        print(gid, '글줄', len(boxes), '지운 픽셀', int(em.sum()), '외딴 점', erase.specks, '구역 밖 변경(점 제외)', outside - erase.specks, '잉크색', col,
              '→', sheet(gid, img.astype(np.uint8), er, out))


if __name__ == '__main__':
    main()
