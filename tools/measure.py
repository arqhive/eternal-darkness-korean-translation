"""글줄 픽셀 폭 측정(일본판 글리프 텍스트 기준).

텍스트: u16 글리프 번호 열. 0x000A = 줄바꿈. ASCII 영역(0x00xx)의 태그는 폭 0:
  \\a? (색, 3글자) / \\i## (아이콘, 숫자) / \\s#.# (글자 크기 배율, 이후 글자 폭에 곱함) / \\n
  ~? (변수: ~p 플레이어 이름 등) → 폭은 따로 VAR_W 로 가정
폭 표: 시스템 묶음 최상위 2번 블록([개수 u32][기본 폭 1바이트][글자별 폭 × 개수]).
"""
import re
import struct

VAR_W = {'p': 0}  # 변수 폭은 측정에서 따로 표시(0으로 두고 has_var 로 알림)


def width_table(path):
    d = open(path, 'rb').read()
    o, s = struct.unpack('>II', d[24:32])
    n = struct.unpack('>I', d[o:o + 4])[0]
    return d[o + 5:o + 5 + n]  # [개수 u32][기본 폭 1바이트(28)][글자별 폭 × 개수]


def codes_of(text):
    return [struct.unpack('>H', text[i:i + 2])[0] for i in range(0, len(text) - 1, 2)]


def to_str(codes):
    """측정·표시용: ASCII 는 그대로, 나머지는 \\uE000+코드 로."""
    return ''.join(chr(c) if c < 0x80 else chr(0xE000 + c) for c in codes)


TAG = re.compile(r'\\a[a-z]|\\i\d+|\\s\d*\.?\d*|\\n|~[a-z0-9]')


def lines_px(text, wt, ascii_text=False):
    """[(줄 문자열, 픽셀 폭, 변수 포함 여부)]"""
    codes = list(text) if ascii_text else codes_of(text)
    s = to_str(codes)
    out = []
    for line in s.split('\n'):
        px = 0.0; scale = 1.0; has_var = False; i = 0
        while i < len(line):
            m = TAG.match(line, i)
            if m:
                t = m.group()
                if t.startswith('\\s'):
                    try:
                        scale = float(t[2:]) if t[2:] not in ('', '.') else 1.0
                    except ValueError:
                        scale = 1.0
                elif t.startswith('~'):
                    has_var = True
                i = m.end(); continue
            c = ord(line[i]); c = c - 0xE000 if c >= 0xE000 else c
            px += (wt[c] if c < len(wt) else 28) * scale
            i += 1
        out.append((line, px, has_var))
    return out
