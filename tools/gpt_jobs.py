"""GPT 그림 재작업 목록(10/11): 그림마다 번호·한국어 문구·크기·투명 여부를 모은다. gpt_prepare·gpt_import 가 쓴다.

종류
  A  이미 한글화한 그림(일본판 원본에서 다시 그리기). 문구는 지금 패치와 같다.
  J  지금 북미판(또는 일본판 디스크 영어판) 그림·로고를 쓰는 곳 → 일본판 원본을 한국어로(10/11 사용자 결정: 북미판 에셋 안 씀).
     로고의 「ETERNAL DARKNESS」 영문은 그대로, 아래 일본어 부제만 한국어로. 부제 번역은 번역안.
문구 출처: 그림 도구 설정(work/gfx/*.json, tools/gfx_*.py 의 상수)을 소스 그대로 읽는다(도구를 import 하지 않음).
"""
import ast
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, 'work', 'gfx')
T = os.path.join(ROOT, 'tools')

LOGO_JA = 'エターナルダークネス ─招かれた13人─'
LOGO_KO = '이터널 다크니스 ─초대받은 13인─'            # 번역안(招かれた13人 = 초대받은 13인)
LOGO_NOTE = '로고의 영문 「ETERNAL DARKNESS」는 그대로 두고, 그 아래 일본어 부제 「%s」만 「%s」로 바꿔.' % (LOGO_JA, LOGO_KO)

# J: 북미판·영어판 에셋을 쓰던 곳
J_ITEMS = {
    'g123': {'title': '타이틀 화면',
             'lines': ['(로고 부제) ' + LOGO_KO, '(배경에 어둡게 박힌 메뉴) 시작하기 / 불러오기 / 옵션'],
             'note': LOGO_NOTE + ' 오른쪽 아래 어둡게 박힌 메뉴 글씨 「スタート / ロード / オプション」는 같은 어두운 색·같은 자리로 「시작하기 / 불러오기 / 옵션」. '
                     '「© 2002 Nintendo」는 그대로. (밝은 메뉴 글씨는 게임이 따로 덮어 그리니 어두운 바탕 글씨만 바꾸면 돼.)',
             'was': '일본판 배경 + 일본판 디스크 영어판(북미판과 같은) 로고 합성'},
    'g126': {'title': 'Coming Soon 화면',
             'lines': ['(위 문구) 더 거센 싸움은, 기대되는 다음 작품에서…', '(로고 부제) 이터널 다크니스 ─깨어난 13인─'],
             'note': '위쪽 일본어 「更なる戦いは、期待の次回作で…」를 「더 거센 싸움은, 기대되는 다음 작품에서…」로(같은 서체 느낌·색). '
                     '로고의 영문 「ETERNAL DARKNESS」는 그대로, 아래 부제 「エターナルダークネス ─目覚めた13人─」은 「이터널 다크니스 ─깨어난 13인─」으로. '
                     '아래 영문 「Coming Soon...」은 그대로.',
             'was': '일본판 디스크 영어판 그림으로 통째 교체'},
    'cover': {'title': '프롤로그 책 표지', 'group': '컷신 장면 텍스처', 'file': 'Levels/Level16/cin0069', 'slot': '1877번 레코드',
              'lines': ['(로고 부제) ' + LOGO_KO],
              'note': LOGO_NOTE + ' 표지 가죽·해골 장식·금속 고리는 원본 그대로.',
              'was': '북미판 표지 그림(Sanity\'s Requiem)'},
}
LOGO_IN = {'g127': '옵션 화면', 'g128': '메모리 카드 화면'}   # 로고만 북미판으로 합성한 메뉴 그림


def _consts(name):
    tree = ast.parse(open(os.path.join(T, name + '.py'), encoding='utf-8').read())
    out = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            try:
                out[n.targets[0].id] = ast.literal_eval(n.value)
            except Exception:
                pass
    return out


def texts():
    """{id: [줄, ...]} 지금 패치에 들어간 그림 문구."""
    t = {}
    for k, v in json.load(open(os.path.join(G, 'autopsy_ko.json'), encoding='utf-8')).items():
        t[k] = list(v)
    for k, v in json.load(open(os.path.join(G, 'book_cfg.json'), encoding='utf-8')).items():
        t[k] = [line for r in v['regions'] for line in r[5]]
    for k, v in _consts('gfx_glowbtn')['CFG'].items():
        t[k] = [x for x in v['text'].split('|')]
    for k, v in _consts('gfx_tab')['CFG'].items():
        t[k] = [v]
    for k, v in _consts('gfx_menu')['CFG'].items():
        t[k] = [s for _, s in v['lines']]
    t['g125'] = list(_consts('gfx_ending')['LINES'])
    c = _consts('gfx_endsave'); t['g162'] = list(c['PARA']) + [s for s, _ in c['CHOICES']]
    for k, v in _consts('gfx_slotsmall')['CFG'].items():
        t[k] = [v['text']]
    for k, v in _consts('gfx_mono')['CFG'].items():
        t[k] = list(v['lines'])
    c = _consts('gfx_poe'); t['g170'] = [s for s, *_ in c['LINES']] + ['(서명) ' + c['SIGN'][0]]
    return t


NOTES = {   # 그림별 덧붙임(원본에서 그대로 둘 것 등)
    'g125': '맨 위 제목의 영문·점(…)은 원본 그대로. 아래 일본어 세 줄만 한국어로.',
    'g090': '흑백 두 색(검정 바탕·흰 글자)만 써. 회색·번짐 금지(원본처럼 1비트 글자).',
    'g170': '에드거 앨런 포 「갈까마귀」 인용. 빛줄기 효과는 원본처럼 글자에서 퍼지게.',
}


def jobs():
    plan = [l.rstrip('\n').split('\t') for l in open(os.path.join(G, 'plan.tsv'), encoding='utf-8')][1:]
    tx = texts()
    out = []
    from PIL import Image
    for gid, grp, f, slot, size, kind, rep, st in plan:
        if st.startswith('원본 유지'):
            continue
        w, h = map(int, size.split('x'))
        src = os.path.join(G, 'src', gid + '_jp.png')
        a = Image.open(src).convert('RGBA').getchannel('A')
        transparent = a.getextrema()[0] < 250
        j = J_ITEMS.get(gid)
        if j:
            out.append(dict(id=gid, kind='J', group=grp, title=j['title'], file=f.replace('jp/', ''), slot=slot, w=w, h=h,
                            transparent=transparent, lines=j['lines'], note=j['note'], was=j['was'],
                            src=src, cur=os.path.join(G, 'done', gid + '.png') if kind == '번역' else os.path.join(G, 'src', gid + '_e.png')))
            continue
        lines = tx[gid]
        note = NOTES.get(gid, '')
        k = 'A'
        if gid in LOGO_IN:
            k = 'J'
            lines = lines + ['(로고 부제) ' + LOGO_KO]
            note = (note + ' ' if note else '') + LOGO_NOTE
        out.append(dict(id=gid, kind=k, group=grp, title=LOGO_IN.get(gid, grp), file=f.replace('jp/', ''), slot=slot, w=w, h=h,
                        transparent=transparent, lines=lines, note=note,
                        was='메뉴 글씨는 한글, 로고는 북미판 합성' if gid in LOGO_IN else '',
                        src=src, cur=os.path.join(G, 'done', gid + '.png')))
    c = J_ITEMS['cover']
    out.append(dict(id='cover', kind='J', group=c['group'], title=c['title'], file=c['file'], slot=c['slot'], w=640, h=480,
                    transparent=False, lines=c['lines'], note=c['note'], was=c['was'],
                    src=os.path.join(G, 'src', 'cover_jp.png'), cur=os.path.join(G, 'src', 'cover_us.png')))
    return out


if __name__ == '__main__':
    import collections
    js = jobs()
    print(len(js), collections.Counter(j['kind'] for j in js))
    for j in js[:3] + [x for x in js if x['kind'] == 'J']:
        print(j['id'], j['kind'], j['title'], j['w'], j['h'], j['transparent'], j['lines'][:3])
