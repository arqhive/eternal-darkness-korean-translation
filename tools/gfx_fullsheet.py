"""최종 리뷰용: 원본 | 번역 전체 크기 나란히(작은 그림은 배율 키움). python gfx_fullsheet.py 이름 g001 g002 ..."""
import os, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, 'work', 'gfx')
F = ImageFont.truetype(os.path.join(ROOT, 'work', 'fonts', 'NotoSansKR-VF.ttf'), 14)


def pair(g):
    ims = []
    for p in ('src/%s_jp.png' % g, 'done/%s.png' % g):
        a = Image.open(os.path.join(G, p)).convert('RGBA')
        b = Image.new('RGBA', a.size, (60, 60, 70, 255)); b.alpha_composite(a)
        ims.append(b.convert('RGB'))
    w = ims[0].width
    sc = 1 if w >= 300 else (2 if w >= 120 else 3)
    return [im.resize((im.width * sc, im.height * sc), Image.NEAREST) for im in ims], sc


def main():
    name, ids = sys.argv[1], sys.argv[2:]
    tiles = []
    for g in ids:
        (a, b), sc = pair(g)
        t = Image.new('RGB', (a.width * 2 + 24, a.height + 22), (24, 24, 28))
        ImageDraw.Draw(t).text((4, 2), '%s  원본 | 번역 (%d배)' % (g, sc), font=F, fill=(220, 220, 220))
        t.paste(a, (0, 22)); t.paste(b, (a.width + 24, 22))
        tiles.append(t)
    W = max(t.width for t in tiles)
    cols = max(1, min(3, 1800 // W))
    rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    H = sum(max(t.height for t in r) + 10 for r in rows)
    s = Image.new('RGB', (cols * (W + 14), H), (40, 40, 44)); y = 0
    for r in rows:
        x = 0
        for t in r:
            s.paste(t, (x, y)); x += W + 14
        y += max(t.height for t in r) + 10
    out = os.path.join(G, 'review6', 'final_%s.png' % name)
    s.save(out); print(out, s.size)


if __name__ == '__main__':
    main()
