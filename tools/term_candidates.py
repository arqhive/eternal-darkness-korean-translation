"""5단계 용어 후보 추출 → work/terms/candidates.json

1) 색 글씨(\\a? … \\aw) 강조어: 영어·일본어 단위에서 같은 순서로 짝지음(개수가 같을 때)
2) 아이템·주문·룬 이름(*_INV 등 이름 칸): 영어 = 일본어 한 줄씩
3) 화자(라벨 접두어) 목록과 대사 수
4) 대문자로 시작하는 고유명사 후보(2회 이상)
"""
import collections
import json
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
COLOR = re.compile(r'\\a([a-vx-z])(.+?)(?=\\a[a-z]|$)', re.S)


def spans(s):
    return [(m.group(1), re.sub(r'\s+', ' ', m.group(2)).strip(' .,!?:;')) for m in COLOR.finditer(s or '')]


def main():
    rows = json.load(open(os.path.join(ROOT, 'work', 'text', 'units.json'), encoding='utf-8'))
    terms = collections.defaultdict(lambda: {'n': 0, 'ja': collections.Counter(), 'kinds': collections.Counter(), 'ex': []})
    for r in rows:
        es, js = spans(r['en']), spans(r['ja'])
        for k, (c, t) in enumerate(es):
            if not t or len(t) > 40:
                continue
            d = terms[t]; d['n'] += 1; d['kinds'][r['kind']] += 1
            if len(es) == len(js) and js[k][1]:
                d['ja'][js[k][1]] += 1
            if len(d['ex']) < 2:
                d['ex'].append(r['id'])
    # 이름 칸(아이템·주문·룬 등): 한 줄 이름
    names = []
    for r in rows:
        lab = r['label'].split('/')[-1]
        if r['kind'] in ('item_name', 'tome') or lab.endswith('_INV'):
            en = re.sub(r'\\[a-z]+[\d.]*', '', r['en']).strip()
            ja = re.sub(r'\\[a-z]+[\d.]*', '', r['ja']).strip()
            if en and len(en) < 60:
                names.append(dict(id=r['id'], kind=r['kind'], en=en, ja=ja))
    spk = collections.Counter(r['speaker'] for r in rows if r['speaker'])
    # 대문자 고유명사(문장 첫 단어 제외)
    caps = collections.Counter()
    for r in rows:
        txt = re.sub(r'\\[a-z]+[\d.]*|~[a-z0-9]', ' ', r['en'])
        for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-z'’]+(?:[ -](?:of |the )?[A-Z][a-z'’]+)*)", txt):
            caps[m.group(1)] += 1
    out = dict(
        colored=[dict(en=t, n=d['n'], ja=[j for j, _ in d['ja'].most_common(3)], kinds=dict(d['kinds']), ex=d['ex'])
                 for t, d in sorted(terms.items(), key=lambda kv: -kv[1]['n'])],
        names=names,
        speakers=spk.most_common(),
        caps=[(w, n) for w, n in caps.most_common() if n >= 2],
    )
    os.makedirs(os.path.join(ROOT, 'work', 'terms'), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'work', 'terms', 'candidates.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('강조어', len(out['colored']), '이름 칸', len(names), '화자', len(spk), '대문자 후보', len(out['caps']))


if __name__ == '__main__':
    main()
