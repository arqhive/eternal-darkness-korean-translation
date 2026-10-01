"""같은 영어·같은 일본어(높임이 같은) 단위를 이미 번역한 문장으로 채운다.
사용: python fill_same.py <묶음 번호…>  → 해당 묶음의 ko 파일(work/text/ko/NNN_이름.json)에 합쳐 쓰고, 남은 단위 수를 알린다."""
import glob
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
TXT = os.path.join(ROOT, 'work', 'text')


def load_ko():
    ko = {}
    for p in glob.glob(os.path.join(glob.escape(os.path.join(TXT, 'ko')), '*.json')):
        ko.update(json.load(open(p, encoding='utf-8')))
    return ko


def main(nums):
    units = {u['id']: u for u in json.load(open(os.path.join(TXT, 'units.json'), encoding='utf-8'))}
    for n in nums:
        cp = glob.glob(os.path.join(glob.escape(os.path.join(TXT, 'chunks')), '%03d_*.json' % n))[0]
        items = json.load(open(cp, encoding='utf-8'))
        kp = os.path.join(TXT, 'ko', os.path.basename(cp))
        mine = json.load(open(kp, encoding='utf-8')) if os.path.exists(kp) else {}
        ko = load_ko(); ko.update(mine)
        filled = 0; left = []
        for it in items:
            if it['id'] in ko:
                continue
            # 같은 영어+같은 일본어인 번역이 이미 있으면 채움
            src = [k for k, v in ko.items() if k in units and units[k]['en'] == it['en'] and it['en']
                   and units[k]['ja'] == it['ja'] and units[k]['kind'] == it['kind']]
            if src:
                mine[it['id']] = ko[src[0]]; filled += 1
            else:
                left.append(it['id'])
        json.dump(mine, open(kp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(os.path.basename(cp), '자동 채움', filled, '남음', len(left))
        for x in left:
            print('  남음:', x)


if __name__ == '__main__':
    main([int(x) for x in sys.argv[1:]])
