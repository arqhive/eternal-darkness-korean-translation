"""닫는 부호 띄우기 미리보기(10/11): 지금 빌드(띄우기 전) vs PUNCT_PAD 적용. 빌드 없이 build/full 폰트 칸으로 찍음.
→ work/review7/punct_preview.png"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_full as B
import font_side as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL = 28
ks = S.sheets(os.path.join(ROOT, 'build', 'full', 'JFonts.tpl'))
kw = S.widths(os.path.join(ROOT, 'build', 'full', 'JBtPakJS.bin'))
cm = {k: int(v, 16) for k, v in json.load(open(os.path.join(ROOT, 'build', 'charmap.json'), encoding='utf-8')).items()}
LINES = ['로드아일랜드주 경찰의 르그라스 경감입니다.', '그럴 리가… 할아버지, 정말요?!', '「영원한 어둠의 서」를 찾았다. 그래, 이거야!', '좋아. 다음은 지하실로 가자, 서둘러야 해.']


def cell(code):
    s = ks[code >> 8]; k = code & 0xFF
    return s.crop(((k % 16) * CELL, (k // 16) * CELL, (k % 16) * CELL + CELL, (k // 16) * CELL + CELL))


def render(text, pad):
    x = 4; parts = []
    for ch in text:
        if ch == ' ':
            x += kw[32]; continue
        c = ord(ch) if ord(ch) < 0x80 else cm[ch]
        g = cell(c); w = kw[c] if c < len(kw) else 26
        if pad and (ch in B.PUNCT_ASCII or ch in B.PUNCT_SYM):
            g = B.pad_right(g); w += B.PUNCT_PAD
        parts.append((x, g)); x += w
    im = Image.new('RGBA', (x + 8, CELL + 4), (0, 0, 0, 255))
    for px, g in parts:
        im.alpha_composite(g, (px, 2))
    return im


rows = []
for t in LINES:
    rows += [('지금', render(t, False)), ('띄움 %dpx' % B.PUNCT_PAD, render(t, True))]
sc = 3; LW = 110
W = LW + max(r.width for _, r in rows) * sc
out = Image.new('RGB', (W, len(rows) * (CELL + 4) * sc + (len(rows) // 2) * 16), (34, 34, 40))
d = ImageDraw.Draw(out); F = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 16); y = 0
for n, (lab, im) in enumerate(rows):
    d.text((10, y + 30), lab, font=F, fill=(160, 160, 170) if n % 2 == 0 else (255, 214, 120))
    out.paste(im.convert('RGB').resize((im.width * sc, im.height * sc), Image.NEAREST), (LW, y))
    y += (CELL + 4) * sc + (16 if n % 2 else 0)
p = os.path.join(ROOT, 'work', 'review7', 'punct_preview.png'); out.save(p); print(p, out.size)
