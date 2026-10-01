"""0x6B5 표식 재귀 묶음(BootPak 등) 파서: [개수][0x6B5][(오프셋,크기)×개수], 오프셋은 묶음 시작 기준."""
import struct

MAGIC = 0x6B5


def is_pak(d):
    if len(d) < 8:
        return False
    n, m = struct.unpack('>II', d[:8])
    if m != MAGIC or not 0 < n < 4096 or 8 + 8 * n > len(d):
        return False
    for i in range(n):
        o, s = struct.unpack('>II', d[8 + 8 * i:16 + 8 * i])
        if s and o + s > len(d):
            return False
    return True


def entries(d):
    n = struct.unpack('>I', d[:4])[0]
    return [struct.unpack('>II', d[8 + 8 * i:16 + 8 * i]) for i in range(n)]


def walk(d, path=(), base=0):
    """(경로, 절대오프셋, 바이트) 잎 노드를 낸다."""
    if is_pak(d):
        for i, (o, s) in enumerate(entries(d)):
            if s:
                yield from walk(d[o:o + s], path + (i,), base + o)
    else:
        yield path, base, d
