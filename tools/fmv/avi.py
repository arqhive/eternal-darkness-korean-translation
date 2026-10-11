"""VP31 AVI 읽기·쓰기(영상 스트림 하나)."""
import struct


def chunks(d, off, end):
    while off + 8 <= end:
        cid = d[off:off + 4]; sz = struct.unpack('<I', d[off + 4:off + 8])[0]
        yield cid, off, sz
        off += 8 + sz + (sz & 1)


def parse(d):
    """반환: (movi 앞부분 바이트, 프레임 목록[(fourcc, data, flags)], idx1 존재, movi 뒤 바이트)"""
    assert d[:4] == b'RIFF' and d[8:12] == b'AVI '
    frames = []; movi = None; idx = None
    for cid, off, sz in chunks(d, 12, len(d)):
        if cid == b'LIST' and d[off + 8:off + 12] == b'movi':
            movi = (off, sz)
        elif cid == b'idx1':
            idx = (off, sz)
    mo, ms = movi
    for cid, off, sz in chunks(d, mo + 12, mo + 8 + ms):
        if cid == b'LIST':   # rec 묶음
            for c2, o2, s2 in chunks(d, off + 12, off + 8 + sz):
                frames.append([c2, d[o2 + 8:o2 + 8 + s2]])
        else:
            frames.append([cid, d[off + 8:off + 8 + sz]])
    flags = []
    if idx:
        io, isz = idx
        for k in range(isz // 16):
            c, fl, o, s = struct.unpack('<4sIII', d[io + 8 + 16 * k:io + 24 + 16 * k])
            flags.append(fl)
    return dict(head=d[12:mo], movi=movi, idx=idx, frames=frames, flags=flags, tail_after=d[mo + 8 + ms + (ms & 1):])
