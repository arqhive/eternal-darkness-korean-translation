"""번역 전체 문장부호 검사(10/12). 영어 원문과 대조해 「번역이 새로 만든 문제」 후보만 뽑는다.
사용: python tools/check_punct.py [출력.json]
항목
  E1 말줄임표·물결표 뒤 마침표(….  ~.)
  E2 부호 겹침·띄어쓰기(.. !. ?. ,. 마침표 앞 공백, ASCII ...)
  E3 괄호·따옴표 짝(「」『』()"")
  M1 끝 부호 빠짐: 영어 끝이 . ! ? 인데 번역 끝이 한글(종결형)
  M2 줄 끝 부호 빠짐: 번역 줄이 종결어미로 끝나고 다음 줄이 새 문장(영어 같은 위치에 문장 끝)
  M3 메뉴·이름에 마침표: item_name·button 끝 마침표
  C1 완결 문장 뒤 쉼표: 「~다, 」「~요, 」 뒤가 호칭·반복이 아닌 것
  M4 대사 끝이 호칭·명사인데 부호 빠짐(영어는 문장 끝)
  E4 부호 뒤 띄어쓰기 빠짐
  P1 대사 속 그녀·그들
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAG = re.compile(r'\\a[a-z]|\\i\d+|\\s[\d.]+|\\n|~[a-z]|　')
END = '다요죠까네군지야어아라자냐니걸게래마세나오구가며데오'
FINAL = re.compile(r'(다|요|죠|까|네|군|지|냐|니|걸|래|라|자|나|세|오|구나|구려|거든|잖아|어|아|야|해|게)$')
FINAL2 = re.compile(r'(다|요|죠|까|네|군|냐|구나|구려|거든|잖아)$')   # 줄 끝 판정용(이어지는 어미 -어/-아/-서/-니/-지 는 제외)
DIALOG = {'subtitle', 'rt_sub', 'voice_sub', 'npc', 'book'}


def clean(s):
    return TAG.sub('', s or '')


def load():
    U = json.load(open(os.path.join(ROOT, 'work/text/units.json'), encoding='utf-8'))
    ko = {}
    for f in sorted(os.listdir(os.path.join(ROOT, 'work/text/ko'))):
        ko.update(json.load(open(os.path.join(ROOT, 'work/text/ko', f), encoding='utf-8')))
    return U, ko


def en_ends_sentence(en):
    e = clean(en).rstrip().rstrip('"\')]')
    return e[-1:] in ('.', '!', '?') and not e.endswith('...')


def check(u, k):
    out = []
    en = u.get('en') or u.get('en_jp') or ''
    c = clean(k)
    if re.search(r'…\.|~\.', c):
        out.append(('E1', '말줄임표·물결표 뒤 마침표'))
    if re.search(r'\.\.|[!?]\.|,\.|[가-힣]\s+[.,!?]|\.{3}', c.replace('…', '')):
        out.append(('E2', '부호 겹침·띄어쓰기'))
    for a, b in ('「」', '『』', '()', '“”'):
        if c.count(a) != c.count(b):
            out.append(('E3', '괄호 짝 %s%s' % (a, b)))
    if c.count('"') % 2:
        out.append(('E3', '따옴표 짝 "'))
    lines = [l.strip() for l in c.split('\n')]
    lines = [l for l in lines if l]
    if not lines:
        return out
    last = lines[-1]
    kind = u['kind']
    if kind in ('item_name', 'button'):
        if last.endswith('.'):
            out.append(('M3', '이름·버튼 끝 마침표'))
    elif en_ends_sentence(en) and re.search('[가-힣)」』"]$', last) and FINAL.search(last.rstrip(')」』"')):
        out.append(('M1', '끝 부호 빠짐(영어는 %s)' % clean(en).rstrip()[-1:]))
    if kind not in ('item_name', 'button', 'tome'):
        for i, l in enumerate(lines[:-1]):
            nxt = lines[i + 1]
            if FINAL2.search(l) and not re.search(r'[.!?…~,]$', l) and re.match(r'[가-힣"「(\d]', nxt):
                # 다음 줄이 이어지는 말(조사·어미로 시작)이면 같은 문장
                if not re.match(r'(은|는|이|가|을|를|에|의|도|만|과|와|로|으로|고|며|면|서|지만)[\s,]', nxt):
                    out.append(('M2', '줄 끝 부호 빠짐: 「%s⏎%s」' % (l[-8:], nxt[:8])))
    for m in re.finditer(r'(다|요|죠|니다|어요|아요|지요),\s*(\S{0,6})', c):
        after = m.group(2)
        out.append(('C1', '완결 문장 뒤 쉼표: 「%s」' % c[max(0, m.start() - 6):m.end() + 4]))
    if kind in DIALOG and en_ends_sentence(en) and re.search('[가-힣]$', last) and not FINAL.search(last):
        out.append(('M4', '대사 끝(호칭·명사) 부호 빠짐'))
    if re.search(r'[.!?,][가-힣A-Za-z]', c):
        out.append(('E4', '부호 뒤 띄어쓰기 빠짐'))
    if kind in DIALOG and re.search('그녀|그들', c):
        out.append(('P1', '대사 속 그녀·그들'))
    return out


def main():
    U, ko = load()
    res = []
    for u in U:
        k = ko.get(u['id'])
        if k is None:
            continue
        for code, why in check(u, k):
            res.append(dict(id=u['id'], kind=u['kind'], code=code, why=why, en=u.get('en') or u.get('en_jp') or '', ko=k))
    from collections import Counter
    print(Counter(r['code'] for r in res))
    if len(sys.argv) > 1:
        json.dump(res, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
