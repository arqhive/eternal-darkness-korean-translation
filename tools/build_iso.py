"""GC ISO 재조립: 원본을 통째로 복사한 뒤 바뀐 파일만 덮어쓴다(바뀌지 않은 파일·패딩은 원본 그대로)(음성 32KB 정렬·읽기 위치 보존),
바뀐 파일은 원래 자리에 들어가면 제자리, 커졌으면 디스크 뒤쪽 빈 영역에 32바이트 정렬로 넣는다.

사용: python build_iso.py <원본.iso> <출력.iso> [--dol main.dol] [--repdir DIR] [--rep 디스크경로=로컬파일 ...]
  --repdir DIR : DIR 아래 같은 상대경로(예: Data/Strings/x.str) 파일이 있으면 교체
"""
import argparse
import os
import shutil
import struct

DISC_SIZE = 1459978240


def read_fst(f):
    f.seek(0)
    h = f.read(0x440)
    dol_off, fst_off, fst_size = struct.unpack('>III', h[0x420:0x42C])
    f.seek(fst_off)
    fst = bytearray(f.read(fst_size))
    n = struct.unpack('>I', fst[8:12])[0]
    strtab = bytes(fst[n * 12:])
    ents = []
    stack = [(n, '')]
    for i in range(1, n):
        while i >= stack[-1][0]:
            stack.pop()
        no = struct.unpack('>I', fst[i * 12:i * 12 + 4])[0] & 0xFFFFFF
        name = strtab[no:strtab.index(b'\0', no)].decode('shift_jis')
        a, b = struct.unpack('>II', fst[i * 12 + 4:i * 12 + 12])
        p = stack[-1][1] + name
        if fst[i * 12]:
            stack.append((b, p + '/'))
        else:
            ents.append((i, p, a, b))
    return dol_off, fst_off, fst, ents


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--dol'); ap.add_argument('--repdir')
    ap.add_argument('--rep', nargs='*', default=[])
    ap.add_argument('--pack', action='store_true', help='교체 파일 자리를 모두 비우고(+뒤쪽 빈 영역) 큰 파일부터 가장 잘 맞는 빈자리에 다시 배치')
    a = ap.parse_args()
    rep = dict(r.split('=', 1) for r in a.rep)

    f = open(a.src, 'rb')
    dol_off, fst_off, fst, ents = read_fst(f)
    f.close()
    ents.sort(key=lambda e: e[2])
    first = ents[0][2]
    shutil.copyfile(a.src, a.dst)  # 원본 통째 복사 → 파일 사이 패딩까지 보존
    out = open(a.dst, 'r+b')
    if a.dol:
        dol = open(a.dol, 'rb').read()
        assert dol_off + len(dol) <= fst_off, 'DOL 이 FST 를 덮음'
        out.seek(dol_off); out.write(dol)
    # 빈 영역: 마지막 파일 뒤 ~ 디스크 끝(일본판 약 55MB). 앞쪽은 FST 바로 뒤에 첫 파일이 붙어 있어 없음
    free_pos = (max(e[2] + e[3] for e in ents) + 0x7FFF) & ~0x7FFF
    free_end = DISC_SIZE
    changed = moved = 0
    if a.pack:   # 10/2: 무압축 파일이 커져 뒤쪽 빈 영역(55MB)만으로 모자람 → 바뀌는 파일 자리를 모두 비워 다시 배치
        srcs = {}
        for i, p, off, size in ents:
            s_ = rep.get(p) or (a.repdir and os.path.isfile(os.path.join(a.repdir, p)) and os.path.join(a.repdir, p))
            if s_:
                srcs[i] = (p, s_)
        regions = []
        for n, (i, p, off, size) in enumerate(ents):
            if i in srcs:
                nxt = ents[n + 1][2] if n + 1 < len(ents) else free_end
                regions.append([off, nxt])
        regions.append([free_pos, free_end]); regions.sort()
        free = []
        for x0, x1 in regions:
            if free and x0 <= free[-1][1]:
                free[-1][1] = max(free[-1][1], x1)
            else:
                free.append([x0, x1])
        info = {i: (p, s_, os.path.getsize(s_)) for i, (p, s_) in srcs.items()}
        for i, (p, s_, sz) in sorted(info.items(), key=lambda x: -x[1][2]):
            best = None
            for r in free:
                pos0 = (r[0] + 31) & ~31
                if pos0 + sz <= r[1] and (best is None or r[1] - pos0 < best[1] - ((best[0] + 31) & ~31)):
                    best = r
            assert best is not None, '빈자리 부족: ' + p
            pos = (best[0] + 31) & ~31; best[0] = pos + sz
            out.seek(pos); out.write(open(s_, 'rb').read())
            orig = struct.unpack('>I', fst[i * 12 + 4:i * 12 + 8])[0]
            struct.pack_into('>II', fst, i * 12 + 4, pos, sz)
            changed += 1; moved += pos != orig
        out.seek(fst_off); out.write(fst); out.close()
        print(f'교체 {changed}개(자리 옮김 {moved}개), 남은 빈자리 {sum(r[1] - r[0] for r in free)/1e6:.1f}MB')
        return
    for i, p, off, size in ents:
        src = rep.get(p)
        if src is None and a.repdir and os.path.isfile(os.path.join(a.repdir, p)):
            src = os.path.join(a.repdir, p)
        if not src:
            continue
        data = open(src, 'rb').read(); changed += 1
        if len(data) <= size:
            pos = off
        else:
            pos = (free_pos + 31) & ~31
            assert pos + len(data) <= free_end, '뒤쪽 빈 영역 부족'
            free_pos = pos + len(data); moved += 1
        out.seek(pos); out.write(data)
        struct.pack_into('>II', fst, i * 12 + 4, pos, len(data))
    out.seek(fst_off); out.write(fst)
    out.close()
    print(f'교체 {changed}개(옮김 {moved}개), 뒤쪽 빈 영역 남음 {(free_end - free_pos)/1e6:.1f}MB')



if __name__ == '__main__':
    main()
