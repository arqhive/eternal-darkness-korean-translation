"""방 텍스트(RmTxt/JRmTxt/JRWTxt, 해제본) 파서·재조립.

구조: [본문 길이 u32] + 묶음 [개수][0x6B5][(표 오프셋, 8)×개수] + 표 머리들(연속) + 레코드(표 순서대로 연속)
표 머리: [항목 수][0xFB90][(레코드 오프셋, 길이)×항목 수], 오프셋은 표 시작 기준. 빈 항목(길이 0)의 오프셋 = 원본값 유지.
"""
import struct

PAK, TAB = 0x6B5, 0xFB90


def parse(d):
    base = 4
    n, m = struct.unpack('>II', d[base:base + 8]); assert m == PAK
    tabs = []
    for i in range(n):
        o, s = struct.unpack('>II', d[base + 8 + 8 * i:base + 16 + 8 * i]); assert s == 8
        st = base + o
        k, m2 = struct.unpack('>II', d[st:st + 8]); assert m2 == TAB
        items = []
        for j in range(k):
            a, l = struct.unpack('>II', d[st + 8 + 8 * j:st + 16 + 8 * j])
            items.append(d[st + a:st + a + l] if l else ('empty', a))
        tabs.append(items)
    return tabs


def build(tabs):
    n = len(tabs)
    hdr_sizes = [8 + 8 * len(t) for t in tabs]
    pak = bytearray(struct.pack('>II', n, PAK))
    pos = 8 + 8 * n
    starts = []
    for h in hdr_sizes:
        starts.append(pos); pak += struct.pack('>II', pos, 8); pos += h
    body = bytearray(); heads = bytearray()
    rec_pos = pos  # 묶음 기준 레코드 시작
    for t, st in zip(tabs, starts):
        heads += struct.pack('>II', len(t), TAB)
        for it in t:
            if isinstance(it, tuple):
                heads += struct.pack('>II', it[1], 0)
            else:
                heads += struct.pack('>II', rec_pos + len(body) - st, len(it)); body += it
    out = pak + heads + body
    return struct.pack('>I', len(out)) + out


# ---- 컷신 파일(cin####.bin 해제본): [길이][묶음: 장면 데이터, 영어 자막 묶음, 일본어 자막 묶음 ...] ----
def cin_parts(d):
    base = 4
    n, m = struct.unpack('>II', d[base:base + 8]); assert m == PAK
    return [struct.unpack('>II', d[base + 8 + 8 * i:base + 16 + 8 * i]) for i in range(n)]


def cin_text(d, i):
    """i번 항목(자막 묶음)을 표 목록으로."""
    o, s = cin_parts(d)[i]
    sub = d[4 + o:4 + o + s]
    return parse(struct.pack('>I', len(sub)) + sub)


def cin_build(d, repl):
    """repl={항목번호: 표 목록}. 항목은 0x20 정렬로 다시 배치."""
    parts = cin_parts(d)
    base = 4; n = len(parts)
    first = min(o for o, s in parts if s)
    out = bytearray(d[base:base + first])
    for i, (o, s) in enumerate(parts):
        if not s:
            continue
        b = build(repl[i])[4:] if i in repl else d[base + o:base + o + s]
        out += bytes((-len(out)) % 0x20)
        struct.pack_into('>II', out, 8 + 8 * i, len(out), len(b))
        out += b
    return struct.pack('>I', len(out)) + out
