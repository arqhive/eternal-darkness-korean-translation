"""컷신 자막 두 벌 작업(10/20 사용자 결정): 일본판 디스크 컷신의 영어 자막 목록(북미판과 같은 줄 나눔)을 뽑는다.

자막 옵션 「영어」를 고르면 이 목록이 나오고(10/20 실기 확인: 한글도 정상 표시, 다른 메뉴는 안 바뀜),
「일본어」(그림 글씨는 한국어 → 일본어로 바꿀 예정)를 고르면 일본어 목록이 나온다. 두 목록을 따로 번역한다.
결과 work/text/ensub/units.json: [{id: 'ensub:<라벨>', en, scenes, locs, order, ja_slot(같은 라벨 일본어), ko_draft(같은 라벨 기존 한글)}]
같은 라벨에 영어가 다르면 id 뒤에 #2 … 를 붙인다.
python tools/extract_ensub.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import txtpak  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, 'tools', 'extract_text.py'), encoding='utf-8').read()
ns = {'__name__': 'x', '__file__': os.path.join(ROOT, 'tools', 'extract_text.py')}
exec(compile(src[:src.index('# ---------- 단위 수집 ----------')], 'extract_text', 'exec'), ns)
norm = lambda s: re.sub(r'\s+', ' ', s or '').strip()


def main():
    DJP = os.path.join(ROOT, 'extract', 'dec', 'jp')
    ko = {}
    for f in sorted(os.listdir(os.path.join(ROOT, 'work', 'text', 'ko'))):
        if f.endswith('.json'):
            ko.update(json.load(open(os.path.join(ROOT, 'work', 'text', 'ko', f), encoding='utf-8')))
    units = {}; order = []
    for root, _, fs in sorted(os.walk(DJP)):
        for f in sorted(fs):
            if not (f.startswith('cin') and f.endswith('.bin')):
                continue
            p = os.path.join(root, f); rel = os.path.relpath(p, DJP).replace(os.sep, '/')
            d = open(p, 'rb').read()
            try:
                parts = txtpak.cin_parts(d)
            except Exception:
                continue
            ja = {}
            ens = []
            for i in range(1, len(parts)):
                if not parts[i][1]:
                    continue
                for ti, k, lab, txt in ns['recs_tabs'](txtpak.cin_text(d, i), True):
                    if ns['is_ja'](txt):
                        ja.setdefault(lab, ns['jdec'](txt))
                    else:
                        ens.append((i, ti, k, lab, norm(ns['wide_ascii'](txt))))
            for n, (i, ti, k, lab, en) in enumerate(ens):
                uid = 'ensub:' + lab; m = 2
                while uid in units and units[uid]['en'] != en:
                    uid = 'ensub:%s#%d' % (lab, m); m += 1
                if uid not in units:
                    units[uid] = dict(id=uid, label=lab, en=en, ja_slot=ja.get(lab), ko_draft=ko.get('cin:' + lab), scenes=[], locs=[])
                    order.append(uid)
                u = units[uid]
                scene = f[:-4]
                if scene not in u['scenes']:
                    u['scenes'].append(scene)
                u['locs'].append('%s#%d.%d.%d' % (rel, i, ti, k))
    out = os.path.join(ROOT, 'work', 'text', 'ensub'); os.makedirs(out, exist_ok=True)
    json.dump([units[u] for u in order], open(os.path.join(out, 'units.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('영어 자막 단위', len(order), '/ 자리', sum(len(u['locs']) for u in units.values()))


if __name__ == '__main__':
    main()
