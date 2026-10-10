"""이터널 다크니스 텍스트 레코드 스캐너·디코더.

문자열표: [개수 u32][0x0000FB90][(오프셋 u32, 길이 u32) × 개수], 오프셋은 표 시작 기준.
레코드: 4바이트 머리(u32) + Gage BPE 블록.
푼 본문: 0x18바이트 헤더, 'c\0', [라벨 32+64바이트(일본판 디스크 파일만, 0 채움)], 텍스트, 00 00.
  북미판 텍스트 = 1바이트 ASCII, 일본판 = 2바이트 글리프 번호(상위=폰트 장, 하위=칸).
"""
import os
import struct
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpe

TMAGIC = b'\x00\x00\xfb\x90'


def tables(d):
    """파일 안 문자열표를 모두 찾는다: (표 오프셋, [(오프셋,길이)])"""
    out = []; i = d.find(TMAGIC, 4)
    while i >= 0:
        st = i - 4
        n = struct.unpack('>I', d[st:st + 4])[0]
        if 0 < n < 5000 and st + 8 + 8 * n <= len(d):
            ents = [struct.unpack('>II', d[st + 8 + 8 * k:st + 16 + 8 * k]) for k in range(n)]
            if all(o >= 8 + 8 * n and l >= 8 and st + o + l <= len(d) for o, l in ents):
                out.append((st, ents))
        i = d.find(TMAGIC, i + 4)
    return out


def record(d, st, o, l):
    head = struct.unpack('>I', d[st + o:st + o + 4])[0]
    body, end = bpe.decode(d, st + o + 4)
    return head, body


def _is_label(x):
    z = x.find(b'\0')
    if z < 0:
        return False
    return all(c == 95 or 48 <= c <= 57 or 65 <= c <= 90 or 97 <= c <= 122 for c in x[:z]) and not any(x[z:])


def parse_body(head, body, jp):
    """(라벨, 텍스트 원시 바이트)"""
    p = 0x18
    if body[p:p + 2] not in (b'c\0', b'l\0', b'r\0'):   # c 보통·l 긴 글(편지·설명)·r 음량 화면(10/10: l·r 을 버려 44개 누락)
        return None, None
    p += 2
    label = ''
    a, b = body[p:p + 32], body[p + 32:p + 96]
    if len(b) == 64 and _is_label(a) and _is_label(b) and b[0]:
        label = a.split(b'\0')[0].decode('latin1') + '/' + b.split(b'\0')[0].decode('latin1')
        p += 96
    t = body[p:]
    if jp:
        k = 0
        while k + 1 < len(t) and t[k:k + 2] != b'\0\0':
            k += 2
    else:
        k = t.find(b'\0')
        if k < 0: k = len(t)
    return label, t[:k]


def ascii_text(t):
    return t.decode('latin1')


def scan(path, jp):
    d = open(path, 'rb').read()
    res = []
    for st, ents in tables(d):
        for idx, (o, l) in enumerate(ents):
            try:
                head, body = record(d, st, o, l)
                label, t = parse_body(head, body, jp)
            except Exception:
                continue
            if t is not None:
                res.append((st, idx, head, label, t))
    return res
