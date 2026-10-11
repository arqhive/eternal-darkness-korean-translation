"""타이틀 메뉴 맞춤(10/12): 게임이 g123 배경 위에 덮어 그리는 밝은 메뉴 그림(g124 시작하기·g129 불러오기·g130 옵션)의
글자를 새 배경(GPT) 글씨 자리로 옮긴다. 덮는 그림 칸·화면 원점은 그대로, 칸 안에서 글자만 (dx, dy) 이동.
dx, dy 는 배경 글씨(어두운 바탕 위 약간 밝은 획)와 덮는 글자 모양의 상관이 가장 큰 곳으로 찾는다.
python title_align.py            → 미리보기 work/review7/title_align.png (바꾸지 않음)
python title_align.py --write    → work/gfx/done/g124·g129·g130.png 를 옮긴 것으로(이전 것은 work/GPT/이전/)
"""
import os, shutil, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, 'work', 'gfx')
SPRITES = {'g124': (541, 243), 'g129': (532, 279), 'g130': (549, 313)}   # 화면 원점(gfx_title 과 같음)


def load(p):
    return np.asarray(Image.open(p).convert('RGBA')).astype(np.float32)


def find(bg, spr, ox, oy, R=24):
    L = bg[..., :3].mean(2)
    h, w = spr.shape[:2]
    sm = ((spr[..., :3].mean(2) > 150) & (spr[..., 3] > 100)).astype(np.float32)   # 글자 획
    ys, xs = np.nonzero(sm)
    best = None
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            yy, xx = ys + oy + dy, xs + ox + dx
            ok = (yy >= 1) & (yy < L.shape[0] - 1) & (xx >= 1) & (xx < L.shape[1] - 1)
            if ok.mean() < 0.99:
                continue
            v = L[yy[ok], xx[ok]]
            # 획 자리가 둘레(위아래 3px)보다 밝을수록 좋음
            ring = (L[np.clip(yy[ok] - 3, 0, None), xx[ok]] + L[np.clip(yy[ok] + 3, None, L.shape[0] - 1), xx[ok]]) / 2
            sc = float((v - ring).mean())
            if best is None or sc > best[0]:
                best = (sc, dx, dy)
    return best


def shift(spr, dx, dy):
    """칸 안에서 (dx, dy) 이동, 비는 자리는 가장자리 픽셀로 채움(칸 바탕이 불투명한 그림)."""
    h, w = spr.shape[:2]; P = 32
    pad = np.pad(spr, ((P, P), (P, P), (0, 0)), mode='edge')
    return pad[P - dy:P - dy + h, P - dx:P - dx + w]


def compose(bg, sprs):
    """게임처럼 밝은 부분만 더함(가산 합성, 검은 바탕은 안 보임)."""
    out = bg[..., :3].copy()
    for g, sp in sprs.items():
        ox, oy = SPRITES[g]; h, w = sp.shape[:2]
        out[oy:oy + h, ox:ox + w] = np.clip(out[oy:oy + h, ox:ox + w] + sp[..., :3] * (sp[..., 3:4] / 255), 0, 255)
    return Image.fromarray(out.astype(np.uint8), 'RGB').convert('RGBA')


def main(write):
    bg = load(os.path.join(G, 'done', 'g123.png'))
    cur = {g: load(os.path.join(G, 'done', g + '.png')) for g in SPRITES}
    new = {}
    for g, (ox, oy) in SPRITES.items():
        sc, dx, dy = find(bg, cur[g], ox, oy)
        print(g, '옮김 dx %+d dy %+d (점수 %.1f)' % (dx, dy, sc))
        s = shift(cur[g], dx, dy)
        bright = lambda a: ((a[..., :3].mean(2) > 40) & (a[..., 3] > 0)).sum()
        lost = bright(cur[g]) - bright(s)
        assert abs(lost) <= 3, '%s: 옮기면 글자·빛이 칸 밖으로 %d px 잘림' % (g, lost)
        new[g] = s
    # 미리보기: 배경만 / 지금 덮개 / 옮긴 덮개 (메뉴 부분 3배)
    box = (500, 230, 720, 380)
    tiles = [('새 배경만', Image.fromarray(bg.astype(np.uint8), 'RGBA'))]
    for g, lab in (('g124', '시작하기'), ('g129', '불러오기'), ('g130', '옵션')):
        tiles += [('지금: %s 커서' % lab, compose(bg, {g: cur[g]})), ('옮김: %s 커서' % lab, compose(bg, {g: new[g]}))]
    F = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 18)
    W, H = (box[2] - box[0]) * 2, (box[3] - box[1]) * 2
    cols = 3; rows = (len(tiles) + cols - 1) // cols
    out = Image.new('RGB', (cols * (W + 10) + 10, rows * (H + 34)), (34, 34, 40)); d = ImageDraw.Draw(out)
    for i, (lab, im) in enumerate(tiles):
        x, y = 10 + (i % cols) * (W + 10), (i // cols) * (H + 34)
        out.paste(im.crop(box).convert('RGB').resize((W, H), Image.NEAREST), (x, y + 30))
        d.text((x, y + 4), lab, font=F, fill=(255, 214, 120))
    p = os.path.join(ROOT, 'work', 'review7', 'title_align.png'); out.save(p); print(p)
    if write:
        os.makedirs(os.path.join(ROOT, 'work', 'GPT', '이전'), exist_ok=True)
        for g, s in new.items():
            dst = os.path.join(G, 'done', g + '.png')
            bk = os.path.join(ROOT, 'work', 'GPT', '이전', g + '.png')
            if not os.path.exists(bk):
                shutil.copy2(dst, bk)
            Image.fromarray(s.astype(np.uint8), 'RGBA').save(dst)
        print('덮는 그림 3장 저장')


if __name__ == '__main__':
    main('--write' in sys.argv)
