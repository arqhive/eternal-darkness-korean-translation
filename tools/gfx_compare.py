"""일본판에만 있는 그림(북미판 어디에도 같은 데이터 없음)을 북미판 대응 그림과 짝지어 비교 시트를 만든다.

대응: 파일 이름 대응표(FILEMAP) → 같은 TPL 순서·번호·크기 우선, 없으면 같은 크기 중 가장 비슷한 그림.
결과: work/gfx/pairs.tsv, work/gfx/sheets/sheet_##.png (왼쪽 일본판 | 오른쪽 북미판, 위아래 뒤집어 바로 보이게)
"""
import collections
import os
import re
import struct
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tpl

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
EXT = os.path.join(ROOT, 'extract')
OUT = os.path.join(ROOT, 'work', 'gfx')
FONT = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 13)


def us_file(jp_rel):
    """일본판 파일 경로 → 북미판 대응 파일 경로 후보."""
    f = jp_rel.replace('jp/', 'us/', 1)
    name = os.path.basename(f); d = os.path.dirname(f)
    m = re.match(r'(dec/)?us/Levels/Level(-?\d+)/(.*)', f)
    if m:
        dec, lv, rest = m.groups()
        if rest.startswith('J_Level'):
            return ['dec/us/Level%s.bin' % lv]
        if rest.startswith('cin'):
            cn = rest[:7]
            return ['dec/us/Chars/%s/%s' % (cn, rest), 'dec/us/Cinematics/%s' % rest, 'us/Cinematics/%s' % rest]
    table = {
        'JMnMenu.cmp': ['EMnMenu.cmp'], 'JMnMenuW.cmp': ['EMnMenu.cmp'], 'JInsane.cmp': ['EInsane.cmp'], 'JInsaneW.cmp': ['EInsane.cmp'],
        'JBkPkJES.bin': ['EBookPak.bin'], 'JBkPkJJS.bin': ['EBookPak.bin'], 'JBkPkEES.bin': ['EBookPak.bin'],
        'JBkAutoJ.tpl': ['EBookAut.tpl'], 'JBkAutoE.tpl': ['EBookAut.tpl'],
        'JBookInJ.tpl': ['EBookInv.tpl', 'EBook.tpl'], 'JBookInE.tpl': ['EBookInv.tpl', 'EBook.tpl'],
        'JWideInJ.tpl': ['EWideInv.tpl'], 'JWideInE.tpl': ['EWideInv.tpl'], 'JWideInW.tpl': ['EWideInv.tpl'], 'JWideInv.tpl': ['EWideInv.tpl'],
        'JloadJ.tpl': ['Eloading.tpl'], 'JloadE.tpl': ['Eloading.tpl'], 'JBtPakES.bin': ['EBootPak.bin'], 'JBtPakJS.bin': ['EBootPak.bin'],
        'JBootPkW.bin': ['EBootPak.bin'], 'JBootPak.bin': ['EBootPak.bin'], 'JFonts.tpl': ['EFonts.tpl'], 'JfontsEAD.tpl': ['EFonts.tpl'],
    }
    if name in table:
        return [os.path.join(d, x).replace('\\', '/') for x in table[name]]
    return [f]


def load_img(ver_rel, off, k):
    p = os.path.join(EXT, ver_rel)
    d = open(p, 'rb').read()[off:]
    for i, w, h, f, o in tpl.images(d):
        if i == k:
            try:
                return tpl.decode(d, o, w, h, f).transpose(Image.FLIP_TOP_BOTTOM).convert('RGBA')
            except Exception:
                return None


def sim(a, b):
    a = np.asarray(a.convert('L').resize((32, 32)), np.float32).ravel(); b = np.asarray(b.convert('L').resize((32, 32)), np.float32).ravel()
    a -= a.mean(); b -= b.mean()
    n = np.linalg.norm(a) * np.linalg.norm(b)
    return float(a @ b / n) if n else 0.0


def main():
    rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(OUT, 'index.tsv'), encoding='utf-8')]
    us_md5 = set(r[7] for r in rows if r[0] == 'us')
    by_file = collections.defaultdict(list)
    for r in rows:
        by_file[r[1]].append(r)
    jo = []; seen = set()
    for r in rows:
        if r[0] == 'jp' and r[7] not in us_md5 and r[7] not in seen:
            seen.add(r[7]); jo.append(r)
    pairs = []
    for r in jo:
        ver, f, off, k, w, h, fmt, md5 = r
        jimg = load_img(f, int(off), int(k))
        cands = [x for uf in us_file(f) for x in by_file.get(uf, [])]
        # 같은 TPL 순서·번호·크기
        jtpls = sorted(set(int(x[2]) for x in by_file[f]))
        best = None
        if cands:
            utpls = sorted(set(int(x[2]) for x in cands))
            ti = jtpls.index(int(off))
            same = [x for x in cands if x[3] == k and (x[4], x[5]) == (w, h) and ti < len(utpls) and int(x[2]) == utpls[ti]]
            pool = same or [x for x in cands if (x[4], x[5]) == (w, h)] or cands
            scored = []
            for x in pool[:200]:
                uimg = load_img(x[1], int(x[2]), int(x[3]))
                if uimg is not None and jimg is not None:
                    scored.append((sim(jimg, uimg) + (0.5 if x in same else 0), x, uimg))
            if scored:
                best = max(scored, key=lambda s: s[0])
        pairs.append((r, jimg, best))
    with open(os.path.join(OUT, 'pairs.tsv'), 'w', encoding='utf-8') as fo:
        for n, (r, jimg, best) in enumerate(pairs):
            u = best[1] if best else ['', '', '', '', '', '', '', '']
            fo.write('%d\t%s\t%s\t%s\t%sx%s\t%s\t%s\t%s\t%.2f\n' % (n, r[1], r[2], r[3], r[4], r[5], u[1], u[2], u[3], best[0] if best else 0))
    # 비교 시트: 한 장에 12쌍
    os.makedirs(os.path.join(OUT, 'sheets'), exist_ok=True)
    for page in range(0, len(pairs), 12):
        chunk = pairs[page:page + 12]
        W = 1000; cellh = 230
        sheet = Image.new('RGB', (W, cellh * len(chunk)), (35, 35, 45)); dr = ImageDraw.Draw(sheet)
        for i, (r, jimg, best) in enumerate(chunk):
            y = i * cellh
            dr.text((4, y + 2), '#%d  일본 %s @%s[%s] %sx%s' % (page + i, r[1].split('/', 1)[1], r[2], r[3], r[4], r[5]), font=FONT, fill=(255, 220, 120))
            if best:
                dr.text((504, y + 2), '북미 %s @%s[%s]' % (best[1][1].split('/', 1)[1], best[1][2], best[1][3]), font=FONT, fill=(140, 220, 255))
            for x0, im in ((4, jimg), (504, best[2] if best else None)):
                if im is None:
                    continue
                t = im.copy(); t.thumbnail((490, cellh - 24))
                bg = Image.new('RGBA', t.size, (90, 90, 100, 255)); bg.alpha_composite(t)
                sheet.paste(bg.convert('RGB'), (x0, y + 20))
        sheet.save(os.path.join(OUT, 'sheets', 'sheet_%02d.png' % (page // 12)))
    print('쌍', len(pairs), '시트', (len(pairs) + 11) // 12)


if __name__ == '__main__':
    main()
