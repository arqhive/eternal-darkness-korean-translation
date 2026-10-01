"""폰트 고르기용 비교 시트: 원본 일본어 자막 글리프(JFonts) vs 한글 후보 글꼴(게임과 같은 28칸·흰 글자·회색 가장자리·그림자 방식).
python font_compare.py → work/review7/font_compare.png"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tpl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL = 28
WF = 'C:/Windows/Fonts/'; UF = os.path.join(os.environ['LOCALAPPDATA'], 'Microsoft', 'Windows', 'Fonts') + '/'
CANDS = [   # 10/2 고딕만, 프리텐다드 추가(PC에는 Bold만 설치됨)
    ('지금: 맑은 고딕', WF + 'malgun.ttf', None, 23),
    ('맑은 고딕 Semilight', WF + 'malgunsl.ttf', None, 23),
    ('맑은 고딕 굵게', WF + 'malgunbd.ttf', None, 23),
    ('본고딕 보통(400)', WF + 'NotoSansKR-VF.ttf', 400, 23),
    ('본고딕 중간(500)', WF + 'NotoSansKR-VF.ttf', 500, 23),
    ('본고딕 굵게(700)', WF + 'NotoSansKR-VF.ttf', 700, 23),
    ('프리텐다드 Bold', UF + 'Pretendard-Bold.otf', None, 23),
    ('나눔스퀘어 R', UF + 'NanumSquareR.ttf', None, 23),
    ('나눔스퀘어 B', UF + 'NanumSquareB.ttf', None, 23),
    ('에스코어 드림 4', UF + 'SCDream4.otf', None, 22),
    ('에스코어 드림 5', UF + 'SCDream5.otf', None, 22),
    ('G마켓 산스 Medium', UF + 'GmarketSansMedium.otf', None, 22),
    ('KoPub 돋움 Bold', UF + 'KoPubWorld-Dotum-Bold.otf', None, 23),
    ('굴림', WF + 'gulim.ttc', None, 23),
]
KO = '알렉산드라 로이바스 씨입니까? 할아버지는 어디 계시죠.'
JA_CODES = None   # 원본: 같은 뜻 일본어 자막을 JFonts 칸에서 그대로 찍음
JA = 'アレキサンドラ・ロイヴァスさんですか？祖父はどこに'


def glyph(ch, path, wgt, px, hint=False):
    S = 1 if hint else 4   # 힌팅: 실제 크기에서 바로 그려 FreeType 힌팅이 픽셀 격자에 맞추게 함
    f = ImageFont.truetype(path, px * S)
    if wgt:
        try:
            f.set_variation_by_axes([wgt])
        except Exception:
            pass
    m = Image.new('L', (CELL * S, CELL * S), 0)
    ImageDraw.Draw(m).text((CELL * S // 2, CELL * S // 2 + S - 3 * S), ch, font=f, fill=255, anchor='mm')
    if S > 1:
        m = m.resize((CELL, CELL), Image.LANCZOS)
    sh = Image.new('L', (CELL, CELL), 0); sh.paste(m, (1, 1))
    out = Image.new('RGBA', (CELL, CELL), (0, 0, 0, 0))
    mp, sp, op = m.load(), sh.load(), out.load()
    for y in range(CELL):
        for x in range(CELL):
            a = mp[x, y]
            if a >= 150: op[x, y] = (255, 255, 255, 255)
            elif a >= 70: op[x, y] = (164, 164, 164, 255)
            elif sp[x, y] >= 110: op[x, y] = (74, 72, 74, 255)
    return out


def jp_line():
    gm = {}
    for l in open(os.path.join(ROOT, 'work', 'glyphmap.tsv'), encoding='utf-8'):
        c = l.rstrip('\r\n').split('\t')
        if len(c) > 1 and c[1] and c[1] not in gm:
            gm[c[1]] = int(c[0], 16)
    d = open(os.path.join(ROOT, 'extract', 'jp', 'JFonts.tpl'), 'rb').read()
    sheets = {i: tpl.decode(d, o, w, h, f).transpose(Image.FLIP_TOP_BOTTOM).convert('RGBA') for i, w, h, f, o in tpl.images(d)}
    cells = []
    for ch in JA:
        code = gm.get(ch)
        if code is None:
            cells.append(None); continue
        s = sheets[code >> 8]; c = code & 0xFF
        cells.append(s.crop(((c % 16) * CELL, (c // 16) * CELL, (c % 16) * CELL + CELL, (c // 16) * CELL + CELL)))
    return cells


def line_img(cells, adv=26, space=10):
    W = sum(space if c is None else adv for c in cells) + 10
    im = Image.new('RGBA', (W, CELL + 4), (0, 0, 0, 255))
    x = 4
    for c in cells:
        if c is None:
            x += space; continue
        im.alpha_composite(c, (x, 2)); x += adv
    return im


def main():
    F = ImageFont.truetype(WF + 'malgun.ttf', 15)
    pick = ['지금: 맑은 고딕', '맑은 고딕 Semilight', '본고딕 보통(400)', '본고딕 중간(500)', '프리텐다드 Bold',
            '나눔스퀘어 R', '에스코어 드림 4', '굴림']
    rows = [('원본 일본어(JFonts)', line_img(jp_line()))]
    for name, path, wgt, px in CANDS:
        if name not in pick or not os.path.exists(path):
            continue
        for hint in (False, True):
            cells = [None if ch == ' ' else glyph(ch, path, wgt, px, hint) for ch in KO]
            rows.append(('%s — %s' % (name.replace('지금: ', ''), '힌팅' if hint else '지금 방식'), line_img(cells)))
    sc = 2
    W = 260 + max(r.width for _, r in rows) * sc
    H = len(rows) * (CELL + 4) * sc + 10 + (len(rows) // 2) * 6
    out = Image.new('RGB', (W, H), (30, 30, 34))
    d = ImageDraw.Draw(out)
    y = 5
    for i, (name, im) in enumerate(rows):
        if i and i % 2 == 1:
            y += 6
        d.text((8, y + 18), name, font=F, fill=(255, 220, 120) if '힌팅' in name else (230, 230, 230))
        out.paste(im.convert('RGB').resize((im.width * sc, im.height * sc), Image.NEAREST), (260, y))
        y += (CELL + 4) * sc
    p = os.path.join(ROOT, 'work', 'review7', 'font_compare_hint.png')
    out.save(p); print(p, out.size)


if __name__ == '__main__':
    main()
