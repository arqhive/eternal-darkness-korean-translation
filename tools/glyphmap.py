"""일본판 폰트(JFonts.tpl) 글리프 번호 → 글자 대응표를 그림 대조로 만든다.

후보: Shift-JIS(cp932) 2바이트 글자 전부 + ASCII·반각 가나. 일본어 글꼴 여러 개로 그려
28px 칸 글리프(흰 획)와 정규화 상관계수로 비교, 가장 높은 글자를 고른다.
결과: work/glyphmap.tsv (코드, 글자, 점수, 2위 글자, 2위 점수) — 점수 낮거나 1·2위 차이 작은 것은 검토 대상.
"""
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure
import tpl

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
FONTS = ['C:/Windows/Fonts/msgothic.ttc', 'C:/Windows/Fonts/YuGothM.ttc', 'C:/Windows/Fonts/YuGothB.ttc']
N = 24  # 비교 해상도
BLUR = 1.2


def cells():
    d = open(os.path.join(ROOT, 'extract', 'jp', 'JFonts.tpl'), 'rb').read()
    sh = [tpl.decode(d, o, w, h, f).transpose(Image.FLIP_TOP_BOTTOM) for i, w, h, f, o in tpl.images(d)]
    n = len(measure.width_table(os.path.join(ROOT, 'extract', 'jp', 'JBootPak.bin')))
    out = {}
    for code in range(n):
        s, k = code >> 8, code & 0xFF
        g = sh[s].crop(((k % 16) * 28, (k // 16) * 28, (k % 16) * 28 + 28, (k // 16) * 28 + 28))
        a = np.asarray(g, dtype=np.float32)
        # 흰 획만(그림자 제외): 밝기 × 알파
        v = (a[:, :, :3].mean(axis=2) / 255.0) * (a[:, :, 3] / 255.0)
        v = np.where(v > 0.55, v, 0)
        out[code] = v
    return out


def norm_vec(img):
    """잉크 영역을 잘라 N×N 으로 맞춘 뒤 정규화(위치·크기 차이 흡수)."""
    ys, xs = np.nonzero(img > 0.2)
    if len(xs) == 0:
        return None
    crop = img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = crop.shape
    side = max(h, w)
    pad = np.zeros((side, side), np.float32)
    pad[(side - h) // 2:(side - h) // 2 + h, (side - w) // 2:(side - w) // 2 + w] = crop
    im = Image.fromarray((pad * 255).astype(np.uint8)).resize((N, N), Image.BILINEAR).filter(ImageFilter.GaussianBlur(BLUR))
    v = np.asarray(im, np.float32).ravel()
    v -= v.mean(); n = np.linalg.norm(v)
    return v / n if n else None


def frame_vec(img28):
    """칸 전체를 그대로(위치·크기 정보 유지) 비교하는 벡터 — 작은 가나 구분용."""
    im = Image.fromarray((np.clip(img28, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(BLUR))
    v = np.asarray(im, np.float32).ravel()
    v -= v.mean(); n = np.linalg.norm(v)
    return v / n if n else None


def render28(ch, font, dy):
    """게임 칸과 같은 28px 칸에 그린다(4배로 그려 줄임)."""
    im = Image.new('L', (112, 112), 0)
    ImageDraw.Draw(im).text((56, 56 + dy * 4), ch, font=font, fill=255, anchor='mm')
    return np.asarray(im.resize((28, 28), Image.LANCZOS), np.float32) / 255.0


def candidates():
    chars = []
    for hi in list(range(0x81, 0xA0)) + list(range(0xE0, 0xF0)):
        for lo in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            try:
                c = bytes([hi, lo]).decode('cp932')
            except UnicodeDecodeError:
                continue
            chars.append(c)
    chars += [chr(c) for c in range(0x21, 0x7F)]
    chars += [bytes([b]).decode('cp932') for b in range(0xA1, 0xE0)]
    return sorted(set(chars))


def _level1(ch):
    try:
        b = ch.encode('cp932')
    except UnicodeEncodeError:
        return False
    return len(b) == 1 or b < bytes([0x98, 0x73])  # 비한자·JIS 1수준


def render(ch, font):
    im = Image.new('L', (64, 64), 0)
    ImageDraw.Draw(im).text((32, 32), ch, font=font, fill=255, anchor='mm')
    return np.asarray(im, np.float32) / 255.0


KANA = [bytes([0x82, b]).decode('cp932') for b in range(0x9F, 0xF2)] +     [bytes([0x83, b]).decode('cp932') for b in list(range(0x40, 0x7F)) + list(range(0x80, 0x97))]
SMALL = 'ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ'
BIG = 'あいうえおつやゆよわアイウエオツヤユヨワカケ'
FIXED = {}
for i, ch in enumerate('、。・：？！々ー…（）「」『』０１２３４５６７８９ＡＢＫＮＯＴ'):
    FIXED[0x101 + i] = ch  # 0x100 은 빈칸
for c in range(0x20, 0x7F):
    FIXED[c] = chr(c)
for c in range(0x01, 0x20):
    FIXED[c] = bytes([0xA0 + c]).decode('cp932')
FIXED[0x09] = '™'
# 1번 장 가나(그림으로 확인, 2026-10-01): ぴ·ぷ·ヌ·ゥ·ォ 등은 폰트에 없음. 0x1B5~0x1B6 은 로마 숫자
_KANA_ROWS = ('ぁあいうえおかがきぎくぐけげこご' 'さざしじすずせぜそぞただちっつづ' 'てでとどなにぬねのはばぱひびふぶ'
              'へべぺほぼぽまみむめもゃやゅゆょ' 'よらりるれろわをんァアィイウェエ' 'オカガキギクグケゲコゴサザシジス'
              'ズセゼソゾタダチッツテデトドナニ' 'ネノハバパヒビピフブプヘベペホボ' 'ポマミムメモャヤュユョヨラリルレ'
              'ロワンヴヶⅠⅢ')
for i, ch in enumerate(_KANA_ROWS):
    FIXED[0x120 + i] = ch


def pool(code, ch):
    """폰트 장별 후보 제한: 0번=기호·라틴, 1번=가나·전각 기호·일부 한자, 2~6번=한자."""
    try:
        b = ch.encode('cp932')
    except UnicodeEncodeError:
        return False
    sheet = code >> 8
    if sheet == 0:
        return len(b) == 1 or b < bytes([0x82, 0x9F])
    if sheet == 1:  # 가나·전각 기호 + 끝부분 한자
        return len(b) == 2
    return len(b) == 2 and b >= bytes([0x88, 0x9F])


def main():
    cs = cells()
    codes = [c for c, v in cs.items() if norm_vec(v) is not None]
    G = np.stack([norm_vec(cs[c]) for c in codes])
    F = np.stack([frame_vec(cs[c]) for c in codes])
    # 게임 한자의 잉크 높이·중심(2~6번 장 중앙값) → 후보를 같은 크기·위치로 그린다
    hs = []; cy = []
    for c in codes:
        if c >= 0x200:
            ys, xs = np.nonzero(cs[c] > 0.2); hs.append(ys.max() - ys.min() + 1); cy.append((ys.max() + ys.min()) / 2)
    gh, gcy = float(np.median(hs)), float(np.median(cy))
    chars = candidates()
    best = np.full((len(codes), 2), -1.0); bestc = [['', ''] for _ in codes]
    KS = None
    for fp in FONTS:
        font = ImageFont.truetype(fp, 48)
        ref = render28('漢', ImageFont.truetype(fp, 100), 0); ys, _ = np.nonzero(ref > 0.2)
        size = int(round(100 * gh / (ys.max() - ys.min() + 1)))
        f28 = ImageFont.truetype(fp, size * 4)
        ref = render28('漢', f28, 0); ys, _ = np.nonzero(ref > 0.2); dy = gcy - (ys.max() + ys.min()) / 2
        vecs = []; fvecs = []; keep = []
        for ch in chars:
            v = norm_vec(render(ch, font))
            fv = frame_vec(render28(ch, f28, dy))
            if v is not None and fv is not None:
                vecs.append(v); fvecs.append(fv); keep.append(ch)
        C = np.stack(vecs); FC = np.stack(fvecs); masks = {}
        bonus = np.array([0.02 if _level1(ch) else 0.0 for ch in keep])
        S = G @ C.T  # 모양(잘라 맞춤) 상관계수. 작은 가나는 아래 small_kana() 에서 잉크 높이로 따로 판정
        for i in range(len(codes)):
            mask = np.array([pool(codes[i], ch) for ch in keep]) if (codes[i] >> 8) not in masks else masks[codes[i] >> 8]
            masks[codes[i] >> 8] = mask
            top = np.argsort(np.where(mask, S[i] + bonus, -9))[-2:][::-1]
            for j in top:
                ch, sc = keep[j], S[i, j] + bonus[j]
                if ch in bestc[i]:
                    k = bestc[i].index(ch); best[i, k] = max(best[i, k], sc); continue
                if sc > best[i, 0]:
                    best[i, 1], bestc[i][1] = best[i, 0], bestc[i][0]
                    best[i, 0], bestc[i][0] = sc, ch
                elif sc > best[i, 1]:
                    best[i, 1], bestc[i][1] = sc, ch
        # 1번 장 가나 순서 정렬용: 1번 장 글리프 × 가나 목록 유사도(글꼴별 최댓값)
        rows1 = [i for i, c in enumerate(codes) if 0x120 <= c < 0x200]
        pos = {ch: j for j, ch in enumerate(keep)}
        sub = np.full((len(rows1), len(KANA)), -1.0)
        for b, k in enumerate(KANA):
            if k in pos:
                sub[:, b] = S[rows1, pos[k]]
        KS = sub if KS is None else np.maximum(KS, sub)
        print(os.path.basename(fp), '완료', flush=True)
    # 1번 장 가나: Shift-JIS 순서로 놓였으므로 순서 보존 정렬(DP)로 정한다
    rows1 = [i for i, c in enumerate(codes) if 0x120 <= c < 0x200]
    # 가나 구간 = 0x120 ~ 모양 대조로 'ヶ'(없으면 'ヴ')가 나온 마지막 글리프
    end = max(k for k, i in enumerate(rows1) if bestc[i][0] in ('ヶ', 'ヴ', 'ケ')) + 1
    KSr = KS[:end]
    m, n = KSr.shape
    NEG = -1e9
    dp = np.full((m + 1, n + 1), NEG); dp[0, :] = 0
    take = np.zeros((m + 1, n + 1), bool)
    for a in range(1, m + 1):
        for b in range(1, n + 1):
            c1 = dp[a - 1, b - 1] + KSr[a - 1, b - 1]   # a번째 글리프 = b번째 가나
            c2 = dp[a, b - 1]                           # b번째 가나는 폰트에 없음
            if c1 >= c2:
                dp[a, b] = c1; take[a, b] = True
            else:
                dp[a, b] = c2
    a, b = m, n; pairs = {}
    while a > 0 and b > 0:
        if take[a, b]:
            pairs[a - 1] = b - 1; a -= 1; b -= 1
        else:
            b -= 1
    for a_, b_ in pairs.items():
        i = rows1[a_]
        if KANA[b_] != bestc[i][0]:
            bestc[i][1], best[i, 1] = bestc[i][0], best[i, 0]
        bestc[i][0] = KANA[b_]; best[i, 0] = KS[a_, b_]
    print('1번 장 가나 구간', len(pairs), '자, 0x120~0x%X' % codes[rows1[end - 1]])
    # 작은/큰 가나: 모양이 같아 잉크 높이로 정한다(같은 장 큰 가나 높이 중앙값의 0.8배 미만이면 작은 가나)
    big_h = np.median([np.ptp(np.nonzero(cs[c] > 0.2)[0]) + 1 for i, c in enumerate(codes)
                       if bestc[i][0] in 'あいうえおかきくけこアイウエオカキクケコ'])
    for i, c in enumerate(codes):
        ch = bestc[i][0]
        if ch in SMALL or ch in BIG:
            h = np.ptp(np.nonzero(cs[c] > 0.2)[0]) + 1
            small = h < 0.8 * big_h
            if small and ch in BIG:
                bestc[i][0] = SMALL[BIG.index(ch)]
            elif not small and ch in SMALL:
                bestc[i][0] = BIG[SMALL.index(ch)]
    with open(os.path.join(ROOT, 'work', 'glyphmap.tsv'), 'w', encoding='utf-8') as fo:
        for i, c in enumerate(codes):
            if c in FIXED:  # 그림으로 확인해 고정한 글자
                fo.write('%04X\t%s\t%.3f\t%s\t%.3f\n' % (c, FIXED[c], 9, '', 0)); continue
            fo.write('%04X\t%s\t%.3f\t%s\t%.3f\n' % (c, bestc[i][0], best[i, 0], bestc[i][1], best[i, 1]))
    print('글리프', len(codes))


if __name__ == '__main__':
    main()
