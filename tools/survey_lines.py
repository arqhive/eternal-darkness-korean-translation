"""일본판 디스크 텍스트 전부의 줄 수·줄 폭(px) 조사 → work/lines_jp.tsv

열: 분류, 파일, 블록, 표, 번호, 라벨, 언어(ja/en), 줄 수, 최대 줄 폭, 줄 폭 목록, 변수 포함
"""
import os
import struct
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpe
import edtext
import measure
import txtpak

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
EX = os.path.join(ROOT, 'extract', 'jp'); DEC = os.path.join(ROOT, 'extract', 'dec', 'jp')
WT = measure.width_table(os.path.join(EX, 'JBtPakJS.bin'))


def recs_from_tabs(tabs):
    for ti, t in enumerate(tabs):
        for k, it in enumerate(t):
            if isinstance(it, tuple):
                continue
            body, _ = bpe.decode(it, 4)
            yield ti, k, body, struct.unpack('>I', it[:4])[0]


def emit(rows, cat, f, blk, ti, k, head, body, ascii_text=False):
    label, txt = edtext.parse_body(head, body, not ascii_text)
    if txt is None:
        return
    if ascii_text:
        lang = 'en'
    else:
        lang = 'ja' if any(txt[0::2]) else 'en'
    ls = measure.lines_px(txt, WT, ascii_text)
    rows.append((cat, f, blk, ti, k, label, lang, len(ls), max(l[1] for l in ls),
                 ','.join('%.0f' % l[1] for l in ls), int(any(l[2] for l in ls))))


def main():
    rows = []
    # 방 문구
    for lv in sorted(os.listdir(os.path.join(DEC, 'Levels'))):
        for f in sorted(os.listdir(os.path.join(DEC, 'Levels', lv))):
            p = os.path.join(DEC, 'Levels', lv, f); rel = lv + '/' + f
            if f.startswith(('JRmTxt', 'JRWTxt')):
                for ti, k, body, head in recs_from_tabs(txtpak.parse(open(p, 'rb').read())):
                    emit(rows, 'room', rel, 0, ti, k, head, body, f.startswith('JRW'))
            elif f.startswith('cin') and f.endswith('.bin'):
                d = open(p, 'rb').read()
                try:
                    parts = txtpak.cin_parts(d)
                except Exception:
                    continue
                for i in range(1, len(parts)):
                    if parts[i][1]:
                        for ti, k, body, head in recs_from_tabs(txtpak.cin_text(d, i)):
                            emit(rows, 'cin', rel, i, ti, k, head, body)
    # 시스템·책 묶음(최상위 블록 중 문자열표 묶음)
    for f, cat in [('JBtPakJS.bin', 'boot'), ('JBkPkJJS.bin', 'book')]:
        d = open(os.path.join(EX, f), 'rb').read()
        n = struct.unpack('>I', d[:4])[0]
        for i in range(n):
            o, s = struct.unpack('>II', d[8 + 8 * i:16 + 8 * i])
            if not s:
                continue
            blk = d[o:o + s]
            try:
                tabs = txtpak.parse(struct.pack('>I', len(blk)) + blk)
            except Exception:
                continue
            for ti, k, body, head in recs_from_tabs(tabs):
                emit(rows, cat, f, i, ti, k, head, body)
    # 메모리 카드(문자열표 직접 검색)
    for f in ['JMemcardText.bin']:
        d = open(os.path.join(EX, f), 'rb').read()
        for st, ents in edtext.tables(d):
            for k, (o, l) in enumerate(ents):
                try:
                    head, body = edtext.record(d, st, o, l)
                except Exception:
                    continue
                emit(rows, 'memcard', f, st, 0, k, head, body)
    with open(os.path.join(ROOT, 'work', 'lines_jp.tsv'), 'w', encoding='utf-8') as fo:
        for r in rows:
            fo.write('\t'.join(map(str, r)) + '\n')
    print('레코드', len(rows))


if __name__ == '__main__':
    main()
