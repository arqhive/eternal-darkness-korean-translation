"""글리프 대응표 한자 오인식 바로잡기: 문맥(잘못 읽힌 말 → 바른 말)으로 해당 글리프 번호를 찾아 work/glyph_fix.tsv 에 고정.

glyphmap.tsv 를 다시 만들어도 이 파일이 덮어쓴다(extract_text.py 가 읽음).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

# (잘못 읽힌 말, 바른 말) — 두 말의 길이가 같고, 다른 글자 자리의 글리프를 바른 글자로 고정
PAIRS = [
    ('永速', '永遠'), ('秘定', '秘宝'), ('工階', '二階'), ('犬きな', '大きな'), ('犬聖堂', '大聖堂'), ('貫って', '言って'),
    ('人問', '人間'), ('礁も', '誰も'), ('礁が', '誰が'), ('の車', 'の章'), ('對印', '封印'), ('對簡', '封筒'), ('遣産', '遺産'),
    ('問連', '間違'), ('場連い', '場違い'), ('肖像雨', '肖像画'), ('晴く', '暗く'), ('晴い', '暗い'), ('確詔', '確認'),
    ('勳い', '動い'), ('独持', '独特'), ('持っ雰', '持つ雰'), ('汚樂', '汚染'), ('昔', '昔'), ('敢府', '政府'), ('小鋭', '小説'),
    ('鋭明', '説明'), ('犠柱', '犠牲'), ('唇護婦', '看護婦'), ('定石', '宝石'), ('奸奇心', '好奇心'), ('疑感', '疑惑'),
    ('迷感', '迷惑'), ('惨剌', '惨劇'), ('橾っ', '操っ'), ('字宙', '宇宙'), ('迫り釆る', '迫り来る'), ('釆ました', '来ました'),
    ('砂漢', '砂漠'), ('拘朿', '拘束'), ('終績', '終結'), ('週り', '通り'), ('相餤', '相談'), ('聒', '話'), ('胎勳', '胎動'),
    ('囚行', '凶行'), ('股定', '設定'), ('俾', '碑'), ('往', '柱'),
]


def main():
    gm = {int(l.split('\t')[0], 16): l.split('\t')[1] for l in open(os.path.join(ROOT, 'work', 'glyphmap.tsv'), encoding='utf-8')}
    texts = []
    for line in open(os.path.join(ROOT, 'work', 'count_dec_jp.tsv'), encoding='utf-8'):
        t = bytes.fromhex(line.rstrip('\n').split('\t')[4])
        if any(t[0::2]):
            texts.append(measure.codes_of(t))
    for line in open(os.path.join(ROOT, 'work', 'count_raw_jp.tsv'), encoding='utf-8'):
        t = bytes.fromhex(line.rstrip('\n').split('\t')[4])
        if any(t[0::2]):
            texts.append(measure.codes_of(t))
    fix = {}
    for wrong, right in PAIRS:
        if len(wrong) != len(right) or wrong == right:
            continue
        found = False
        for cs in texts:
            s = ''.join(chr(c) if c < 0x80 else gm.get(c, '□') for c in cs)
            i = s.find(wrong)
            if i < 0:
                continue
            for k, (a, b) in enumerate(zip(wrong, right)):
                if a != b:
                    fix[cs[i + k]] = b
            found = True
            break
        if not found:
            print('문맥 못 찾음:', wrong)
    fix[0x100] = '　'  # 1번 장 첫 칸 = 전각 공백(그림으로 빈칸 확인)
    with open(os.path.join(ROOT, 'work', 'glyph_fix.tsv'), 'w', encoding='utf-8') as fo:
        for c, ch in sorted(fix.items()):
            fo.write('%04X\t%s\t(이전 %s)\n' % (c, ch, gm.get(c)))
    print('고정', len(fix))


if __name__ == '__main__':
    main()
