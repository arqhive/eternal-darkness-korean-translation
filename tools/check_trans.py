"""번역 기계 검사: 태그 보존·넘침·부호 규칙·높임(일본어 대응 줄)·용어
사용: python check_trans.py <번역 json: {id: ko}>  (원문은 work/text/units.json)"""
import json
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_overflow

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
TAG = re.compile(r'\\a[a-z]|\\i\d+|\\s\d*\.?\d*|~[a-z0-9]')
JA_POL = re.compile(r"(です(?!ら)|でした|ます|ました|ません|でしょう|ましょう|下さい|ください|ございます|まして)")
KO_POL = re.compile(r'(니다|니까|니다만|십시오|시오|소서|세요|에요|예요|어요|아요|해요|군요|네요|죠|지요|요)[.,!?…\s"」]*$')


END = re.compile(r'[.!?…"」』)]$')


def is_fragment(k):
    """문장부호로 끝나지 않는 줄 = 다음 칸으로 이어지는 조각(서술어가 다른 칸에 있음) → 높임 판정 안 함."""
    return not END.search(sentences_end(k).rstrip())


def is_polite(k):
    """문장 끝이 존대인가. 끝에 붙은 호칭(「, 루서.」)은 떼고 본다. ~니다·~니까는 앞 글자 받침이 ㅂ일 때만."""
    t = sentences_end(k)
    m = re.search(r',\s*([^,.!?…]{1,12})[.!?…]*$', t)                 # 끝 호칭 떼기(서술어로 끝나면 호칭 아님)
    if m and not re.search(r'(다|요|까|죠|오|라|자|네|지|야|어|아|게|니|소|마|래|걸|데|가)$', m.group(1).strip()):  # 「주군」처럼 군으로 끝나는 호칭은 뗀다
        t = t[:m.start()]
    t = re.sub(r'[.,!?…\s"」』)]+$', '', t)
    m = re.search(r'(.)(니다|니까|니다만)$', t)
    if m:
        c = ord(m.group(1))
        return 0xAC00 <= c <= 0xD7A3 and (c - 0xAC00) % 28 == 17
    return bool(re.search(r'(십시오|시오|소서|세요|에요|예요|어요|아요|해요|군요|네요|죠|지요|요|옵니다|시기를|시길)$', t))


def sentences_end(s):
    s = re.sub(TAG, '', s).strip()
    return s


def main(path):
    units = {u['id']: u for u in json.load(open(os.path.join(ROOT, 'work', 'text', 'units.json'), encoding='utf-8'))}
    ko = json.load(open(path, encoding='utf-8'))
    probs = []
    ok = set()
    exf = os.path.join(ROOT, 'work', 'text', 'check_exceptions.txt')
    if os.path.exists(exf):
        ok = {l.split('	')[0].strip() for l in open(exf, encoding='utf-8') if l.strip() and not l.startswith('#')}
    for id_, k in ko.items():
        u = units[id_]
        src_tags = sorted(TAG.findall(u['ja'] if u['en_src'] == '영어 없음' else u['ja']))
        en_tags = sorted(TAG.findall(u['en']))
        if sorted(TAG.findall(k)) not in (src_tags, en_tags):  # 일본어 또는 영어 원문과 같으면 통과
            probs.append((id_, '태그', '일본어 %s / 영어 %s / 번역 %s' % (src_tags, en_tags, sorted(TAG.findall(k)))))
        for kind_, msg in check_overflow.check(k, u['kind']):
            probs.append((id_, '넘침 ' + kind_, msg))
        if re.search(r'…\.', k) or re.search(r'~\.', k):
            probs.append((id_, '부호', '말줄임표·물결표 뒤 마침표'))
        if '그녀' in k:
            probs.append((id_, '문체', '「그녀」'))
        # 높임: 일본어 줄 전체가 존대인지(마지막 서술 기준)와 번역 마지막 서술 비교(대사 창만)
        if u['kind'] in ('subtitle', 'rt_sub', 'voice_sub', 'npc'):
            ja_last = re.split(r'[。！？]\s*', re.sub(TAG, '', u['ja']).strip())
            ja_last = [x for x in ja_last if x.strip(' …')] or ['']
            mm = re.search(r'[、，]\s*([^、，]{1,8})$', ja_last[-1].strip())   # 끝 호칭(「、おじいさま」) 떼기
            if mm and re.search(r'(さま|様|さん|殿|くん|君|ちゃん|博士|隊長|警部|司教|^[ァ-ヶー・]+)$', mm.group(1).strip(' …')):
                ja_last[-1] = ja_last[-1].strip()[:mm.start()]
            jp = bool(JA_POL.search(ja_last[-1]))
            kp = is_polite(k)
            if id_ in ok or is_fragment(k):
                pass
            elif jp and not kp:
                probs.append((id_, '높임', '일본어 존대인데 번역 반말: %s | %s' % (u['ja'], k)))
            elif kp and not jp and re.search(r'(だ|よ|わ|の|ぞ|ぜ|な|さ|か)[。！？…]*$', ja_last[-1].strip()):
                probs.append((id_, '높임', '일본어 반말인데 번역 존대: %s | %s' % (u['ja'], k)))
    for p in probs:
        print(*p, sep=' | ')
    print('검사 %d줄, 문제 %d건' % (len(ko), len(probs)))


if __name__ == '__main__':
    main(sys.argv[1])
