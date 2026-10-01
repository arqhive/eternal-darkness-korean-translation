"""폴더 아래 텍스트 레코드를 전수 집계해 work/count_<이름>.tsv 로 남긴다.
사용: python count_text.py <폴더> <jp|us> <이름>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edtext

root, v, name = sys.argv[1:4]
rows = []
for r, ds, fs in os.walk(root):
    for f in sorted(fs):
        p = os.path.join(r, f)
        with open(p, 'rb') as fp:
            d = fp.read()
        if d[:8] == b'*SK_ASC*' or edtext.TMAGIC not in d:
            continue
        jp = v == 'jp' and not os.path.basename(p).startswith('JRW')
        for st, idx, head, label, t in edtext.scan(p, jp):
            rows.append((os.path.relpath(p, root), st, idx, label, t.hex()))
with open(f'work/count_{name}.tsv', 'w', encoding='utf-8') as fo:
    for x in rows:
        fo.write('\t'.join(map(str, x)) + '\n')
print(name, len(rows))
