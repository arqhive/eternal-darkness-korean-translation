"""작업 묶음을 번역하기 좋게 출력: python show_chunk.py <번호>"""
import glob
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
d = os.path.join(ROOT, 'work', 'text', 'chunks')
n = int(sys.argv[1])
p = [x for x in glob.glob(os.path.join(glob.escape(d), '%03d_*.json' % n))][0]
items = json.load(open(p, encoding='utf-8'))
print('#', os.path.basename(p), len(items), '단위')
for it in items:
    print('--', it['id'], '|', it['kind'], '|', it['spk'], ('| 같은 영어: ' + it['same_en_as']) if it.get('same_en_as') else '')
    print('  EN:', (it['en'] or '(없음)').replace('\n', ' ⏎ '))
    print('  JA:', it['ja'].replace('\n', ' ⏎ '))
    for a in (it.get('ja_alt', []) if not it['id'].startswith('boot:') else []):  # 시스템 묶음 변형판은 폰트 배치가 달라 깨져 보임
        print('  JA*:', a.replace('\n', ' ⏎ '))
    if it.get('near'):
        print('  근처 EN:', it['near'].replace('\n', ' ⏎ '))
