"""CMPR(GC DXT1) 부분 재인코딩: 바뀐 4x4 칸만 다시 부호화하고 나머지는 원본 바이트 유지.

이미지 배열은 TPL 저장 순서 그대로(위아래 뒤집지 않은 원본 좌표)."""
import struct


def _565(c):
    r, g, b = c[:3]
    return (r >> 3) << 11 | (g >> 2) << 5 | (b >> 3)


def _un565(v):
    return ((v >> 11) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31)


def encode_sub(px):
    """px: 16개 (r,g,b,a) → 8바이트. 투명 있으면 3색+투명 모드."""
    opaque = [p for p in px if p[3] >= 128]
    trans = len(opaque) < 16
    if not opaque:
        return struct.pack('>HHI', 0, 0xFFFF, 0xFFFFFFFF)
    lum = lambda p: p[0] * 3 + p[1] * 6 + p[2]
    lo = min(opaque, key=lum); hi = max(opaque, key=lum)
    a, b = _565(lo), _565(hi)
    if trans:
        c0, c1 = min(a, b), max(a, b)
        if c0 == c1 and c1 < 0xFFFF:
            pass
        pal = [_un565(c0), _un565(c1)]
        pal.append(tuple((x + y) // 2 for x, y in zip(pal[0], pal[1])))
        n = 3
    else:
        c0, c1 = max(a, b), min(a, b)
        if c0 == c1:
            if c0 == 0:
                c0 = 1
            else:
                c1 = c0 - 1
        p0, p1 = _un565(c0), _un565(c1)
        pal = [p0, p1, tuple((2 * x + y) // 3 for x, y in zip(p0, p1)), tuple((x + 2 * y) // 3 for x, y in zip(p0, p1))]
        n = 4
    bits = 0
    for p in px:
        if p[3] < 128:
            idx = 3
        else:
            idx = min(range(n), key=lambda k: sum((p[i] - pal[k][i]) ** 2 for i in range(3)))
        bits = bits << 2 | idx
    return struct.pack('>HHI', c0, c1, bits)


def patch(data, doff, w, h, img, rects):
    """data(bytearray)의 CMPR 이미지(doff, w, h)에서 rects[(x0,y0,x1,y1)]와 겹치는 4x4 칸을 img(PIL RGBA, 원본 좌표)로 다시 부호화."""
    px = img.load()
    need = set()
    for x0, y0, x1, y1 in rects:
        for sy in range(y0 // 4, (y1 + 3) // 4):
            for sx in range(x0 // 4, (x1 + 3) // 4):
                need.add((sx, sy))
    for sx, sy in need:
        bx, by = sx // 2, sy // 2
        blk = by * (w // 8) + bx
        sub = (sy % 2) * 2 + (sx % 2)
        off = doff + blk * 32 + sub * 8
        pix = [px[sx * 4 + i, sy * 4 + j] for j in range(4) for i in range(4)]
        data[off:off + 8] = encode_sub(pix)
