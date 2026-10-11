"""GPT 그림 재작업 묶음 만들기(10/11) → work/GPT/
  원본/<번호>_원본_<w>x<h>.png (+ 작은 그림은 픽셀 그대로 키운 <번호>_원본_<N>배_<W>x<H>.png)
  참고/<번호>_현재판.png  지금 패치(또는 지금 쓰는 북미판) 그림
  결과/  GPT 결과를 <번호>.png 로 저장하는 곳(비어 있음)
  비교/  gpt_import 가 원본 | 현재 | GPT 반영 시트를 만드는 곳
  목록.json, 요청서.md
python tools/gpt_prepare.py
"""
import json
import os
import shutil
import sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gpt_jobs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'work', 'GPT')

RULES = '''닌텐도 게임큐브 게임 「이터널 다크니스(エターナルダークネス ─招かれた13人─)」 일본판의 그림을 한국어판으로 바꾸는 작업이야.
네가 만든 PNG를 내가 프로그램으로 원래 크기로 줄이고 게임 형식(CMPR)으로 다시 인코딩해서 넣을 거라서,
아래 규칙을 반드시 지켜야 해.

[필수 규칙]
1. 결과는 반드시 PNG. JPG 금지.
2. 첨부한 원본과 가로세로 비율을 똑같이 맞춰. 크기는 원본보다 크게(긴 변 512픽셀 이상) 만들어.
   (첨부가 픽셀을 키운 그림이면 그 비율 그대로)
3. 그림 전체를 원본과 같은 구도로 다시 그리고, 일본어 글자만 내가 준 한국어로 바꿔.
   그림·색·테두리·배경 무늬·위치는 원본 그대로 둬. 새로 그려 넣는 것 금지(테두리 상자, 받침 판, 워터마크, 서명 금지).
4. 내가 "투명 배경"이라고 한 그림은 글자 밖을 완전히 투명하게. 흰 배경·체크무늬 금지.
5. 글자는 원본의 서체 느낌(굵기·기울기·손글씨/인쇄체), 색, 외곽선·빛 번짐, 크기, 정렬을 따라 해.
   한국어가 길면 글자 폭을 조금 좁혀서라도 원본 글자가 있던 자리 안에 넣어.
6. 한국어 맞춤법과 글자 모양을 정확하게. 받침이 빠지거나 획이 붙거나 깨지면 안 돼.
   다 만든 뒤에 글자를 한 자씩 확인하고, 틀렸으면 다시 만들어.
7. 내가 준 문구를 그대로 써. 띄어쓰기·문장부호도 바꾸지 마. 「 / 」는 줄바꿈 표시고, ( ) 안 설명은 위치 안내라 쓰지 마.
8. 영어·숫자로 된 부분(로고의 ETERNAL DARKNESS, Coming Soon, © 2002 Nintendo 등)은 번역하지 말고 원본 그대로 둬.

이해했으면 "확인"이라고만 답하고, 내가 그림을 보낼 때까지 기다려.'''


def scale_for(w, h):
    n = 1
    while max(w, h) * n < 512:
        n *= 2
    return n


def main():
    for d in ('원본', '참고', '결과', '비교'):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
    js = gpt_jobs.jobs()
    lst = []
    for j in js:
        src = Image.open(j['src']).convert('RGBA')
        assert src.size == (j['w'], j['h']), (j['id'], src.size)
        o1 = '%s_원본_%dx%d.png' % (j['id'], j['w'], j['h'])
        src.save(os.path.join(OUT, '원본', o1))
        n = scale_for(j['w'], j['h'])
        att = o1
        if n > 1:
            att = '%s_원본_%d배_%dx%d.png' % (j['id'], n, j['w'] * n, j['h'] * n)
            src.resize((j['w'] * n, j['h'] * n), Image.NEAREST).save(os.path.join(OUT, '원본', att))
        ref = '%s_현재판.png' % j['id']
        shutil.copy2(j['cur'], os.path.join(OUT, '참고', ref))
        lst.append(dict({k: v for k, v in j.items() if k not in ('src', 'cur')}, attach=att, ref=ref, save=j['id'] + '.png'))
    json.dump(lst, open(os.path.join(OUT, '목록.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    A = [x for x in lst if x['kind'] == 'A']; J = [x for x in lst if x['kind'] == 'J']
    bg = lambda x: '투명 배경(모양은 원본 그대로)' if x['transparent'] else '불투명(그림 전체)'
    L = ['# GPT 그림 재작업 요청서 (이터널 다크니스 한글 패치)', '',
         'GPT(ChatGPT 이미지 생성)에게 그림을 다시 그려 달라고 할 때 쓰는 프롬프트입니다.',
         '결과 PNG를 받아서 게임 크기·형식(CMPR)에 맞춰 넣습니다. **필요한 것만 골라서 맡기면 됩니다.**', '',
         '## 폴더', '', '| 폴더 | 내용 |', '|---|---|',
         '| `work\\GPT\\원본\\` | GPT에 첨부할 일본어 원본. 작은 그림은 픽셀 그대로 키운 `_N배` 판이 있습니다(첨부는 확대판 권장). |',
         '| `work\\GPT\\참고\\` | 지금 패치에 들어간 그림(`_현재판`). J 묶음은 지금 쓰는 북미판·영어판 그림입니다. |',
         '| `work\\GPT\\결과\\` | **GPT가 만든 PNG를 여기에 저장합니다.** 「저장할 이름」을 그대로 써 주세요(예: `g014.png`). |',
         '| `work\\GPT\\비교\\` | 반영하면 원본 \\| 현재 \\| GPT 반영(게임 형식으로 바꿨다 푼 모양) 비교 시트가 생깁니다. |', '',
         '결과를 저장한 뒤 저에게 말하면 `python tools/gpt_import.py`(또는 `… g014 cover`처럼 번호 지정)로 크기를 맞춰 넣고 비교 시트를 보내 드립니다.',
         '- 결과가 원본과 비율이 다르면 경고하고 그림 전체를 게임 크기로 줄입니다(게임 크기 그대로 와도 됩니다).',
         '- 투명이 있는 그림은 원본 투명도(모양)를 그대로 쓰고 색만 GPT 그림에서 가져옵니다.',
         '- J 묶음(지금 북미판 에셋을 쓰는 곳)은 반영하면 북미판 대신 GPT 그림이 들어갑니다. 로고 부제 「초대받은 13인」·「깨어난 13인」과 Coming Soon 위 문구는 **번역안**이라 바꾸고 싶으면 말해 주세요.', '',
         '## 1. 맨 처음 한 번만 붙여 넣을 공통 규칙', '', '```', RULES, '```', '',
         '## 2. 목록', '']

    def table(items):
        r = ['| 번호 | 분류 | 한국어 | 게임 크기 | 배경 | 저장할 이름 |', '|---|---|---|---|---|---|']
        for x in items:
            ko = ' / '.join(x['lines'])
            ko = ko if len(ko) <= 60 else ko[:58] + '…'
            r.append('| %s | %s | %s | %d×%d | %s | `%s` |' % (x['id'], x['title'], ko.replace('|', '\\|'), x['w'], x['h'], bg(x), x['save']))
        return r
    L += ['### J. 북미판 에셋을 쓰던 곳 → 일본판 원본을 한국어로 — %d개' % len(J), '',
          '로고의 영문 「ETERNAL DARKNESS」는 그대로, 아래 일본어 부제만 한국어로 바꿉니다.', ''] + table(J) + ['']
    L += ['### A. 이미 한글화한 그림 다시 그리기 (문구는 지금 패치와 같음) — %d개' % len(A), ''] + table(A) + ['']
    L += ['## 3. 그림별 요청', '', '첨부 파일은 `work\\GPT\\` 기준 경로입니다.', '']
    for x in J + A:
        L += ['### %s %s' % (x['id'], x['title']), '',
              '첨부: `원본\\%s`, `참고\\%s`' % (x['attach'], x['ref']), '', '```']
        L.append('첨부한 첫 번째 그림(일본어 원본, 실제 게임 크기 %d×%d)을 한국어로 다시 그려 줘. %s' %
                 (x['w'], x['h'], '글자 밖은 원본처럼 완전히 투명하게.' if x['transparent'] else '배경까지 그림 전체를 다시 그려.'))
        L.append('바꿀 글자(위에서 아래 순서):')
        for s in x['lines']:
            L.append('  - ' + s)
        if x['note']:
            L.append(x['note'])
        if x['id'] in gpt_jobs.LOGO_IN:
            L.append('두 번째 그림은 지금 쓰는 한글판이야(메뉴 글씨 문구는 이대로). 로고만 북미판으로 바꿔 둔 거라 로고는 참고하지 말고 일본어 원본 로고를 따라 그려.')
        elif x['kind'] == 'J':
            L.append('두 번째 그림은 지금 임시로 쓰는 북미판(영어판) 그림이야. 이건 참고하지 말고 일본어 원본을 기준으로 그려.')
        else:
            L.append('두 번째 그림은 지금 쓰는 한글판이야. 문구는 같게, 그림 품질만 원본 수준으로 맞춰 줘.')
        L += ['```', '']
    open(os.path.join(OUT, '요청서.md'), 'w', encoding='utf-8').write('\n'.join(L))
    print('목록', len(lst), '(J %d, A %d) →' % (len(J), len(A)), OUT)


if __name__ == '__main__':
    main()
