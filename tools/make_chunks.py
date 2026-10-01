"""번역 단위를 장면 순서 작업 묶음으로 나눈다 → work/text/chunks/NNN_이름.json

순서: 컷신(Act 순) → 실시간·음성 자막(시스템 9·12번 블록) → 방 문구(레벨 순) → NPC(8번) → 아이템(4번)
      → 책 화면 문구(3번) → 버튼(6번) → 시스템 기타 → 책(부검 기록) → 메모리 카드.
이미 번역된 단위(work/text/ko/*.json 에 있는 id)는 뺀다. 한 묶음 최대 60단위.
"""
import glob
import json
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
TXT = os.path.join(ROOT, 'work', 'text')
MAXN = 60


def act_key(label):
    m = re.match(r'Act(\d+)([a-z]?)', label)
    if m:
        return (0, int(m.group(1)), m.group(2))
    return (1, 0, label)


def loc_key(loc):
    f, _, pos = loc.partition('#')
    return (f, [int(x) if x.isdigit() else x for x in re.split(r'[.]', pos)])


def main():
    rows = json.load(open(os.path.join(TXT, 'units.json'), encoding='utf-8'))
    done = set()
    for p in glob.glob(os.path.join(glob.escape(os.path.join(TXT, 'ko')), '*.json')):
        done |= set(json.load(open(p, encoding='utf-8')))
    groups = {}
    for r in rows:
        loc = r['locs'][0]; f = loc.split('#')[0]
        blk = loc.split('#')[1].split('.')[0] if r['group'] in ('boot', 'book') else ''
        if r['group'] == 'cin':
            a = act_key(r['label'])
            key = '0|%d|%03d|%s|%s' % (a[0], a[1], a[2], f.split('/')[-1])
            name = r['label'].split('/')[0]
        elif r['group'] == 'boot' and blk in ('9', '12'):
            key = '1|%02d|%s' % (int(blk), r['label'].split('/')[0])
            name = 'sub_' + r['label'].split('/')[0]
        elif r['group'] == 'room':
            lv = f.split('/')[0]
            key = '2|%03d' % (int(lv.replace('Level', '')) + 1)
            name = 'room_' + lv
        elif r['group'] == 'boot':
            order = {'8': 3, '4': 4, '3': 5, '6': 6}.get(blk, 7)
            key = '%d|%s' % (order, r['label'].split('/')[0])
            name = 'sys%s_%s' % (blk, r['label'].split('/')[0])
        elif r['group'] == 'book':
            key = '8|%s' % r['label'].split('/')[0]
            name = 'book_' + r['label'].split('/')[0]
        else:
            key = '9|'
            name = 'memcard'
        groups.setdefault(key, {'name': name, 'rows': []})['rows'].append(r)
    out = os.path.join(TXT, 'chunks')
    os.makedirs(out, exist_ok=True)
    for p in glob.glob(os.path.join(glob.escape(out), '*.json')):
        os.remove(p)
    n = 0; total = 0; seen_en = {}
    for key in sorted(groups):
        g = groups[key]
        rs = sorted(g['rows'], key=lambda r: loc_key(r['locs'][0]))
        items = []
        for i, r in enumerate(rs):
            it = dict(id=r['id'], kind=r['kind'], spk=r['speaker'], en=r['en'], ja=r['ja'])
            if r.get('ja_alt'):
                it['ja_alt'] = r['ja_alt']
            if r.get('en_near'):
                it['near'] = r['en_near']
            if r['group'] in ('cin', 'boot') and r['kind'] in ('subtitle', 'rt_sub', 'voice_sub'):
                if i > 0:
                    it['prev_en'] = rs[i - 1]['en']
                if i + 1 < len(rs):
                    it['next_en'] = rs[i + 1]['en']
            k = (r['kind'], r['en'])
            if r['en'] and k in seen_en:
                it['same_en_as'] = seen_en[k]
            elif r['en']:
                seen_en[k] = r['id']
            if r['id'] not in done:
                items.append(it)
        for s in range(0, len(items), MAXN):
            part = items[s:s + MAXN]
            if not part:
                continue
            n += 1; total += len(part)
            suffix = '' if len(items) <= MAXN else '_%d' % (s // MAXN + 1)
            fn = '%03d_%s%s.json' % (n, re.sub(r'[^A-Za-z0-9_]', '', g['name']), suffix)
            json.dump(part, open(os.path.join(out, fn), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('묶음', n, '단위', total, '(이미 번역 %d 제외)' % len(done))


if __name__ == '__main__':
    main()
