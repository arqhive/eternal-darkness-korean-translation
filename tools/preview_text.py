"""빌드한 폰트(TPL)·폭 표로 문장을 게임처럼 그려 본다: python preview_text.py <시험폴더> <출력png>"""
import os
import struct
import sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpe
import edtext
import tpl
import txtpak


def sheets(path):
    d = open(path, 'rb').read()
    return [tpl.decode(d, o, w, h, f).transpose(Image.FLIP_TOP_BOTTOM) for i, w, h, f, o in tpl.images(d)]


def widths(path):
    d = open(path, 'rb').read()
    o, s = struct.unpack('>II', d[24:32])
    n = struct.unpack('>I', d[o:o + 4])[0]
    return d[o + 5:o + 5 + n]


def draw(text, sh, wd):
    codes = [struct.unpack('>H', text[i:i + 2])[0] for i in range(0, len(text), 2)]
    nl = sum(1 for c in codes if c == 0x0A)
    img = Image.new('RGBA', (1600, 32 + 28 * nl), (30, 30, 60, 255)); x = 4; y = 2
    for c in codes:
        if c == 0x0A:
            x = 4; y += 28; continue
        s, k = c >> 8, c & 0xFF
        g = sh[s].crop(((k % 16) * 28, (k // 16) * 28, (k % 16) * 28 + 28, (k // 16) * 28 + 28))
        img.alpha_composite(g, (x, y)); x += wd[c] if c < len(wd) else 28
    return img


def main(folder, out):
    sh = sheets(os.path.join(folder, 'JFonts.tpl')); wd = widths(os.path.join(folder, 'JBtPakJS.bin'))
    lines = []
    d = open(os.path.join(folder, 'Levels', 'Level00', 'JRmTxt00.cmp'), 'rb').read()
    for t in txtpak.parse(d):
        for it in t:
            if isinstance(it, tuple): continue
            body, _ = bpe.decode(it, 4)
            lab, txt = edtext.parse_body(0, body, True)
            if lab.split('/')[-1] in ('PORTRAITS', 'CLOCK', 'WINDOWS'): lines.append(txt)
    d = open(os.path.join(folder, 'Levels', 'Level00', 'cin0005.bin'), 'rb').read()
    parts = txtpak.cin_parts(d)
    for i in range(1, len(parts)):
        for t in txtpak.cin_text(d, i):
            for it in t[:3]:
                if isinstance(it, tuple): continue
                body, _ = bpe.decode(it, 4); lab, txt = edtext.parse_body(0, body, True)
                if any(txt[0::2]): lines.append(txt)
    for st, ents in edtext.tables(open(os.path.join(folder, 'JBtPakJS.bin'), 'rb').read()):
        dd = open(os.path.join(folder, 'JBtPakJS.bin'), 'rb').read()
        for o, l in ents:
            try:
                h, b = edtext.record(dd, st, o, l); lab, txt = edtext.parse_body(h, b, True)
            except Exception:
                continue
            if lab and lab.endswith('/CannotUse') and any(txt[0::2]): lines.append(txt)
    imgs = [draw(t, sh, wd) for t in lines]
    W = 1600; H = sum(i.height for i in imgs)
    s = Image.new('RGBA', (W, H)); y = 0
    for i in imgs: s.paste(i, (0, y)); y += i.height
    s.save(out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
