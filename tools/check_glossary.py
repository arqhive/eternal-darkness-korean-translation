"""7단계: 용어집 대조. 용어집 표(원문 | 한국어)를 읽어, 영어 원문에 그 용어가 있는데 번역에 정해진 한국어가 없는 줄을 찾는다.
일반어(사용·확인·저장 등 화면 낱말)는 문맥 따라 달라지므로 SKIP. 결과: work/review7/glossary.tsv
python check_glossary.py"""
import glob, json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {'Use', 'Equip', 'Mix', 'Check', 'Mode', 'Assign', 'Map', 'Magick', 'Journal', 'Options', 'Save', 'Load', 'Delete',
        'Yes', 'No', 'Health', 'Cast', 'Tome', 'Credits', 'empty', 'Standard', 'Volume', 'Keeper', 'Second Floor', 'Basement',
        'Alex', 'Max', 'Edward', 'Liche', 'Zombie', 'Horror', 'Rune', 'Spell', 'Shield', 'Bind', 'Recover', 'Staff', 'Mace',
        'Pistol', 'Rifle', 'Torch', 'Item', 'Self', 'Power', 'Creature', 'Project', 'Protect', 'Summon', 'Absorb', 'Dispel',
        'Cathedral', 'Persia', 'Khmer', 'Frank', 'Inquisition', 'Kali', 'Alignment', 'Eternal Darkness', 'Ancient', 'Guardian',
        'Saved Game', 'Game File', 'Subtitles', 'Widescreen', 'Mono', 'Stereo', 'Sabre', 'Revolver', 'Shotgun'}


def terms():
    out = []
    for line in open(os.path.join(ROOT, 'docs', 'glossary.md'), encoding='utf-8'):
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(c) < 2 or not re.match(r'[A-Za-z.]', c[0]) or c[0] in ('원문', '룬'):
            continue
        ens = [x.strip() for x in c[0].split('/')]
        kos = [x.strip() for x in c[1].split('/')]
        if len(ens) != len(kos):
            continue
        for e, k in zip(ens, kos):
            e = re.sub(r'\(.*?\)', '', e).strip()
            k = re.sub(r'\(.*?\)', '', k).strip()
            if not e or not k or '~' in e or '…' in e or e in SKIP or '확인' in k or '같음' in k:
                continue
            out.append((e, k))
    return out


def main():
    units = {u['id']: u for u in json.load(open(os.path.join(ROOT, 'work', 'text', 'units.json'), encoding='utf-8'))}
    ko = {}
    kd = os.path.join(ROOT, 'work', 'text', 'ko')   # 폴더 이름에 [GC]가 있어 glob 쓰면 아무것도 못 찾음
    for f in sorted(os.path.join(kd, x) for x in os.listdir(kd) if x.endswith('.json')):
        for k, v in json.load(open(f, encoding='utf-8')).items():
            ko[k] = (v, os.path.basename(f))
    TAG = re.compile(r'\\a[a-z]|\\i\d+|\\s\d*\.?\d*|~[a-z0-9]|\\n')
    rows, cnt = [], collections.Counter()
    for e, k in terms():
        pat = re.compile(r"(?<![A-Za-z'])" + re.escape(e).replace(r'\ ', r'\s+') + r"(?![A-Za-z])", re.I)
        kk = k.replace(' ', '')
        for id_, (v, f) in ko.items():
            en = units[id_]['en']
            if en and pat.search(en) and kk not in TAG.sub('', v).replace(' ', '').replace('\n', ''):
                rows.append((e, k, id_, f, en.replace('\n', ' ')[:120], v.replace('\n', ' ')[:120]))
                cnt[(e, k)] += 1
    os.makedirs(os.path.join(ROOT, 'work', 'review7'), exist_ok=True)
    with open(os.path.join(ROOT, 'work', 'review7', 'glossary.tsv'), 'w', encoding='utf-8') as fo:
        fo.write('용어\t정한 말\tid\t파일\t영어\t번역\n')
        for r in rows:
            fo.write('\t'.join(r) + '\n')
    for (e, k), n in cnt.most_common():
        print(n, e, '→', k)
    print('불일치 후보', len(rows), '줄 /', len(cnt), '용어')


if __name__ == '__main__':
    main()
