"""부호 칸 점검(10/11): 빌드 폰트에서 한글 글자 잉크 오른쪽 끝과 부호 칸의 잉크 왼쪽 위치·폭 표 값을 잰다."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import font_side as S
import build_full as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL = 28
ks = S.sheets(os.path.join(ROOT, 'build', 'full', 'JFonts.tpl'))
kw = S.widths(os.path.join(ROOT, 'build', 'full', 'JBtPakJS.bin'))
cm = {k: int(v, 16) for k, v in json.load(open(os.path.join(ROOT, 'build', 'charmap.json'), encoding='utf-8')).items()}


def ink(code):
    s = ks[code >> 8]; k = code & 0xFF
    a = np.asarray(s.crop(((k % 16) * CELL, (k // 16) * CELL, (k % 16) * CELL + CELL, (k // 16) * CELL + CELL)))[..., 3]
    xs = np.nonzero(a.max(0) > 0)[0]
    return (int(xs.min()), int(xs.max())) if len(xs) else None


r = [ink(cm[c])[1] for c in '한다요까니습없였는데']
print('한글 잉크 오른쪽 끝', r, '진행 폭', B.HANGUL_ADV)
for ch in '.,?!:;\'"-()~':
    c = ord(ch); print(repr(ch), '잉크', ink(c), '폭', kw[c])
for ch in '…「」『』·':
    if ch in cm:
        c = cm[ch]; print(ch, hex(c), '잉크', ink(c), '폭', kw[c] if c < len(kw) else None)
