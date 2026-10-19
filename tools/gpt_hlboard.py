"""평상시 ↔ 선택 글씨 짝을 **판 단위(전체판)**로 GPT에 다시 그리게 하는 묶음(10/20, 사용자 지시: 단어마다 잘라 주면 주변에서 GPT가 뭘 했는지 확인할 수 없음).

첨부 = 위 칸: 배경 판 전체(평상시) / 흰 줄 / 아래 칸: 같은 크기 바탕(검정 또는 자홍)에 그 판의 선택 글씨들을 게임과 같은 자리에 놓은 것.
반영 = 위 칸 → 판 전체 교체(판 모양 투명도는 일본판 그대로, 글자 조각 판은 자홍→투명),
       아래 칸 → 선택 글씨마다 원래 자리에서 잘라 선택 글씨 그림으로(검정 정리 / 자홍→투명).
자리·합성 방식·한국어는 tools/gpt_hlpair.py 의 PAIRS(일본판에서 찾고 겹침 확인한 값)를 그대로 쓴다.

python tools/gpt_hlboard.py prepare        → work/GPT/짝글씨_판/
python tools/gpt_hlboard.py import [판…]   → 결과/<판>.png 반영 + 비교/<판>.png
"""
import json
import hashlib
import os
import shutil
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gpt_hlpair import PAIRS, KEY, G, rgba, src, done  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'work', 'GPT', '짝글씨_판')
BAK = os.path.join(ROOT, 'work', 'GPT', '이전')
GAP = 4
NAMES = {'g049': '책 옵션 — 화면·자막 설정판', 'g054': '책 옵션 — 소리 설정판', 'g048': '책 옵션 — 컨트롤러 페이지',
         'g060': '책 — 무비 페이지', 'g046': '진동 「켬」 조각', 'g047': '진동 「끔」 조각',
         'g082': '인벤토리 화면(일반)', 'g084': '인벤토리 「조합하다」 판', 'g085': '인벤토리 「모드」 판', 'g037': '스펠 화면 버튼 줄'}


def unkey(rgb):
    """자홍 바탕 → 투명. 가장자리 화소는 가장 가까운 속(자홍 안 섞인) 화소 색을 기준으로 섞인 비율을 구해
    그 색·비율로 바꿈(자홍 섞인 색을 그대로 두면 게임에서 분홍 테두리, 10/20 사용자 화면)."""
    from scipy.ndimage import distance_transform_edt
    k = np.array(KEY, np.float32)
    d = np.sqrt(((rgb - k) ** 2).sum(2))
    solid = (d > 60) & (rgb[..., 2] <= rgb[..., 1])   # 자홍이 안 섞인 화소(노랑·갈색·검정은 파랑 ≤ 초록)
    if not solid.any():
        return np.zeros_like(rgb), np.zeros(rgb.shape[:2], np.float32)
    _, (iy, ix) = distance_transform_edt(~solid, return_indices=True)
    fg = rgb[iy, ix]
    v = fg - k
    t = np.clip(((rgb - k) * v).sum(2) / np.maximum((v * v).sum(2), 1), 0, 1)
    t[solid] = 1
    t[d < 60] = 0
    return np.where(t[..., None] > 0, np.where(solid[..., None], rgb, fg), 0), t * 255


def boards():
    out = {}
    for i, (b, x, y, mode, ko, desc) in PAIRS.items():
        out.setdefault(b, []).append((i, x, y, mode, ko))
    return out


def glyph_piece(b):
    """판 자체가 글자 모양 투명 조각인지(켬·끔): 투명이 많고 테두리 판 모양이 아님."""
    a = src(b)[..., 3]
    return bool((a < 250).mean() > 0.3) and b in ('g046', 'g047')


def base_board(b):
    """지금 한글판 판(GPT 1차 반영 전 것이 백업에 있으면 그것)."""
    p = os.path.join(BAK, b + '_짝이전.png')
    return rgba(p) if os.path.exists(p) else done(b)


def bottom_canvas(b, items, jp=True):
    bg = src(b); h, w = bg.shape[:2]
    mode = items[0][3]
    canvas = np.zeros((h, w, 3), np.float32) + (0 if mode == 'add' else np.array(KEY, np.float32))
    for i, x, y, md, ko in items:
        sp = src(i) if jp else done(i)
        sh, sw = sp.shape[:2]
        reg = canvas[y:y + sh, x:x + sw]
        if md == 'add':
            reg[:] = np.maximum(reg, sp[..., :3])
        else:
            a = sp[..., 3:] / 255; reg[:] = reg * (1 - a) + sp[..., :3] * a
    return canvas


def top_img(bg, key):
    t = bg[..., :3].copy()
    a = bg[..., 3:] / 255
    fill = np.array(KEY, np.float32) if key else np.array([60, 40, 80], np.float32)
    return t * a + fill * (1 - a)


def stack(top, bot):
    w = top.shape[1]
    return np.concatenate([top, np.full((GAP, w, 3), 255, np.float32), bot], 0).astype(np.uint8)


RULES = '''닌텐도 게임큐브 게임 「이터널 다크니스」 일본판 그림을 한국어판으로 바꾸는 작업이야.
이번 그림은 「배경 판 전체」와 「그 판 위에 선택했을 때 덮이는 글씨」를 한 장에 위아래로 놓은 거야. 가운데 흰 줄이 경계야.
  - 위 칸 = 평상시: 배경 판 전체(양피지·나무판 무늬, 테두리, 판 위의 모든 글자)
  - 아래 칸 = 선택 상태: 위 칸과 같은 크기의 바탕에, 선택했을 때 밝게 빛나거나 노랗게 덮이는 글자들만 위 칸과 똑같은 자리에 있음
게임은 아래 칸 글자를 위 칸의 같은 글자 위에 정확히 겹쳐 그려. 그래서 아래 칸에 있는 글자는 위 칸의 같은 글자와 모양·크기·굵기·위치가 픽셀까지 똑같아야 해.

[필수 규칙]
1. 결과는 PNG 한 장. 첨부한 일본판과 똑같은 구성(위 칸 / 흰 줄 / 아래 칸)과 가로세로 비율로. 크기는 첨부와 같거나 더 크게.
2. 위 칸: 판 무늬·색·테두리·그림은 일본판 그대로 두고, 일본어 글자만 내가 준 한국어로 바꿔. 판 위의 모든 일본어를 바꿔(내가 목록으로 줄게).
   영어·숫자(16:9, 4:3 등)는 그대로.
3. 아래 칸: 위 칸에서 바꾼 한국어 글자 가운데 선택 글씨에 해당하는 것만, 위 칸 글자를 그대로 복사해 같은 자리에 놓고 색·효과만 일본판 아래 칸처럼 바꿔.
   **원판 스크린샷처럼 검정 바탕 계열과 자홍 바탕 계열의 효과를 구분한다.**
   - 빛나는 글씨(바탕 검정): 평상시 글자색을 그대로 유지하고, 획 밖에만 4~6픽셀 빛을 더한다.
     선택용 가산 조각은 글자 획과 안티앨리어싱 자리에서 0(검정)이다. 밝기는 각 일본판 원본의 밝은 부분을 직접 채취한다(자막 원본의 비검정 97백분위 238, 16:9 참고 246). 80으로 제한하지 않는다. 게임이 노란색을 입힌다.
     획을 밝은색으로 채워 기존 검은 글씨를 노랗게 만들지 않는다. 가장자리의 빛은 공통 글자 마스크 역값으로 감쇠한다.
   - 노란 글씨(바탕 자홍): 글자 획 전체를 노란색으로 채우고, 바깥에 어두운 갈색(#45331A) 테두리 1픽셀 + 옅은 갈색 그림자 1~2픽셀.
     **분홍·보라 테두리 금지.** 갈색 테두리 바로 바깥은 곧장 순수 자홍(#FF00FF). 갈색과 자홍을 부드럽게 섞지 마(안티에일리어싱 끄고 딱 끊어서).
     그림자도 갈색·검정 계열로만, 자홍과 섞인 분홍·보라 화소가 한 개도 없게.
   아래 칸 바탕:
   - 「바탕 검정」이면 순수한 검정(#000000). 회색 금지(게임에서 네모 상자로 보임).
   - 「바탕 자홍」이면 순수한 자홍색(#FF00FF). 내가 투명으로 바꿀 거야.
   - 위 칸 판 바깥이 자홍인 그림은 위 칸 판 바깥도 자홍 그대로 둬.
4. 글꼴은 「연천 허목체」(붓글씨 느낌 한글 글꼴). 첨부한 「지금 한글판」 글자 모양은 따라 하지 마(색·위치만 참고).
   굵기·크기는 일본판 글자에 맞추고 일본판 글자가 있던 자리 안에. 위·아래 잘림 금지.
5. 한국어 맞춤법·글자 모양을 정확하게. 다 만든 뒤 한 자씩 확인하고 틀리면 다시 만들어.
6. 새로 그려 넣는 것 금지(테두리 상자, 워터마크, 서명 금지). 일본판에 없는 무늬를 더하거나 지우지 마.

이해했으면 "확인"이라고만 답하고, 내가 그림을 보낼 때까지 기다려.'''

# 판 위의 모든 글자(위 칸 바꿀 목록) — 지금 한글판 문구 기준
BOARD_TEXT = {
    'g049': '밝기 조절 / 자막 · 한국어 · 영어 / 와이드 화면 설정 · 16:9 · 4:3(숫자는 그대로)',
    'g054': '모드 · 모노 · 스테레오 · 스테레오 서라운드 / 음량',
    'g048': '컨트롤러 버튼 설명 전부(지금 한글판 참고 그림의 문구 그대로) + 진동 기능:',
    'g060': '영상',
    'g046': '켬', 'g047': '끔',
    'g082': '사용 · 장비 · 체크 (판의 다른 그림은 그대로)',
    'g084': '조합하다', 'g085': '모드',
    'g037': '사용 · 등록 · 체크',
}


def prepare():
    for d in ('원본', '참고', '결과', '비교'):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
    rows, meta = [], []
    for b, items in boards().items():
        jb = src(b); key = glyph_piece(b)
        up = lambda a: Image.fromarray(a).resize((a.shape[1] * s, a.shape[0] * s), Image.NEAREST)
        s = 2 if jb.shape[1] >= 300 else (4 if jb.shape[1] >= 120 else 8)
        up(stack(top_img(jb, key), bottom_canvas(b, items))).save(os.path.join(OUT, '원본', '%s_일본판_판전체_%d배.png' % (b, s)))
        kb = base_board(b)
        up(stack(top_img(kb, key), bottom_canvas(b, items, jp=False))).save(os.path.join(OUT, '참고', '%s_지금한글_%d배.png' % (b, s)))
        mode = items[0][3]
        word = '바탕 검정' if mode == 'add' else '바탕 자홍'
        if key:
            word += ', 위 칸 판 바깥도 자홍'
        sel = ' · '.join(ko for _, _, _, _, ko in items)
        meta.append(dict(board=b, w=int(jb.shape[1]), h=int(jb.shape[0]), key=bool(key), items=[dict(id=i, x=x, y=y, mode=m, ko=ko) for i, x, y, m, ko in items]))
        rows.append('| %s | %s | %s | %s | %d×%d (두 칸 합계 %d×%d) | %s | `%s.png` |' % (b, NAMES.get(b, ''), BOARD_TEXT.get(b, ''), sel, jb.shape[1], jb.shape[0], jb.shape[1], jb.shape[0] * 2 + GAP, word, b))
    json.dump(meta, open(os.path.join(OUT, '목록.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    md = ['# 짝 글씨 GPT 요청서 — 판 전체판', '',
          '단어마다 자른 판(`work/GPT/짝글씨`) 대신 **판 전체**를 위 칸, 그 판의 선택 글씨를 아래 칸에 놓았습니다. 넣은 뒤 판 전체를 비교 시트로 확인할 수 있습니다.', '',
          '| 폴더 | 내용 |', '|---|---|',
          '| `원본\\` | GPT에 첨부할 일본판(위 판 전체 / 흰 줄 / 아래 선택 글씨) |',
          '| `참고\\` | 지금 한글판 같은 구성(1차 GPT 반영 전) |',
          '| `결과\\` | **GPT 결과를 「저장할 이름」으로** (예: `g049.png`) |',
          '| `비교\\` | 반영하면 판 전체 비교 시트 |', '',
          '반영: `python tools/gpt_hlboard.py import` — 위 칸은 판 전체로, 아래 칸은 선택 글씨마다 제자리에서 잘라 넣습니다.', '',
          '## 1. 공통 규칙(처음 한 번)', '', '```', RULES, '```', '',
          '## 2. 그림마다 보낼 말', '', '`원본\\<판>_일본판_판전체_N배.png` 와 `참고\\<판>_지금한글_N배.png` 를 첨부하고:', '',
          '```', '위 칸의 일본어를 「(위 칸 글자)」로, 아래 칸 선택 글씨는 「(아래 칸 글자)」로 바꿔 줘. 아래 칸은 (바탕 검정 / 바탕 자홍).', '```', '',
          '## 3. 목록 (%d장)' % len(meta), '',
          '| 판 | 어디 | 위 칸 글자(판 전체) | 아래 칸 선택 글씨 | 게임 크기 | 바탕 | 저장할 이름 |', '|---|---|---|---|---|---|---|'] + rows
    open(os.path.join(OUT, '요청서.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')
    print('준비', len(meta), '판 →', OUT)


def native_bundle(m, result_path):
    """Use verified native exports when available, avoiding two lossy steps:
    shrinking keyed PNGs with Lanczos, and recropping overlapping glow slots.
    Hand-edited/unmatched result images retain the original import behavior.
    This reader performs no writes.
    """
    manifest_path = os.path.join(OUT, '비교', '제작자료', '선택효과_반영정보.json')
    if not os.path.exists(manifest_path):
        return None, {}
    with open(manifest_path, encoding='utf-8') as f:
        entry = json.load(f).get('boards', {}).get(m['board'])
    def file_hash(path):
        with open(path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    if not entry or file_hash(result_path) != entry.get('result_sha256'):
        return None, {}
    def checked(desc, size):
        path = os.path.abspath(os.path.join(OUT, desc['path']))
        if os.path.commonpath([os.path.abspath(OUT), path]) != os.path.abspath(OUT):
            raise ValueError('Native export path outside the result bundle')
        if file_hash(path) != desc['sha256']:
            raise ValueError('Native export changed; regenerate/verify: ' + path)
        im = Image.open(path).convert('RGB')
        if im.size != size:
            raise ValueError('Native export size mismatch: ' + path)
        return np.asarray(im).astype(np.float32)
    full = checked(entry['native_pair'], (m['w'], m['h'] * 2 + GAP))
    parts = {}
    for it in m['items']:
        sh, sw = src(it['id']).shape[:2]
        parts[it['id']] = checked(entry['selection'][it['id']], (sw, sh))
    return full, parts


def pending_layout_updates(meta, only=None):
    """Read-only preflight: never silently truncate expanded highlight assets."""
    path = os.path.join(OUT, '비교', '제작자료', '선택효과_반영정보.json')
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        records = json.load(f).get('boards', {})
    pending = []
    for m in meta:
        b = m['board']
        if only and b not in only:
            continue
        result_path = os.path.join(OUT, '결과', b + '.png')
        entry = records.get(b, {})
        if not entry.get('requires_game_texture_layout_update') or not os.path.exists(result_path):
            continue
        with open(result_path, 'rb') as f:
            current = hashlib.sha256(f.read()).hexdigest()
        if current == entry.get('result_sha256'):
            pending.append(b)
    return pending


def imp(only):
    meta = json.load(open(os.path.join(OUT, '목록.json'), encoding='utf-8'))
    pending = pending_layout_updates(meta, only)
    if pending:
        raise ValueError('선택 번짐 확장본은 기존 텍스처로 잘라 반영할 수 없습니다: '
                         + ', '.join(pending)
                         + '. 게임 텍스처 크기와 배치 확장이 필요합니다. '
                         + '비교/제작자료/영역확장_반영요구.json 참조. 게임 파일은 쓰지 않았습니다.')
    os.makedirs(BAK, exist_ok=True)
    F = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 14)
    for m in meta:
        b = m['board']
        p = os.path.join(OUT, '결과', b + '.png')
        if (only and b not in only) or not os.path.exists(p):
            continue
        w, h = m['w'], m['h']
        full, native_parts = native_bundle(m, p)
        if full is None:
            full = np.asarray(Image.open(p).convert('RGB').resize((w, h * 2 + GAP), Image.LANCZOS)).astype(np.float32)
        top, bot = full[:h], full[h + GAP:]
        jb = src(b)
        if not os.path.exists(os.path.join(BAK, b + '_짝이전.png')):
            shutil.copy2(os.path.join(G, 'done', b + '.png'), os.path.join(BAK, b + '_짝이전.png'))
        if m['key']:
            top, a = unkey(top)
        else:
            a = jb[..., 3]   # 판 모양은 일본판 그대로
        Image.fromarray(np.dstack([top, a]).round().astype(np.uint8), 'RGBA').save(os.path.join(G, 'done', b + '.png'))
        for it in m['items']:
            i, x, y = it['id'], it['x'], it['y']
            sp = src(i); sh, sw = sp.shape[:2]
            reg = native_parts[i] if i in native_parts else bot[y:y + sh, x:x + sw]
            if not os.path.exists(os.path.join(BAK, i + '_짝이전.png')):
                shutil.copy2(os.path.join(G, 'done', i + '.png'), os.path.join(BAK, i + '_짝이전.png'))
            if it['mode'] == 'add':
                rgb = reg if i in native_parts else np.clip((reg - 10) * 255 / 245, 0, 255)
                out = np.dstack([rgb, np.full((sh, sw), 255.0)])
            else:
                out = np.dstack(unkey(reg))
            Image.fromarray(out.round().astype(np.uint8), 'RGBA').save(os.path.join(G, 'done', i + '.png'))
        # 비교 시트: 일본판 판 | 일본판 전부 선택 | 한글 판(새로) | 한글 전부 선택(새로)
        def sel(board, items, jp):
            t = top_img(board, False).copy()
            for i2, x2, y2, md, ko in items:
                sp = src(i2) if jp else done(i2); sh, sw = sp.shape[:2]; r = t[y2:y2 + sh, x2:x2 + sw]
                if md == 'add':
                    r[:] = np.clip(r + sp[..., :3], 0, 255)
                else:
                    al = sp[..., 3:] / 255; r[:] = r * (1 - al) + sp[..., :3] * al
            return t
        items = [(it['id'], it['x'], it['y'], it['mode'], it['ko']) for it in m['items']]
        kb = done(b)
        cells = [top_img(jb, False), sel(jb, items, True), top_img(kb, False), sel(kb, items, False)]
        sheet = np.concatenate([np.pad(c.astype(np.uint8), ((3, 3), (3, 3), (0, 0)), constant_values=25) for c in cells], 1)
        s = 2 if w < 300 else 1
        im = Image.fromarray(sheet).resize((sheet.shape[1] * s, sheet.shape[0] * s), Image.NEAREST)
        lab = Image.new('RGB', (im.width, 24)); ImageDraw.Draw(lab).text((6, 3), '%s %s — 일본판 | 일본판 선택 | 한글(새로) | 한글 선택(새로)' % (b, NAMES.get(b, '')), font=F, fill=(255, 255, 0))
        o = Image.new('RGB', (im.width, im.height + 24)); o.paste(lab, (0, 0)); o.paste(im, (0, 24))
        o.save(os.path.join(OUT, '비교', b + '.png'))
        print('반영', b, [it['id'] for it in m['items']])


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        prepare()
    else:
        imp(sys.argv[2:])
