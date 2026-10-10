"""번역문 넘침 검사.

사용: python check_overflow.py <번역.json>
번역 JSON: [{"id": ..., "kind": <창 종류>, "ko": "번역문"}, ...]
  kind 는 아래 LIMITS 키(분류 함수 kind_of 로 라벨·위치에서 정할 수 있음).
한글 폭은 HANGUL_W(폰트 칸 폭 표에 넣을 값), 그 밖의 글자는 일본판 폭 표(ASCII·전각 부호) 그대로.
태그(\\a?, \\i##, \\s#.#, ~?)는 폭 0, \\s 는 배율 적용. ~p(플레이어 이름) 등 변수는 VAR_W 로 계산.
"""
import json
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
HANGUL_W = 23   # build_full.HANGUL_ADV 와 같게(10/4 26→23)
PUNCT_PAD, PUNCT_ASCII = 2, '.,!:;)~'   # build_full 과 같게(10/11 닫는 부호 2px 띄움)
VAR_W = 26 * 6   # 변수 자리(이름 등) 예상 폭: 한글 6자 기준(임시)

# 창 종류별 한계: (한 줄 최대 px, 최대 줄 수). docs/windows.md 참고(2026-10-01).
LIMITS = {
    # 확인 = 3단계 측정판(v0.0.3) 돌핀 확인, 원문 = 일본어 원문 최대치(가안)
    'room':      (621, 14),  # 방 조사 창: 자동 줄바꿈 폭 621~629px 확인, 15줄째부터 화면 아래로 잘림(확인)
    'item_desc': (602, 18),  # 아이템·주문 설명(원문)
    'item_name': (334, 3),   # 아이템 이름 _INV(원문)
    'pickup':    (543, 4),   # 획득 메시지 _PICKUP(원문)
    'generic':   (600, 14),  # 시스템 일반 문구(원문)
    'button':    (412, 6),   # 버튼 안내(원문)
    'npc':       (621, 13),  # NPC 대사(원문)
    'subtitle':  (765, 2),   # 컷신 자막: 765px 한 줄 표시·두 줄 표시 확인
    'rt_sub':    (590, 1),   # 실시간 자막(원문)
    'voice_sub': (643, 1),   # 음성 자막(원문)
    'tome':      (396, 3),   # 책 메뉴·주문 화면(원문)
    'book':      (595, 12),  # 책 문구(원문)
    'memcard':   (546, 12),  # 메모리 카드(원문)
}
AUTOWRAP = {'room'}  # 자동 줄바꿈 확인된 창: 공백에서 꺾어 줄 수를 셈

_wt = None


def wt():
    global _wt
    if _wt is None:
        _wt = measure.width_table(os.path.join(ROOT, 'extract', 'jp', 'JBtPakJS.bin'))
    return _wt


TAG = re.compile(r'\\a[a-z]|\\i\d+|\\s\d*\.?\d*|\\n|~[a-z0-9]')


def line_px(line):
    px = 0.0; scale = 1.0; i = 0
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
                px += VAR_W * scale
            i = m.end(); continue
        c = line[i]
        if '가' <= c <= '힣':
            w = HANGUL_W
        elif ord(c) < 0x80:
            w = wt()[ord(c)] + (PUNCT_PAD if c in PUNCT_ASCII else 0)
        else:
            w = 28  # 전각 부호 등(일본판 칸 폭 27~28)
        px += w * scale; i += 1
    return px


def wrap(line, maxw):
    """게임 자동 줄바꿈 흉내: 공백 단위로 채우다 넘치면 꺾고, 공백 없는 덩어리는 글자 단위로 꺾는다."""
    out = []; cur = ''
    for w in re.split(r'(?<= )', line):
        if line_px(cur + w) <= maxw:
            cur += w; continue
        if cur:
            out.append(cur); cur = ''
        while line_px(w) > maxw:
            k = len(w)
            while k > 1 and line_px(w[:k]) > maxw:
                k -= 1
            out.append(w[:k]); w = w[k:]
        cur = w
    out.append(cur)
    return out


def check(ko, kind):
    """[(문제 종류, 설명)] — 빈 목록이면 통과. 자동 줄바꿈 창은 꺾인 뒤 줄 수만 본다."""
    maxw, maxl = LIMITS[kind]
    probs = []
    if kind in AUTOWRAP:
        lines = [x for l in ko.split('\n') for x in wrap(l, maxw)]
        if len(lines) > maxl:
            probs.append(('줄 수', '자동 줄바꿈 후 %d줄 > %d줄' % (len(lines), maxl)))
        return probs
    lines = ko.split('\n')
    if len(lines) > maxl:
        probs.append(('줄 수', '%d줄 > %d줄' % (len(lines), maxl)))
    for n, l in enumerate(lines, 1):
        w = line_px(l)
        if w > maxw:
            probs.append(('폭', '%d번째 줄 %.0fpx > %dpx: %s' % (n, w, maxw, l)))
    return probs


def kind_of(cat, blk, name):
    """survey_lines.py 의 분류·블록·라벨 → 창 종류."""
    if cat in ('room', 'memcard', 'book'):
        return cat
    if cat == 'cin':
        return 'subtitle'
    if cat == 'boot':
        blk = int(blk)
        if blk == 4:
            for suf, k in (('_INV', 'item_name'), ('_DESC', 'item_desc'), ('_PICKUP', 'pickup')):
                if name.endswith(suf):
                    return k
            return 'generic'
        return {3: 'tome', 6: 'button', 8: 'npc', 9: 'rt_sub', 12: 'voice_sub'}[blk]
    raise KeyError(cat)


def main(path):
    items = json.load(open(path, encoding='utf-8'))
    bad = 0
    for it in items:
        for kind_, msg in check(it['ko'], it['kind']):
            bad += 1; print(it['id'], kind_, msg)
    print('검사 %d개, 문제 %d건' % (len(items), bad))


if __name__ == '__main__':
    main(sys.argv[1])
