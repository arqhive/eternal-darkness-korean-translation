"""원본 일본어 폰트 vs 빌드된 한글 폰트를 게임과 같은 칸·폭 표로 찍어 나란히 비교.
같은 자막 줄을 원본(일본어 글리프·원래 폭)과 번역(빌드 폰트·빌드 폭)으로 위아래 배치. → work/review7/font_side.png"""
import json, os, struct, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tpl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL = 28
IDS = ['cin:Act01/LEGRASSE_Miss_Alexandra_Roivas', 'cin:Act01/LEGRASSE_This_is_inspector', 'cin:Act01/ALEX_I_dont_understand',
       'cin:Act01/LEGRASSE_Theres_no_head', 'cin:Act01/ALEX_There_must_be_some', 'cin:PRO/I_am_Doctor', 'cin:PRO/This_wretched_book']


def sheets(path):
    d = open(path, 'rb').read()
    return {i: tpl.decode(d, o, w, h, f).transpose(Image.FLIP_TOP_BOTTOM).convert('RGBA') for i, w, h, f, o in tpl.images(d)}


def widths(path):
    d = open(path, 'rb').read()
    o, s = struct.unpack('>II', d[24:32])
    return d[o + 5:o + s]


def render(codes, sh, wd):
    x = 4; parts = []
    for c in codes:
        if c == 10:
            parts.append(None); continue
        s = sh[c >> 8]; k = c & 0xFF
        parts.append((x, s.crop(((k % 16) * CELL, (k // 16) * CELL, (k % 16) * CELL + CELL, (k // 16) * CELL + CELL))))
        x += wd[c] if c < len(wd) else 26
    W = max(8, x + 8)
    im = Image.new('RGBA', (W, CELL + 4), (0, 0, 0, 255))
    for p in parts:
        if p:
            im.alpha_composite(p[1], (p[0], 2))
    return im


def main():
    units = {u['id']: u for u in json.load(open(os.path.join(ROOT, 'work', 'text', 'units.json'), encoding='utf-8'))}
    ko = {}
    kd = os.path.join(ROOT, 'work', 'text', 'ko')
    for x in os.listdir(kd):
        if x.endswith('.json'):
            ko.update(json.load(open(os.path.join(kd, x), encoding='utf-8')))
    gm = {}
    for l in open(os.path.join(ROOT, 'work', 'glyphmap.tsv'), encoding='utf-8'):
        c = l.rstrip('\r\n').split('\t')
        if len(c) > 1 and c[1] and (c[1] not in gm or (gm[c[1]] < 0x100 <= int(c[0], 16))):   # 전각(1번 장 이후) 글리프 우선
            gm[c[1]] = int(c[0], 16)
    cm = {k: int(v, 16) for k, v in json.load(open(os.path.join(ROOT, 'build', 'charmap.json'), encoding='utf-8')).items()}
    js, jw = sheets(os.path.join(ROOT, 'extract', 'jp', 'JFonts.tpl')), widths(os.path.join(ROOT, 'extract', 'jp', 'JBtPakJS.bin'))
    ks, kw = sheets(os.path.join(ROOT, 'build', 'full', 'JFonts.tpl')), widths(os.path.join(ROOT, 'build', 'full', 'JBtPakJS.bin'))
    F = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 15)
    rows = []
    for i in IDS:
        ja = units[i]['ja'].replace('\n', ' ')
        jc = [ord(ch) if ord(ch) < 0x80 else gm.get(ch, 0x100) for ch in ja]
        kc = [ord(ch) if ord(ch) < 0x80 else cm[ch] for ch in ko[i].replace('\n', ' ')]
        rows.append(('원본', render(jc, js, jw)))
        rows.append(('한글', render(kc, ks, kw)))
    sc = 2
    W = 70 + max(r.width for _, r in rows) * sc
    H = sum((CELL + 4) * sc for _ in rows) + (len(rows) // 2) * 14
    out = Image.new('RGB', (W, H), (34, 34, 40)); d = ImageDraw.Draw(out); y = 0
    for n, (lab, im) in enumerate(rows):
        d.text((10, y + 18), lab, font=F, fill=(160, 160, 170) if lab == '원본' else (255, 214, 120))
        out.paste(im.convert('RGB').resize((im.width * sc, im.height * sc), Image.NEAREST), (70, y))
        y += (CELL + 4) * sc + (14 if n % 2 else 0)
    p = os.path.join(ROOT, 'work', 'review7', 'font_side.png'); out.save(p); print(p, out.size)
    # 글자 칸 확대(원본 가나 vs 한글) 6글자씩
    cells = [js[gm[c] >> 8].crop(((gm[c] & 255) % 16 * CELL, (gm[c] & 255) // 16 * CELL, (gm[c] & 255) % 16 * CELL + CELL, (gm[c] & 255) // 16 * CELL + CELL)) for c in 'アあ漢字です']
    cells += [ks[cm[c] >> 8].crop(((cm[c] & 255) % 16 * CELL, (cm[c] & 255) // 16 * CELL, (cm[c] & 255) % 16 * CELL + CELL, (cm[c] & 255) // 16 * CELL + CELL)) for c in '아가한글입니']
    z = Image.new('RGB', (6 * 30 * 6, 2 * 30 * 6 + 10), (80, 80, 90))
    for k, c in enumerate(cells):
        b = Image.new('RGBA', (CELL, CELL), (0, 0, 0, 255)); b.alpha_composite(c)
        z.paste(b.convert('RGB').resize((CELL * 6, CELL * 6), Image.NEAREST), ((k % 6) * 30 * 6, (k // 6) * (30 * 6 + 10)))
    p2 = os.path.join(ROOT, 'work', 'review7', 'font_cells.png'); z.save(p2); print(p2)


if __name__ == '__main__':
    main()
