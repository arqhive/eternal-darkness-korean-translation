"""8단계 본 빌드: 번역 3,333줄 + 폰트 + 폭 표 + 그림 112장 + 무압축 우회 DOL → build/full/ (디스크 경로 그대로)
python build_full.py   (그 뒤 build_iso.py 로 ISO 재조립)

- 글자 배정: 번역에 쓰인 비ASCII 글자를 0x120부터 차례로(두 폰트·모든 묶음 같은 번호). 일본어 가나·한자 칸을 덮는다.
  한글은 맑은 고딕 그림(2단계 시험과 같은 모양), 기호(… 「」『』 ・ 　)는 JFonts 원래 글리프를 옮겨 씀.
- 폭 표(시스템 묶음 2번 블록): 한글 26, 기호는 JFonts 배치 원래 폭.
- 압축(SK_ASC) 파일은 해제본(첫 u32=길이)으로 넣는다 → DOL 무압축 우회 패치가 읽음.
"""
import collections
import hashlib
import json
import os
import shutil
import struct
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpe
import cmpr
import cmpr_full
import edtext
import patch_dol
import tpl
import txtpak
from make_test import new_body, width_block, repack, CELL, FONT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = os.path.join(ROOT, 'extract', 'jp'); DEC = os.path.join(ROOT, 'extract', 'dec', 'jp')
OUT = os.path.join(ROOT, 'build', 'full')
G = os.path.join(ROOT, 'work', 'gfx')
BASE = 0x120
LIMIT = 0x6D8                       # 두 폭 표(1752·1763칸) 안
BOOTS = ['JBootPak.bin', 'JBootPkW.bin', 'JBtPakES.bin', 'JBtPakJS.bin']
FONTS = ['JFonts.tpl', 'JfontsEAD.tpl']
GLYPH_FONT = os.path.join(ROOT, 'work', 'fonts', 'SCDream4.otf')   # 10/2 사용자 결정: 에스코어 드림 4, 힌팅 방식
GLYPH_PX = 22
HANGUL_ADV = 23   # 한글 진행 폭(글자 그림 17~21px). 10/4 사용자 결정 26→23(자간 줄임)
GLYPH_DY = -1   # 가나 칸 위치(2~24px)에 맞춤. 10/2 실기 제보(메모리 카드 상자 겹침) 뒤 글꼴별로 맞춰 정함
SYM_SRC = {'…': 0x109, '「': 0x10C, '」': 0x10D, '『': 0x10E, '』': 0x10F, '・': 0x103, '·': 0x103, '　': 0x100}


def disk(rel):
    """로컬 원본: 해제본이 있으면 해제본."""
    p = os.path.join(DEC, rel)
    return p if os.path.exists(p) else os.path.join(EX, rel)


def rel_of(locfile):
    return 'Levels/' + locfile if locfile.startswith('Level') else locfile


# ---------- 번역 ----------
def load():
    units = json.load(open(os.path.join(ROOT, 'work', 'text', 'units.json'), encoding='utf-8'))
    ko = {}
    kd = os.path.join(ROOT, 'work', 'text', 'ko')
    for x in sorted(os.listdir(kd)):
        if x.endswith('.json'):
            ko.update(json.load(open(os.path.join(kd, x), encoding='utf-8')))
    return units, ko


class Charset:
    def __init__(self, texts):
        chars = sorted({c for t in texts for c in t if ord(c) >= 0x80})
        assert BASE + len(chars) <= LIMIT, '칸 부족 %d' % len(chars)
        self.map = {c: BASE + i for i, c in enumerate(chars)}

    def encode(self, s):
        return b''.join(struct.pack('>H', ord(c) if ord(c) < 0x80 else self.map[c]) for c in s)


# ---------- 텍스트 넣기 ----------
def set_rec(tabs, ti, k, data, cs):
    it = tabs[ti][k]
    body, _ = bpe.decode(it, 4)
    nb = new_body(body, cs.encode(data))
    rec = it[:4] + bpe.encode(nb)
    chk, _ = bpe.decode(rec, 4)
    assert chk == nb, 'BPE 왕복 실패'
    tabs[ti][k] = rec


def pak_parse(d):
    n = struct.unpack('>I', d[:4])[0]
    return n, [struct.unpack('>II', d[8 + 8 * i:16 + 8 * i]) for i in range(n)]


def build_text(units, ko, cs, gfx_data):
    """반환 {디스크 상대경로: bytes}"""
    by_file = collections.defaultdict(list)
    for u in units:
        if u['id'] not in ko:
            continue
        for loc in u['locs']:
            f, path = loc.split('#')
            by_file[f].append((tuple(int(x) for x in path.split('.')), ko[u['id']]))
    out = {}
    n_rec = 0
    for f, items in sorted(by_file.items()):
        rel = rel_of(f)
        src = gfx_data.get(rel) or open(disk(rel), 'rb').read()
        name = os.path.basename(f)
        if name.startswith('JRmTxt'):
            tabs = txtpak.parse(src)
            for (ti, k), t in items:
                set_rec(tabs, ti, k, t, cs); n_rec += 1
            out[rel] = txtpak.build(tabs)
        elif name.startswith('cin'):
            repl = {}
            for (i, ti, k), t in items:
                if i not in repl:
                    repl[i] = txtpak.cin_text(src, i)
                set_rec(repl[i], ti, k, t, cs); n_rec += 1
            out[rel] = txtpak.cin_build(src, repl)
        elif name == 'JMemcardText.bin':
            tabs = txtpak.parse(struct.pack('>I', len(src)) + src)
            for (st, ti, k), t in items:
                assert st == 16
                set_rec(tabs, ti, k, t, cs); n_rec += 1
            out[rel] = txtpak.build(tabs)[4:]
        else:   # 시스템·책 묶음
            d = bytearray(src)
            n, ents = pak_parse(d)
            blocks = collections.defaultdict(list)
            for (b, ti, k), t in items:
                blocks[b].append((ti, k, t))
            repl = {}
            for b, its in blocks.items():
                o, s = ents[b]
                tabs = txtpak.parse(struct.pack('>I', s) + bytes(d[o:o + s]))
                for ti, k, t in its:
                    set_rec(tabs, ti, k, t, cs); n_rec += 1
                repl[b] = txtpak.build(tabs)[4:]
            out[rel] = (d, repl)   # 폭 표·재조립은 뒤에서
    print('텍스트 레코드', n_rec, '곳 /', len(out), '파일')
    return out


# ---------- 폰트 ----------
def glyph(ch):
    """28x28 흰 글자 + 오른쪽 아래 어두운 그림자(원본 폰트 3단계 색: 흰 255·회색 164·그림자 74)."""
    from PIL import ImageDraw, ImageFont
    f = ImageFont.truetype(GLYPH_FONT, GLYPH_PX)   # 실제 크기에서 바로 그림(힌팅이 픽셀 격자에 맞춤)
    m = Image.new('L', (CELL, CELL), 0)
    ImageDraw.Draw(m).text((CELL // 2, CELL // 2 + 1 + GLYPH_DY), ch, font=f, fill=255, anchor='mm')
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



def build_fonts(cs, files):
    jf = open(os.path.join(EX, 'JFonts.tpl'), 'rb').read()
    jimgs = list(tpl.images(jf))

    def cell_img(data, imgs, code):
        i, w, h, fmt, doff = imgs[code >> 8]
        img = tpl.decode(data, doff, w, h, fmt).convert('RGBA')
        c = code & 0xFF
        x0 = (c % 16) * CELL; y0 = h - (c // 16 + 1) * CELL
        return img.crop((x0, y0, x0 + CELL, y0 + CELL))

    for fn in FONTS:
        d = bytearray(open(os.path.join(EX, fn), 'rb').read())
        imgs = list(tpl.images(bytes(d)))
        sheets = {}
        for ch, code in cs.map.items():
            sh = code >> 8
            if sh not in sheets:
                i, w, h, fmt, doff = imgs[sh]
                sheets[sh] = tpl.decode(bytes(d), doff, w, h, fmt).convert('RGBA')
            img = sheets[sh]
            h = img.height
            c = code & 0xFF
            x0 = (c % 16) * CELL; y0 = h - (c // 16 + 1) * CELL
            if ch in SYM_SRC:
                g = cell_img(jf, jimgs, SYM_SRC[ch])            # 저장 좌표 그대로
            else:
                g = glyph(ch).transpose(Image.FLIP_TOP_BOTTOM)
            img.paste(Image.new('RGBA', (CELL, CELL), (0, 0, 0, 0)), (x0, y0))
            img.paste(g, (x0, y0))
        for sh, img in sheets.items():
            i, w, h, fmt, doff = imgs[sh]
            assert fmt == 14
            enc = cmpr_full.encode_font(np.asarray(img))   # 10/4: 원본처럼 고정 팔레트(손실 없음)
            d[doff:doff + len(enc)] = enc
        files[fn] = bytes(d)
    print('폰트', FONTS, '글자', len(cs.map), '칸 0x%X~0x%X' % (min(cs.map.values()), max(cs.map.values())))


def widths(cs):
    """JFonts 배치(JBtPakJS) 원래 폭에서 기호 폭을 가져온다."""
    d = open(os.path.join(EX, 'JBtPakJS.bin'), 'rb').read()
    o, s = struct.unpack('>II', d[24:32])
    blk = d[o:o + s]
    W = {}
    for ch, code in cs.map.items():
        W[code] = blk[5 + SYM_SRC[ch]] if ch in SYM_SRC else HANGUL_ADV
    return W


def width_set(d, W):
    o, s = struct.unpack('>II', d[8 + 16:8 + 24])
    blk = bytearray(d[o:o + s]); cnt = struct.unpack('>I', blk[:4])[0]
    for c, w in W.items():
        assert c < cnt, '폭 표 범위 밖 0x%X' % c
        blk[5 + c] = w
    return bytes(blk)


# ---------- 그림 ----------
def build_gfx():
    """반환 {디스크 상대경로: bytes} — 같은 그림의 모든 일본판 사본에 넣는다."""
    idx = [l.rstrip('\n').split('\t') for l in open(os.path.join(G, 'index.tsv'), encoding='utf-8')]
    pairs = {'g%03d' % int(p.split('\t')[0]): p.rstrip('\n').split('\t') for p in open(os.path.join(G, 'pairs.tsv'), encoding='utf-8')}
    plan = [l.rstrip('\n').split('\t') for l in open(os.path.join(G, 'plan.tsv'), encoding='utf-8')][1:]
    md5of = {(r[1], r[2], r[3]): r for r in idx}
    bymd5 = collections.defaultdict(list)
    for r in idx:
        if r[0] == 'jp':
            bymd5[r[7]].append((r[1], int(r[2]), int(r[3])))
    data = {}

    def get(cf):
        rel = cf.split('/', 2)[-1] if cf.startswith('dec/') else cf.split('/', 1)[1]
        if rel not in data:
            data[rel] = bytearray(open(os.path.join(ROOT, 'extract', cf), 'rb').read())
        return rel, data[rel]

    n = 0
    for r in plan:
        gid, kind, st = r[0], r[5], r[-1]
        n_, f, off, k = pairs[gid][:4]
        if st.startswith('확정') and kind == '번역':
            img = np.asarray(Image.open(os.path.join(G, 'done', gid + '.png')).convert('RGBA'))
            stor = np.ascontiguousarray(img[::-1])
        elif st.startswith('교체'):
            sf, so, sk = r[6].split()[0], int(r[6].split()[1].split('[')[0]), int(r[6].split('[')[1].rstrip(']'))
            sd = open(os.path.join(ROOT, 'extract', 'dec', sf), 'rb').read()[so:]
            ii = [x for x in tpl.images(sd) if x[0] == sk][0]
            stor = np.asarray(tpl.decode(sd, ii[4], ii[1], ii[2], ii[3]).convert('RGBA'))
        else:
            continue
        enc = cmpr_full.encode(stor)
        for cf, co, ck in bymd5[md5of[(f, off, k)][7]]:
            rel, d = get(cf)
            ii = [x for x in tpl.images(bytes(d[co:])) if x[0] == ck][0]
            i, w, h, fmt, doff = ii
            assert fmt == 14 and (w, h) == (stor.shape[1], stor.shape[0]), (gid, cf)
            d[co + doff:co + doff + len(enc)] = enc
            n += 1
    print('그림', n, '곳 /', len(data), '파일')
    return {k: bytes(v) for k, v in data.items()}


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    units, ko = load()
    cs = Charset(ko.values())
    gfx = build_gfx()
    files = dict(gfx)
    txt = build_text(units, ko, cs, gfx)
    W = widths(cs)
    for rel, v in txt.items():
        if isinstance(v, tuple):
            d, repl = v
            if os.path.basename(rel) in BOOTS:
                repl[2] = width_set(d, W)
            files[rel] = bytes(repack(d, repl))
        else:
            files[rel] = v
    for b in BOOTS:   # 텍스트가 없는 묶음도 폭 표는 맞춤
        if b not in txt:
            d = bytearray(files.get(b) or open(os.path.join(EX, b), 'rb').read())
            files[b] = bytes(repack(d, {2: width_set(d, W)}))
    build_fonts(cs, files)
    for rel, v in files.items():
        p = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(v)
    patch_dol.main(os.path.join(EX, 'main.dol'), os.path.join(OUT, 'main.dol'))
    json.dump({c: '%04X' % v for c, v in cs.map.items()}, open(os.path.join(OUT, '..', 'charmap.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('파일', len(files), '+ main.dol →', OUT)


if __name__ == '__main__':
    main()
