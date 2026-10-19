"""평상시 글씨 ↔ 선택(커서·강조) 글씨 짝을 GPT에 한 장으로 다시 그리게 하는 묶음(10/20, 사용자 결정 「GPT가 둘 다 한 장에」).

일본판은 같은 글자 모양을 평상시는 배경 판에 어둡게(또는 회색 새김), 선택 때는 따로 된 그림으로 밝게 그려 획이 완전히 겹친다.
한글판은 둘을 따로 만들어 어긋났다(사용자 제보 10/20, work/feedback_1020/목록.md).
GPT에게 「위 = 평상시(배경 판 그 자리), 아래 = 선택 글씨」 두 칸을 같은 글자 모양으로 그리게 하고,
받은 그림을 둘로 잘라 위 칸은 배경 판의 그 자리에, 아래 칸은 선택 글씨 그림으로 넣는다.

python tools/gpt_hlpair.py prepare        → work/GPT/짝글씨/ (원본·참고·결과·비교, 요청서.md)
python tools/gpt_hlpair.py import [id…]   → 결과/<id>.png 를 반영(work/gfx/done/<배경>.png 의 그 자리 + <id>.png), 비교 시트
"""
import json
import os
import shutil
import sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, 'work', 'gfx')
OUT = os.path.join(ROOT, 'work', 'GPT', '짝글씨')
SCALE = 8
KEY = (255, 0, 255)   # 투명 바탕 선택 글씨는 GPT에 자홍색 바탕으로 그리게 해서 투명으로 바꿈

# id: (배경 판, 원점 x, y, 합성, 한국어, 설명) — 원점은 tools/pair_find.py 로 일본판에서 찾고 겹침 시트로 확인(10/20)
#   합성 add  = 더하기(선택 글씨 바탕은 완전 검정, 빛나는 글씨)
#   합성 alpha = 투명도(선택 글씨 바탕은 투명, 노란 글씨+어두운 테두리)
PAIRS = {
    'g061': ('g060', 10, 405, 'add', '영상', '책 옵션 화면 「영상」(무비 페이지)'),
    'g059': ('g048', 109, 393, 'add', '진동 기능:', '책 옵션 컨트롤러 페이지 「진동 기능:」'),
    'g057': ('g046', 0, 0, 'add', '켬', '진동 기능 「켬」'),
    'g058': ('g047', 0, 0, 'add', '끔', '진동 기능 「끔」'),
    'g052': ('g049', 257, 59, 'add', '영어', '자막 설정 「영어」'),
    'g053': ('g049', 164, 62, 'add', '한국어', '자막 설정 「한국어」(일본판 「日本語」 자리)'),
    'g068': ('g054', 224, 11, 'add', '스테레오', '소리 설정 「스테레오」'),
    'g055': ('g054', 123, 34, 'add', '스테레오 서라운드', '소리 설정 「스테레오 서라운드」'),
    'g056': ('g054', 121, 6, 'add', '모노', '소리 설정 「모노」'),
    'g081': ('g082', 127, 203, 'alpha', '사용', '인벤토리 버튼 「사용」'),
    'g087': ('g082', 124, 234, 'alpha', '장비', '인벤토리 버튼 「장비」'),
    'g086': ('g082', 126, 265, 'alpha', '체크', '인벤토리 버튼 「체크」'),
    'g088': ('g084', 8, 2, 'alpha', '조합하다', '인벤토리 버튼 「조합하다」'),
    'g089': ('g085', 8, 1, 'alpha', '모드', '인벤토리 버튼 「모드」'),
    'g072': ('g037', 10, 17, 'alpha', '사용', '스펠 화면 버튼 「사용」'),
    'g071': ('g037', 92, 29, 'alpha', '등록', '스펠 화면 버튼 「등록」'),
    'g035': ('g037', 175, 16, 'alpha', '체크', '스펠 화면 버튼 「체크」'),
}


def rgba(p):
    return np.asarray(Image.open(p).convert('RGBA')).astype(np.float32)


def src(i):
    return rgba(os.path.join(G, 'src', i + '_jp.png'))


def done(i):
    return rgba(os.path.join(G, 'done', i + '.png'))


def two_state(bg, sp, x, y, mode, key=False):
    """위 = 배경 판 그 자리(평상시), 아래 = 선택 글씨(더하기는 검정 바탕, 투명은 자홍/체크무늬 바탕)."""
    h, w = sp.shape[:2]
    reg = bg[y:y + h, x:x + w]
    top = reg[..., :3]
    if (reg[..., 3] < 250).any():   # 평상시 글씨도 투명 조각(켬·끔 판)이면 위 칸도 투명 바탕 표시
        tb = np.zeros((h, w, 3), np.float32) + (np.array(KEY, np.float32) if key else 0)
        if not key:
            yy, xx = np.mgrid[:h, :w]; tb += (((yy // 4 + xx // 4) % 2) * 60 + 80)[..., None]
        ta = reg[..., 3:] / 255
        top = tb * (1 - ta) + top * ta
    if mode == 'add':
        bot = sp[..., :3]
    else:
        base = np.zeros((h, w, 3), np.float32) + (np.array(KEY, np.float32) if key else 0)
        if not key:
            yy, xx = np.mgrid[:h, :w]; base += (((yy // 4 + xx // 4) % 2) * 60 + 80)[..., None]
        a = sp[..., 3:] / 255
        bot = base * (1 - a) + sp[..., :3] * a
    gap = np.full((2, w, 3), 255, np.float32)   # 두 칸 사이 흰 줄(경계 표시)
    return np.concatenate([top, gap, bot], 0).astype(np.uint8)


def up(a):
    im = Image.fromarray(a)
    return im.resize((im.width * SCALE, im.height * SCALE), Image.NEAREST)


RULES = '''닌텐도 게임큐브 게임 「이터널 다크니스」 일본판 그림을 한국어판으로 바꾸는 작업이야.
이번 그림들은 「같은 글자를 두 상태로 그린 짝」이야. 첨부한 일본판 그림은 위아래 두 칸이고, 가운데 흰 줄이 경계야.
  - 위 칸 = 평상시: 배경 판(양피지·나무판)에 글자가 어둡게(또는 회색으로 새겨져) 있는 모습
  - 아래 칸 = 선택했을 때: 같은 글자가 밝게 빛나거나 노랗게 덮이는 모습
게임은 아래 칸 글자를 위 칸 글자 위에 정확히 겹쳐 그려. 그래서 두 칸의 글자는 모양·크기·굵기·위치가 픽셀까지 똑같아야 해.

[필수 규칙]
1. 결과는 PNG 한 장. 첨부한 일본판과 똑같은 구성(위 칸 / 흰 줄 / 아래 칸)과 가로세로 비율로 그려. 크기는 첨부와 같거나 더 크게.
2. 두 칸 모두 일본어 글자를 내가 준 한국어로 바꾸고, 두 칸의 한국어 글자 모양·위치를 완전히 똑같이 맞춰.
   한 칸에서 글자를 정하고, 다른 칸은 그 글자를 그대로 복사해서 색·효과만 바꾸는 식으로 만들어.
3. 위 칸: 배경 판 무늬·색·테두리는 일본판 그대로 두고 글자만 바꿔. 글자 색은 일본판 위 칸 글자 색 그대로.
4. 아래 칸 바탕:
   - 「바탕 검정」이라고 한 그림은 글자 밖을 순수한 검정(#000000)으로. 회색·어두운 회색 금지(게임에서 네모 상자로 보임).
   - 「바탕 자홍」이라고 한 그림은 글자 밖을 순수한 자홍색(#FF00FF)으로. 자홍색은 내가 투명으로 바꿀 거야.
   글자의 빛 번짐·어두운 테두리는 일본판 아래 칸처럼 그려.
5. 글꼴은 「연천 허목체」(붓글씨 느낌 한글 글꼴)로 써. 첨부한 「지금 한글판」 글자 모양을 따라 하지 마(참고는 색·위치만).
   굵기·크기는 일본판 글자에 맞추고, 일본판 글자가 차지하던 자리 안에 들어가게 해. 위·아래가 잘리면 안 돼.
6. 한국어 맞춤법·글자 모양을 정확하게. 다 만든 뒤 한 자씩 확인하고 틀리면 다시 만들어.
7. 새로 그려 넣는 것 금지(테두리 상자, 워터마크, 서명 금지).

참고로 「지금 한글판」 그림도 같이 줄게. 지금 패치에 들어간 위 칸(평상시) 모습이야. 글꼴은 따라 하지 말고(규칙 5: 연천 허목체), 색·위치만 참고해.

이해했으면 "확인"이라고만 답하고, 내가 그림을 보낼 때까지 기다려.'''


def prepare():
    for d in ('원본', '참고', '결과', '비교'):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
    rows, meta = [], []
    for i, (b, x, y, mode, ko, desc) in PAIRS.items():
        sp = src(i); h, w = sp.shape[:2]
        jb = src(b); kb = done(b)
        up(two_state(jb, sp, x, y, mode)).save(os.path.join(OUT, '원본', '%s_일본판_두칸_%d배.png' % (i, SCALE)))
        up(kb[y:y + h, x:x + w, :3].astype(np.uint8)).save(os.path.join(OUT, '참고', '%s_지금한글_위칸_%d배.png' % (i, SCALE)))
        bgword = '바탕 검정' if mode == 'add' else '바탕 자홍'
        if (jb[y:y + h, x:x + w, 3] < 250).any():
            bgword += ', 위 칸도 바탕 자홍'
        top_alpha = bool((jb[y:y + h, x:x + w, 3] < 250).any())
        meta.append(dict(id=i, bg=b, x=x, y=y, w=w, h=h, mode=mode, ko=ko, desc=desc, top_alpha=top_alpha))
        rows.append('| %s | %s | %s | %d×%d (두 칸 합계 %d×%d) | %s | `%s.png` |' % (i, desc, ko, w, h, w, h * 2 + 2, bgword, i))
    json.dump(meta, open(os.path.join(OUT, '목록.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    md = ['# 짝 글씨(평상시 ↔ 선택) GPT 요청서', '',
          '사용자 화면 피드백(10/20, `work/feedback_1020/목록.md`) 반영용. 평상시 글씨와 선택 글씨가 어긋난 곳을 **한 장에 두 상태로** 다시 그려 받습니다.', '',
          '## 폴더', '', '| 폴더 | 내용 |', '|---|---|',
          '| `원본\\` | GPT에 첨부할 일본판 두 칸 그림(위 평상시 / 흰 줄 / 아래 선택, 8배 확대) |',
          '| `참고\\` | 지금 한글판 위 칸(평상시) 모습, 8배 |',
          '| `결과\\` | **GPT 결과를 「저장할 이름」으로 저장** (예: `g061.png`) |',
          '| `비교\\` | 반영하면 비교 시트가 생깁니다 |', '',
          '결과를 저장한 뒤 말해 주면 `python tools/gpt_hlpair.py import` 로 넣고 비교 시트를 보내 드립니다.',
          '- 위 칸은 배경 판의 그 자리에, 아래 칸은 선택 글씨 그림으로 들어갑니다.',
          '- 「바탕 검정」 그림은 어두운 부분을 완전 검정으로 정리하고, 「바탕 자홍」 그림은 자홍색을 투명으로 바꿉니다.', '',
          '## 1. 맨 처음 한 번만 붙여 넣을 공통 규칙', '', '```', RULES, '```', '',
          '## 2. 그림마다 보낼 말', '',
          '`원본\\<번호>_일본판_두칸_8배.png` 와 `참고\\<번호>_지금한글_위칸_8배.png` 를 첨부하고:', '',
          '```', '이 그림의 일본어를 「(한국어)」로 바꿔서 두 칸 모두 같은 글자 모양으로 그려 줘. 아래 칸은 (바탕 검정 / 바탕 자홍).', '```', '',
          '## 3. 목록 (%d개)' % len(PAIRS), '',
          '| 번호 | 어디 | 한국어 | 게임 크기 | 아래 칸 바탕 | 저장할 이름 |', '|---|---|---|---|---|---|'] + rows + ['',
          '## 이번에 빠진 것', '',
          '- 와이드(16:9) 인벤토리 버튼 노란 글씨(g109 사용·g114 장비·g113 체크·g115 조합·g116 모드): 일본판에서 배경 글씨와의 자리를 확실히 못 찾음. 와이드 화면 캡처를 받으면 추가.']
    open(os.path.join(OUT, '요청서.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')
    print('준비', len(PAIRS), '→', OUT)


def imp(ids):
    meta = {m['id']: m for m in json.load(open(os.path.join(OUT, '목록.json'), encoding='utf-8'))}
    bak = os.path.join(ROOT, 'work', 'GPT', '이전'); os.makedirs(bak, exist_ok=True)
    for i in ids or sorted(meta):
        p = os.path.join(OUT, '결과', i + '.png')
        if not os.path.exists(p):
            continue
        m = meta[i]; w, h = m['w'], m['h']
        im = Image.open(p).convert('RGB')
        full = np.asarray(im.resize((w, h * 2 + 2), Image.LANCZOS)).astype(np.float32)
        top, bot = full[:h], full[h + 2:]
        # 아래 칸 → 선택 글씨
        if m['mode'] == 'add':
            spr = np.clip((bot - 10) * 255 / 245, 0, 255)            # 어두운 바탕은 완전 검정으로
            out = np.dstack([spr, np.full((h, w), 255.0)])
        else:
            d = np.sqrt(((bot - np.array(KEY, np.float32)) ** 2).sum(2))
            a = np.clip((d - 60) / 80, 0, 1)                          # 자홍색 → 투명
            out = np.dstack([bot, a * 255])
        dst = os.path.join(G, 'done', i + '.png')
        shutil.copy2(dst, os.path.join(bak, i + '_짝이전.png'))
        Image.fromarray(out.round().astype(np.uint8), 'RGBA').save(dst)
        # 위 칸 → 배경 판 그 자리(가장자리 2px 부드럽게)
        bp = os.path.join(G, 'done', m['bg'] + '.png'); b = rgba(bp)
        if not os.path.exists(os.path.join(bak, m['bg'] + '_짝이전.png')):
            shutil.copy2(bp, os.path.join(bak, m['bg'] + '_짝이전.png'))
        x, y = m['x'], m['y']
        wgt = np.ones((h, w), np.float32); r = 2
        for k in range(r):
            f = (k + 1) / (r + 1); wgt[k, :] = np.minimum(wgt[k, :], f); wgt[-1 - k, :] = np.minimum(wgt[-1 - k, :], f)
            wgt[:, k] = np.minimum(wgt[:, k], f); wgt[:, -1 - k] = np.minimum(wgt[:, -1 - k], f)
        if m.get('top_alpha'):   # 평상시도 투명 조각: 자홍 → 투명, 칸 전체 교체
            d = np.sqrt(((top - np.array(KEY, np.float32)) ** 2).sum(2))
            b[y:y + h, x:x + w, :3] = top; b[y:y + h, x:x + w, 3] = np.clip((d - 60) / 80, 0, 1) * 255
        else:
            reg = b[y:y + h, x:x + w, :3]
            b[y:y + h, x:x + w, :3] = reg * (1 - wgt[..., None]) + top * wgt[..., None]
        Image.fromarray(b.round().astype(np.uint8), 'RGBA').save(bp)
        print('반영', i, '→', m['bg'], (x, y))


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        prepare()
    else:
        imp(sys.argv[2:])
