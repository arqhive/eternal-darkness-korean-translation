"""7단계 기계 검수(번역 검사기 check_trans 가 보지 않는 항목).
- 부호: 영어가 마침표로 끝나는데 번역 끝 부호 없음(서술 문장), ASCII 말줄임 '...', 물결표 뒤 마침표, 겹공백 이상(원문에 없는)
- 문자: 번역에 남은 일본어 가나·한자, 원문에 없는 영어 낱말, 한글 자모 낱자
- 변수 조사: ~p 뒤 조사 병기 누락
- 일관성: 같은 영어(짧은 이름류)가 다른 번역
- 글자 수: 쓰인 비ASCII 글자 수(폰트 칸 1~6번 장 1,536칸 안인지)
- 그래픽 규격: done 그림이 원본과 크기·투명도 구성이 같은지
결과: work/review7/*.tsv, 요약 출력. python review7.py"""
import collections
import json
import os
import re

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'work', 'review7')
TAG = re.compile(r'\\a[a-z]|\\i\d+|\\s\d*\.?\d*|~[a-z0-9]')
KANA = re.compile(r'[぀-ヿ一-鿿]')
JAMO = re.compile(r'[ㄱ-ㆎᄀ-ᇿ]')
NAMEKIND = ('item_name', 'button', 'tome', 'menu', 'label')


def load():
    units = {u['id']: u for u in json.load(open(os.path.join(ROOT, 'work', 'text', 'units.json'), encoding='utf-8'))}
    ko = {}
    kd = os.path.join(ROOT, 'work', 'text', 'ko')          # [GC] 폴더라 glob 금지
    for x in sorted(os.listdir(kd)):
        if x.endswith('.json'):
            for k, v in json.load(open(os.path.join(kd, x), encoding='utf-8')).items():
                ko[k] = (v, x)
    return units, ko


def plain(s):
    return TAG.sub('', s).replace('\\n', '\n')


def main():
    os.makedirs(OUT, exist_ok=True)
    units, ko = load()
    rows = collections.defaultdict(list)
    for id_, (v, f) in ko.items():
        u = units[id_]
        en, ja, k = u['en'] or '', u['ja'] or '', plain(v)
        kt = k.strip()
        # 부호
        if '...' in k:
            rows['부호 ASCII 말줄임'].append((id_, f, kt[:80]))
        if re.search(r'[~～]\.', k):
            rows['부호 물결표 뒤 마침표'].append((id_, f, kt[:80]))
        last_en = plain(en).strip()
        if (last_en.endswith('.') and u['kind'] not in NAMEKIND and kt and len(kt) > 8
                and not re.search(r'[.!?…"」』)\]~～:：]$', kt) and not re.search(r'[。！？]$', plain(ja).strip()) is False):
            if not re.search(r'[.!?…"」』)\]~～:：]$', kt):
                rows['부호 문장 끝 부호 없음'].append((id_, f, kt[-60:].replace('\n', '⏎')))
        # 문자
        if KANA.search(k):
            rows['문자 일본어 남음'].append((id_, f, ''.join(sorted(set(KANA.findall(k)))), kt[:60]))
        if JAMO.search(k):
            rows['문자 한글 낱자'].append((id_, f, ''.join(sorted(set(JAMO.findall(k)))), kt[:60]))
        for w in set(re.findall(r'[A-Za-z]{3,}', k)):
            if w not in en and w not in ja and w not in ('Act', 'TV'):
                rows['문자 원문에 없는 영어'].append((id_, f, w, kt[:60]))
        # 변수 조사
        for m in re.finditer(r'~[a-z0-9]([은는이가을를와과])(?!\()', v):
            rows['변수 조사 병기 누락'].append((id_, f, m.group(0), kt[:60]))
    # 일관성: 짧은 이름류 같은 영어 → 번역 여럿
    by_en = collections.defaultdict(set)
    for id_, (v, f) in ko.items():
        u = units[id_]
        en = plain(u['en'] or '').strip().replace('\n', ' ')
        if en and len(en) <= 30 and u['kind'] in NAMEKIND:
            by_en[en].add(plain(v).strip().replace('\n', ' '))
    for en, kos in sorted(by_en.items()):
        if len(kos) > 1:
            rows['일관성 같은 영어 다른 번역'].append(('', '', en, ' | '.join(sorted(kos))))
    # 글자 수
    chars = collections.Counter()
    for v, _ in ko.values():
        for ch in plain(v):
            if ord(ch) >= 0x80:
                chars[ch] += 1
    hangul = [c for c in chars if 0xAC00 <= ord(c) <= 0xD7A3]
    other = [c for c in chars if not (0xAC00 <= ord(c) <= 0xD7A3)]
    # 그래픽 규격
    plan = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'work', 'gfx', 'plan.tsv'), encoding='utf-8')][1:]
    gok = 0
    for r in plan:
        gid, st = r[0], r[-1]
        if not st.startswith('확정') or r[5] != '번역':
            continue
        a = Image.open(os.path.join(ROOT, 'work', 'gfx', 'src', gid + '_jp.png')).convert('RGBA')
        b = Image.open(os.path.join(ROOT, 'work', 'gfx', 'done', gid + '.png')).convert('RGBA')
        if a.size != b.size:
            rows['그래픽 크기 다름'].append((gid, '', str(a.size), str(b.size)))
            continue
        A, B = np.asarray(a)[..., 3], np.asarray(b)[..., 3]
        ua, ub = len(np.unique(A)), len(np.unique(B))
        if (ua == 1) != (ub == 1) or (A.min() == 255) != (B.min() == 255):
            rows['그래픽 투명도 구성 다름'].append((gid, '', 'alpha 값 %d종→%d종' % (ua, ub), ''))
            continue
        gok += 1
    for name, rs in rows.items():
        with open(os.path.join(OUT, name.replace(' ', '_') + '.tsv'), 'w', encoding='utf-8') as fo:
            for r in rs:
                fo.write('\t'.join(map(str, r)) + '\n')
    print('번역 줄', len(ko))
    for name in sorted(rows):
        print('%-22s %d' % (name, len(rows[name])))
    print('쓰인 글자: 한글 %d, 기타 비ASCII %d (%s)' % (len(hangul), len(other), ''.join(sorted(other))))
    print('그래픽 확정본 규격 일치', gok)


if __name__ == '__main__':
    main()
