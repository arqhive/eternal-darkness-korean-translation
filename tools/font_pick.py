"""글꼴 후보 비교(10/11): 원본 일본어 자막 vs 지금(에스코어 드림 4) vs 후보 글꼴을 빌드와 같은 방식으로 찍어 나란히.
빌드 방식 = build_full.glyph(): 22px 근처 힌팅 그대로 그림, 흰 255(≥150)·회 164(≥70)·그림자 74, 한글 진행 폭 23px.
후보 글자 크기는 「한」 높이가 지금 글꼴(22px)과 같아지도록 맞춘다. 기호·영숫자는 지금 빌드 폰트 칸을 그대로 씀.
python font_pick.py → work/review7/font_pick.png"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_full as B
import font_side as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL = 28
WF = 'C:/Windows/Fonts/'; UF = os.path.join(os.environ['LOCALAPPDATA'], 'Microsoft', 'Windows', 'Fonts') + '/'
SERIF = WF + 'NotoSerifKR-VF.ttf' if os.path.exists(WF + 'NotoSerifKR-VF.ttf') else UF + 'NotoSerifKR-VF.ttf'
CANDS = [   # 10/11 본고딕 vs 본명조
    ('지금: 에스코어 드림 4', os.path.join(ROOT, 'work', 'fonts', 'SCDream4.otf'), None),
    ('본고딕 보통(400)', WF + 'NotoSansKR-VF.ttf', 400),
    ('본고딕 중간(500)', WF + 'NotoSansKR-VF.ttf', 500),
    ('본명조 보통(400)', SERIF, 400),
    ('본명조 중간(500)', SERIF, 500),
    ('본명조 반굵게(600)', SERIF, 600),
]
IDS = ['cin:Act01/LEGRASSE_Miss_Alexandra_Roivas', 'cin:Act01/LEGRASSE_This_is_inspector', 'cin:PRO/This_wretched_book']


def font(path, wght, px):
    f = ImageFont.truetype(path, px)
    if wght:
        f.set_variation_by_axes([wght])
    return f


def ink_h(f):
    m = Image.new('L', (60, 60), 0); ImageDraw.Draw(m).text((30, 30), '한', font=f, fill=255, anchor='mm')
    b = m.getbbox(); return b[3] - b[1]


def glyph(f, ch):
    m = Image.new('L', (CELL, CELL), 0)
    ImageDraw.Draw(m).text((CELL // 2, CELL // 2 + 1 + B.GLYPH_DY), ch, font=f, fill=255, anchor='mm')
    sh = Image.new('L', (CELL, CELL), 0); sh.paste(m, (1, 1))
    out = Image.new('RGBA', (CELL, CELL), (0, 0, 0, 0))
    mp, sp, op = m.load(), sh.load(), out.load()
    for y in range(CELL):
        for x in range(CELL):
            a = mp[x, y]
            if a >= 150:
                op[x, y] = (255, 255, 255, 255)
            elif a >= 70:
                op[x, y] = (164, 164, 164, 255)
            elif sp[x, y] >= 110:
                op[x, y] = (74, 72, 74, 255)
    return out


def line(f, text, ks, kw, cm):
    x = 4; parts = []
    for ch in text:
        if '가' <= ch <= '힣':
            parts.append((x, glyph(f, ch))); x += B.HANGUL_ADV
        else:
            c = ord(ch) if ord(ch) < 0x80 else cm[ch]
            s = ks[c >> 8]; k = c & 0xFF
            parts.append((x, s.crop(((k % 16) * CELL, (k // 16) * CELL, (k % 16) * CELL + CELL, (k // 16) * CELL + CELL))))
            x += kw[c] if c < len(kw) else 26
    im = Image.new('RGBA', (x + 8, CELL + 4), (0, 0, 0, 255))
    for px, g in parts:
        im.alpha_composite(g, (px, 2))
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
        if len(c) > 1 and c[1] and (c[1] not in gm or (gm[c[1]] < 0x100 <= int(c[0], 16))):
            gm[c[1]] = int(c[0], 16)
    cm = {k: int(v, 16) for k, v in json.load(open(os.path.join(ROOT, 'build', 'charmap.json'), encoding='utf-8')).items()}
    js, jw = S.sheets(os.path.join(ROOT, 'extract', 'jp', 'JFonts.tpl')), S.widths(os.path.join(ROOT, 'extract', 'jp', 'JBtPakJS.bin'))
    ks, kw = S.sheets(os.path.join(ROOT, 'build', 'full', 'JFonts.tpl')), S.widths(os.path.join(ROOT, 'build', 'full', 'JBtPakJS.bin'))
    ref = ink_h(font(CANDS[0][1], None, B.GLYPH_PX))
    fonts = []
    for lab, p, w in CANDS:
        px = min(range(16, 30), key=lambda s: (abs(ink_h(font(p, w, s)) - ref), abs(s - 22)))
        fonts.append((lab + ' %dpx' % px, font(p, w, px)))
        print(lab, px)
    LF = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 15)
    blocks = []
    for i in IDS:
        ja = units[i]['ja'].replace('\n', ' ')
        jc = [ord(ch) if ord(ch) < 0x80 else gm.get(ch, 0x100) for ch in ja]
        rows = [('원본(일본어)', S.render(jc, js, jw))]
        for lab, f in fonts:
            rows.append((lab, line(f, ko[i].replace('\n', ' '), ks, kw, cm)))
        blocks.append(rows)
    sc = 2; LW = 230
    W = LW + max(r.width for b in blocks for _, r in b) * sc
    H = sum(len(b) * (CELL + 4) * sc + 24 for b in blocks)
    out = Image.new('RGB', (W, H), (34, 34, 40)); d = ImageDraw.Draw(out); y = 0
    for b in blocks:
        for n, (lab, im) in enumerate(b):
            col = (160, 160, 170) if n == 0 else ((255, 214, 120) if n == 1 else (220, 220, 230))
            d.text((10, y + 18), lab, font=LF, fill=col)
            out.paste(im.convert('RGB').resize((im.width * sc, im.height * sc), Image.NEAREST), (LW, y))
            y += (CELL + 4) * sc
        y += 24
    p = os.path.join(ROOT, 'work', 'review7', 'font_pick.png'); out.save(p); print(p, out.size)


if __name__ == '__main__':
    main()
