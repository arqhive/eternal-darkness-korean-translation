"""4단계 전수 추출: 번역 단위 표 → work/text/units.json, work/text/units.xlsx, work/text/report.txt

번역 단위 = 일본판 디스크의 일본어 레코드(넣을 자리). 같은 (분야, 라벨, 일본어 원문)은 한 단위로 묶고 위치를 모두 적는다.
영어 원문: 일본판 디스크의 같은 라벨 영어 레코드 → 북미판 같은 파일 묶음에서 문장 내용으로 대응(완전 일치 > 유사도).
  최종 원문 en = 북미판 문장(없으면 일본판 디스크 영어).
일본어 ja = 글리프 대응표(work/glyphmap.tsv)로 푼 문장(한자 일부 오인식 가능, 높임 참고용).
"""
import difflib
import json
import os
import re
import struct
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpe
import check_overflow
import edtext
import measure
import txtpak

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
JP = os.path.join(ROOT, 'extract', 'jp'); US = os.path.join(ROOT, 'extract', 'us')
DJP = os.path.join(ROOT, 'extract', 'dec', 'jp'); DUS = os.path.join(ROOT, 'extract', 'dec', 'us')
OUT = os.path.join(ROOT, 'work', 'text')

GM = {int(l.split('\t')[0], 16): l.split('\t')[1] for l in open(os.path.join(ROOT, 'work', 'glyphmap.tsv'), encoding='utf-8')}
_FX = os.path.join(ROOT, 'work', 'glyph_fix.tsv')  # 문맥으로 바로잡은 한자(tools/glyph_fix.py)
if os.path.exists(_FX):
    GM.update({int(l.split('\t')[0], 16): l.split('\t')[1] for l in open(_FX, encoding='utf-8')})


def jdec(t):
    return ''.join(chr(c) if c < 0x80 else GM.get(c, '□') for c in measure.codes_of(t))


def wide_ascii(t):
    """2바이트 글리프 중 상위 0 인 영어 → 문자열."""
    return ''.join(chr(c) if c < 0x100 else '□' for c in measure.codes_of(t))


def is_ja(t):
    return any(t[0::2])


# ---------- 레코드 읽기 ----------
def recs_tabs(tabs, wide):
    """(표, 번호, 라벨, 텍스트 bytes)"""
    for ti, t in enumerate(tabs):
        for k, it in enumerate(t):
            if isinstance(it, tuple):
                continue
            body, _ = bpe.decode(it, 4)
            lab, txt = edtext.parse_body(struct.unpack('>I', it[:4])[0], body, wide)
            if txt is not None:
                yield ti, k, lab, txt


def pak_blocks(path):
    d = open(path, 'rb').read(); n = struct.unpack('>I', d[:4])[0]
    for i in range(n):
        o, s = struct.unpack('>II', d[8 + 8 * i:16 + 8 * i])
        if not s:
            continue
        blk = d[o:o + s]
        try:
            tabs = txtpak.parse(struct.pack('>I', len(blk)) + blk)
        except Exception:
            continue
        yield i, tabs


def read_pak(path, wide):
    """시스템·책 묶음: (블록, 표, 번호, 라벨, 텍스트)"""
    for blk, tabs in pak_blocks(path):
        for ti, k, lab, txt in recs_tabs(tabs, wide):
            yield blk, ti, k, lab, txt


def read_scan(path, wide):
    d = open(path, 'rb').read()
    for st, ents in edtext.tables(d):
        for k, (o, l) in enumerate(ents):
            try:
                head, body = edtext.record(d, st, o, l)
            except Exception:
                continue
            lab, txt = edtext.parse_body(head, body, wide)
            if txt is not None:
                yield st, 0, k, lab, txt


def us_texts(paths):
    out = []
    for p in paths:
        if not os.path.exists(p):
            continue
        if os.path.basename(p).startswith('RmTxt'):
            it = ((0, ti, k, lab, txt) for ti, k, lab, txt in recs_tabs(txtpak.parse(open(p, 'rb').read()), False))
        elif os.path.basename(p).startswith('cin'):
            d = open(p, 'rb').read(); parts = txtpak.cin_parts(d)
            it = ((i, ti, k, lab, txt) for i in range(1, len(parts)) if parts[i][1]
                  for ti, k, lab, txt in recs_tabs(txtpak.cin_text(d, i), False))
        elif os.path.basename(p).startswith('EMemcard'):
            it = read_scan(p, False)
        else:
            it = read_pak(p, False)
        for blk, ti, k, lab, txt in it:
            out.append(txt.decode('latin1'))
    return out


def norm(s):
    return re.sub(r'\s+', ' ', s or '').strip()


# ---------- 단위 수집 ----------
units = {}   # key -> dict
order = []


def add(group, label, ja_bytes, loc, en_jp, extra):
    """같은 (분야, 라벨, 영어 원문)은 한 단위. 영어가 없으면 일본어로 구분. 일본어 변형(음성 언어판 등)은 모두 보관."""
    key = (group, label, norm(en_jp)) if en_jp is not None else (group, label, '#' + ja_bytes.hex())
    ja = jdec(ja_bytes)
    if key not in units:
        units[key] = dict(id='%s:%s' % (group, label) if label else '%s:%s' % (group, loc), group=group, label=label,
                          ja=ja, ja_alt=[], en_jp=en_jp, locs=[], **extra)
        order.append(key)
    u = units[key]
    if ja != u['ja'] and ja not in u['ja_alt']:
        u['ja_alt'].append(ja)
    u['locs'].append(loc)


def speaker_of(label):
    name = label.split('/')[-1]
    m = re.match(r'([A-Z][A-Z0-9]+)_', name)
    return m.group(1) if m else ''


def collect():
    us_pool = {}
    # 방 문구
    for lv in sorted(os.listdir(os.path.join(DJP, 'Levels'))):
        n = lv.replace('Level', '')
        pj = os.path.join(DJP, 'Levels', lv, 'JRmTxt%s.cmp' % n)
        pw = os.path.join(DJP, 'Levels', lv, 'JRWTxt%s.cmp' % n)
        if not os.path.exists(pj):
            continue
        en = {lab: txt.decode('latin1') for ti, k, lab, txt in recs_tabs(txtpak.parse(open(pw, 'rb').read()), False)} if os.path.exists(pw) else {}
        us_pool['room', lv] = us_texts([os.path.join(DUS, 'RmTxt%s.cmp' % n)])
        for ti, k, lab, txt in recs_tabs(txtpak.parse(open(pj, 'rb').read()), True):
            add('room', lab, txt, '%s/JRmTxt%s.cmp#%d.%d' % (lv, n, ti, k), en.get(lab),
                dict(kind='room', speaker='', pool=('room', lv), room=lab.split('/')[0]))
    # 컷신 자막
    for lv in sorted(os.listdir(os.path.join(DJP, 'Levels'))):
        for f in sorted(os.listdir(os.path.join(DJP, 'Levels', lv))):
            if not (f.startswith('cin') and f.endswith('.bin')):
                continue
            d = open(os.path.join(DJP, 'Levels', lv, f), 'rb').read()
            try:
                parts = txtpak.cin_parts(d)
            except Exception:
                continue
            ja, en = [], {}
            for i in range(1, len(parts)):
                if not parts[i][1]:
                    continue
                for ti, k, lab, txt in recs_tabs(txtpak.cin_text(d, i), True):
                    if is_ja(txt):
                        ja.append((i, ti, k, lab, txt))
                    else:
                        en[lab] = wide_ascii(txt)
            cn = f[:-4]
            us_pool['cin', cn] = us_texts([os.path.join(DUS, 'Chars', cn, f)])
            for i, ti, k, lab, txt in ja:
                add('cin', lab, txt, '%s/%s#%d.%d.%d' % (lv, f, i, ti, k), en.get(lab),
                    dict(kind='subtitle', speaker=speaker_of(lab), pool=('cin', cn)))
    # 시스템·책·메모리 카드
    for group, jfiles, efile, usfile, reader in [
            ('memcard', ['JMemcardText.bin'], 'JMemcardTextW.bin', 'EMemcardText.bin', read_scan),
            ('boot', ['JBtPakJS.bin', 'JBtPakES.bin', 'JBootPak.bin'], 'JBootPkW.bin', 'EBootPak.bin', read_pak),
            ('book', ['JBkPkJJS.bin', 'JBkPkJES.bin'], 'JBkPkEES.bin', 'EBookPak.bin', read_pak)]:
        en = {}
        for blk, ti, k, lab, txt in reader(os.path.join(JP, efile), False):
            en[lab] = txt.decode('latin1')
        us_pool[group, ''] = us_texts([os.path.join(US, usfile)])
        for jf in jfiles:
            for blk, ti, k, lab, txt in reader(os.path.join(JP, jf), True):
                if not is_ja(txt):
                    continue
                kind = check_overflow.kind_of(group, blk, lab.split('/')[-1]) if group != 'memcard' else 'memcard'
                if group == 'book':
                    kind = 'memcard' if blk == 2 else 'book'
                spk = speaker_of(lab) if (group == 'boot' and blk in (8, 9, 12)) or group == 'book' else ''
                g = 'memcard' if kind == 'memcard' else group   # 책 묶음 2번 블록 = 메모리 카드 문구와 같음
                add(g, lab, txt, '%s#%s.%d.%d' % (jf, blk, ti, k), en.get(lab),
                    dict(kind=kind, speaker=spk, pool=(g, '')))
    return us_pool


# ---------- 북미판 대응 ----------

def match_us(us_pool):
    stat = defaultdict(int)
    used = defaultdict(set)
    for key in order:
        u = units[key]
        pool = us_pool.get(u['pool'], [])
        src = u['en_jp']
        if src is None:
            u['en'] = ''; u['en_src'] = '영어 없음'; stat['영어 없음'] += 1; continue
        n = norm(src)
        hit = [i for i, t in enumerate(pool) if norm(t) == n]
        if hit:
            u['en'] = pool[hit[0]]; u['en_src'] = '북미 일치'; used[u['pool']].add(hit[0]); stat['북미 일치'] += 1; continue
        best, bi = 0, -1
        for i, t in enumerate(pool):
            r = difflib.SequenceMatcher(None, norm(t), n).quick_ratio()
            if r > best - 0.0001 and r >= 0.5:
                r2 = difflib.SequenceMatcher(None, norm(t), n).ratio()
                if r2 > best:
                    best, bi = r2, i
        if bi >= 0 and best >= 0.6:
            u['en'] = pool[bi]; u['en_src'] = '북미 유사 %.2f' % best; used[u['pool']].add(bi); stat['북미 유사'] += 1
        else:
            u['en'] = src; u['en_src'] = '일본판 디스크 영어'; stat['북미 없음(일본판 영어 사용)'] += 1
    unused = sum(len(p) - len(used[k]) for k, p in us_pool.items())
    return stat, unused


def write_xlsx(rows):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    wb = Workbook(); ws = wb.active; ws.title = '번역 단위'
    cols = [('id', 34), ('group', 8), ('kind', 10), ('speaker', 10), ('en', 60), ('ja', 50), ('ko', 50),
            ('en_src', 14), ('en_jp', 40), ('en_near', 40), ('ja_alt', 30), ('locs', 30)]
    ws.append([c for c, w in cols])
    for c in ws[1]:
        c.font = Font(bold=True)
    for r in rows:
        ws.append([('\n'.join(r.get(c) or []) if c in ('ja_alt', 'locs') else r.get(c, '')) for c, w in cols])
    for i, (c, w) in enumerate(cols):
        ws.column_dimensions[chr(65 + i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'B2'
    wb.save(os.path.join(OUT, 'units.xlsx'))


def main():
    os.makedirs(OUT, exist_ok=True)
    us_pool = collect()
    stat, unused = match_us(us_pool)
    rows = []
    for key in order:
        u = units[key]
        rows.append(dict(id=u['id'], group=u['group'], kind=u['kind'], speaker=u['speaker'], label=u['label'],
                         en=u['en'], en_src=u['en_src'], en_jp=u['en_jp'] if u['en_jp'] != u['en'] else '',
                         ja=u['ja'], ja_alt=u['ja_alt'], ko='', locs=u['locs']))
    # 영어 없는 줄: 같은 파일 앞뒤 단위의 영어를 참고로 붙인다
    for i, r in enumerate(rows):
        if r['en_src'] == '영어 없음':
            f = r['locs'][0].split('#')[0]
            near = [x for x in rows[max(0, i - 3):i + 4] if x is not r and x['locs'][0].split('#')[0] == f and x['en']]
            r['en_near'] = ' / '.join(x['en'] for x in near[:4])
    # 같은 id 가 여러 개(같은 라벨, 다른 일본어)면 번호를 붙인다
    cnt = defaultdict(int)
    for r in rows:
        cnt[r['id']] += 1
    seen = defaultdict(int)
    for r in rows:
        if cnt[r['id']] > 1:
            seen[r['id']] += 1; r['id'] += '#%d' % seen[r['id']]
    json.dump(rows, open(os.path.join(OUT, 'units.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    write_xlsx(rows)
    rep = ['번역 단위 %d개 (위치 %d곳)' % (len(rows), sum(len(r['locs']) for r in rows))]
    by = defaultdict(lambda: [0, 0])
    for r in rows:
        by[r['group'], r['kind']][0] += 1; by[r['group'], r['kind']][1] += len(r['en'])
    for k in sorted(by):
        rep.append('  %s/%s: %d개, 영어 %d자' % (k[0], k[1], by[k][0], by[k][1]))
    rep.append('영어 원문 출처: ' + ', '.join('%s %d' % kv for kv in sorted(stat.items())))
    rep.append('북미판에만 있고 일본판에 자리가 없는 영어 레코드: %d' % unused)
    rep.append('영어 원문 합계(중복 제외 단위 기준): %d자' % sum(len(r['en']) for r in rows))
    open(os.path.join(OUT, 'report.txt'), 'w', encoding='utf-8').write('\n'.join(rep) + '\n')
    print('\n'.join(rep))


if __name__ == '__main__':
    main()
