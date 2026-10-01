"""그래픽 전수 조사: 두 판의 모든 파일(해제본 포함)에서 TPL(표식 00 20 AF 30)을 찾아 이미지 목록을 만든다.

결과: work/gfx/index.tsv  (판, 파일, TPL 오프셋, 번호, 폭, 높이, 형식, 데이터 md5)
그림 저장은 gfx_compare.py 에서 필요한 것만 한다.
"""
import hashlib
import os
import struct
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MAGIC = b'\x00\x20\xaf\x30'
BPP = {0: 4, 1: 8, 2: 8, 3: 16, 4: 16, 5: 16, 6: 32, 8: 4, 9: 8, 10: 16, 14: 4}
BLK = {0: (8, 8), 1: (8, 4), 2: (8, 4), 3: (4, 4), 4: (4, 4), 5: (4, 4), 6: (4, 4), 8: (8, 8), 9: (8, 4), 10: (4, 4), 14: (8, 8)}
SKIP_EXT = ('.aud', '.avi', '.h4m', '.ssm', '.dsp')


def data_size(w, h, fmt):
    bw, bh = BLK[fmt]
    return ((w + bw - 1) // bw * bw) * ((h + bh - 1) // bh * bh) * BPP[fmt] // 8


def tpls(d):
    i = d.find(MAGIC)
    while i >= 0:
        try:
            n, tbl = struct.unpack('>II', d[i + 4:i + 12])
            if 0 < n < 512 and tbl == 12:
                imgs = []
                for k in range(n):
                    io, po = struct.unpack('>II', d[i + tbl + 8 * k:i + tbl + 8 * k + 8])
                    h, w, fmt, doff = struct.unpack('>HHII', d[i + io:i + io + 12])
                    if fmt not in BPP or not (0 < w <= 1024 and 0 < h <= 1024):
                        raise ValueError
                    sz = data_size(w, h, fmt)
                    if i + doff + sz > len(d):
                        raise ValueError
                    imgs.append((k, w, h, fmt, doff, sz))
                yield i, imgs
        except (ValueError, struct.error):
            pass
        i = d.find(MAGIC, i + 4)


def files(ver):
    for base in [os.path.join(ROOT, 'extract', ver), os.path.join(ROOT, 'extract', 'dec', ver)]:
        for r, ds, fs in os.walk(base):
            for f in fs:
                p = os.path.join(r, f)
                if f.lower().endswith(SKIP_EXT):
                    continue
                rel = os.path.relpath(p, os.path.join(ROOT, 'extract')).replace('\\', '/')
                yield rel, p


def main():
    os.makedirs(os.path.join(ROOT, 'work', 'gfx'), exist_ok=True)
    n = 0
    with open(os.path.join(ROOT, 'work', 'gfx', 'index.tsv'), 'w', encoding='utf-8') as fo:
        for ver in ('jp', 'us'):
            for rel, p in files(ver):
                with open(p, 'rb') as f:
                    d = f.read()
                if d[:8] == b'*SK_ASC*' or MAGIC not in d:
                    continue
                for off, imgs in tpls(d):
                    for k, w, h, fmt, doff, sz in imgs:
                        md5 = hashlib.md5(d[off + doff:off + doff + sz]).hexdigest()
                        fo.write('%s\t%s\t%d\t%d\t%d\t%d\t%d\t%s\n' % (ver, rel, off, k, w, h, fmt, md5)); n += 1
            print(ver, '완료', n, flush=True)


if __name__ == '__main__':
    main()
