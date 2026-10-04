"""에스코어 드림 4 깔끔하게 찍는 방법 비교(원본 일본어 줄과 함께). → work/review7/font_crisp.png"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import font_side as FS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL = 28
FONT = os.path.join(ROOT, 'work', 'fonts', 'SCDream4.otf')


def three(m, white, gray, shadow_src=None):
    """밝기 판 m(0~255) → 원본 3단계 색(흰 255·회 164·그림자 74)."""
    sh = Image.new('L', (CELL, CELL), 0); sh.paste(Image.fromarray(shadow_src if shadow_src is not None else m), (1, 1))
    s = np.asarray(sh)
    out = np.zeros((CELL, CELL, 4), np.uint8)
    w = m >= white; g = (m >= gray) & ~w; d = (s >= 110) & ~w & ~g
    out[w] = (255, 255, 255, 255); out[g] = (164, 164, 164, 255); out[d] = (74, 72, 74, 255)
    return Image.fromarray(out, 'RGBA')


def render(ch, px=22, dy=-1, mode='L'):
    f = ImageFont.truetype(FONT, px)
    m = Image.new('L', (CELL, CELL), 0); d = ImageDraw.Draw(m)
    d.fontmode = mode
    d.text((CELL // 2, CELL // 2 + 1 + dy), ch, font=f, fill=255, anchor='mm')
    return np.asarray(m)


VARS = {
    'A 지금(흰150·회70)': lambda ch: three(render(ch), 150, 70),
    'B 회색 줄임(흰120·회100)': lambda ch: three(render(ch), 120, 100),
    'C 흑백만(흰 획+그림자)': lambda ch: three(render(ch, mode='1'), 128, 256),
    'D 흑백 획+회색 테두리 1겹': None,
    'E 23px 지금 방식': lambda ch: three(render(ch, 23, -1), 150, 70),
}


def var_d(ch):
    b = render(ch, mode='1') >= 128
    import cv2
    ring = cv2.dilate(b.astype(np.uint8), np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], np.uint8)).astype(bool) & ~b
    aa = render(ch)
    m = np.where(b, 255, np.where(ring & (aa >= 60), 120, 0)).astype(np.uint8)
    return three(m, 200, 100, shadow_src=(b * 255).astype(np.uint8))


VARS['D 흑백 획+회색 테두리 1겹'] = var_d


def line(gfn, text, cm, ks, kw):
    im = Image.new('RGBA', (26 * len(text) + 12, CELL + 4), (0, 0, 0, 255)); x = 4
    for ch in text:
        if ch == ' ':
            x += 10; continue
        if 0xAC00 <= ord(ch) <= 0xD7A3:
            im.alpha_composite(gfn(ch), (x, 2)); x += 26
        else:
            c = ord(ch) if ord(ch) < 0x80 else cm[ch]; s = ks[c >> 8]; k = c & 255
            im.alpha_composite(s.crop((k % 16 * 28, k // 16 * 28, k % 16 * 28 + 28, k // 16 * 28 + 28)), (x, 2)); x += kw[c]
    return im.crop((0, 0, x + 8, CELL + 4))


def main():
    units = {u['id']: u for u in json.load(open(os.path.join(ROOT, 'work', 'text', 'units.json'), encoding='utf-8'))}
    ko = {}
    for x in os.listdir(os.path.join(ROOT, 'work', 'text', 'ko')):
        if x.endswith('.json'):
            ko.update(json.load(open(os.path.join(ROOT, 'work', 'text', 'ko', x), encoding='utf-8')))
    gm = {}
    for l in open(os.path.join(ROOT, 'work', 'glyphmap.tsv'), encoding='utf-8'):
        c = l.rstrip('\r\n').split('\t')
        if len(c) > 1 and c[1] and (c[1] not in gm or gm[c[1]] < 0x100 <= int(c[0], 16)):
            gm[c[1]] = int(c[0], 16)
    cm = {k: int(v, 16) for k, v in json.load(open(os.path.join(ROOT, 'build', 'charmap.json'), encoding='utf-8')).items()}
    js, jw = FS.sheets(os.path.join(ROOT, 'extract', 'jp', 'JFonts.tpl')), FS.widths(os.path.join(ROOT, 'extract', 'jp', 'JBtPakJS.bin'))
    ks, kw = FS.sheets(os.path.join(ROOT, 'build', 'full', 'JFonts.tpl')), FS.widths(os.path.join(ROOT, 'build', 'full', 'JBtPakJS.bin'))
    F = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 15)
    rows = []
    for i in ('cin:Act01/LEGRASSE_This_is_inspector', 'cin:Act01/ALEX_There_must_be_some'):
        ja = units[i]['ja'].replace('\n', ' ')
        rows.append(('원본', FS.render([ord(c) if ord(c) < 0x80 else gm.get(c, 0x100) for c in ja], js, jw)))
        for name, fn in VARS.items():
            rows.append((name, line(fn, ko[i].replace('\n', ' '), cm, ks, kw)))
    sc = 3; per = 1 + len(VARS)
    W = 230 + max(r.width for _, r in rows) * sc
    H = len(rows) * (CELL + 4) * sc + 2 * 20
    out = Image.new('RGB', (W, H), (34, 34, 40)); d = ImageDraw.Draw(out); y = 0
    for n, (lab, im) in enumerate(rows):
        d.text((10, y + 30), lab, font=F, fill=(160, 160, 170) if lab == '원본' else (255, 214, 120) if lab.startswith('A') else (140, 210, 255))
        out.paste(im.convert('RGB').resize((im.width * sc, im.height * sc), Image.NEAREST), (230, y))
        y += (CELL + 4) * sc + (20 if n % per == per - 1 else 0)
    p = os.path.join(ROOT, 'work', 'review7', 'font_crisp.png'); out.save(p); print(p, out.size)


if __name__ == '__main__':
    main()
