"""그림 교체 체크 목록 자료: 일본판 전용 그림마다 (일본판 | 일본판 디스크 영어판 | 북미판) 후보를 붙여 JSON 으로.

결과: work/gfx/review/items.json (그림은 JPEG data URI, 가로 최대 320px)
"""
import base64
import collections
import io
import json
import os
import sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gfx_compare as G

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'work', 'gfx', 'review')

# 일본어판 파일 → 같은 디스크의 영어판 파일
EVAR = {
    'jp/JBkPkJJS.bin': 'jp/JBkPkEES.bin', 'jp/JBkPkJES.bin': 'jp/JBkPkEES.bin',
    'jp/JBookInJ.tpl': 'jp/JBookInE.tpl', 'jp/JWideInJ.tpl': 'jp/JWideInE.tpl', 'jp/JWideInv.tpl': 'jp/JWideInW.tpl',
    'dec/jp/JMnMenu.cmp': 'dec/jp/JMnMenuW.cmp', 'dec/jp/JInsane.cmp': 'dec/jp/JInsaneW.cmp',
    'jp/JBkAutoJ.tpl': 'jp/JBkAutoE.tpl', 'jp/JloadJ.tpl': 'jp/JloadE.tpl',
}
# 일본어판 파일 → 북미판 대응 파일(정렬용, 묶음이 같은 구조인 것만)
USMAP = {
    'jp/JBkPkJJS.bin': 'us/EBookPak.bin', 'jp/JBkPkJES.bin': 'us/EBookPak.bin', 'jp/JBkPkEES.bin': 'us/EBookPak.bin',
    'jp/JBookInJ.tpl': 'us/EBookInv.tpl', 'jp/JBookInE.tpl': 'us/EBookInv.tpl', 'jp/JWideInJ.tpl': 'us/EWideInv.tpl',
    'jp/JWideInE.tpl': 'us/EWideInv.tpl', 'jp/JWideInv.tpl': 'us/EWideInv.tpl', 'jp/JWideInW.tpl': 'us/EWideInv.tpl',
    'dec/jp/JMnMenu.cmp': 'dec/us/EMnMenu.cmp', 'dec/jp/JMnMenuW.cmp': 'dec/us/EMnMenu.cmp', 'dec/jp/JInsane.cmp': 'dec/us/EInsane.cmp',
    'dec/jp/JInsaneW.cmp': 'dec/us/EInsane.cmp', 'jp/JBkAutoJ.tpl': 'us/EBookAut.tpl', 'jp/JBkAutoE.tpl': 'us/EBookAut.tpl',
    'jp/JloadJ.tpl': 'us/Eloading.tpl', 'jp/JloadE.tpl': 'us/Eloading.tpl',
}
# 묶음별 설명(4단계 육안 검토)
GROUP = [
    ('JInsane', '타이틀·엔딩 화면'), ('JMnMenuW', '메뉴(영어판 묶음 자체)'), ('JMnMenu', '타이틀 메뉴·옵션'),
    ('JBkPkEES', '책 화면(영어판 묶음 자체)'), ('JBkPk', '책 화면·옵션'), ('JBookInE', '인벤토리 버튼(영어판 자체)'),
    ('JWideInE', '인벤토리 버튼(영어판 자체)'), ('JWideInW', '인벤토리 버튼(영어판 자체)'),
    ('JBookIn', '인벤토리 버튼'), ('JWideIn', '인벤토리 버튼(와이드)'), ('JBkAutoE', '부검 그림(영어판 자체)'),
    ('JBkAuto', '부검 그림'), ('JBootPkW', '컨트롤러 안내'), ('JBtPak', '컨트롤러 안내'), ('Fonts', '폰트'), ('fonts', '폰트'),
    ('J_Level', '레벨 텍스처'), ('cin', '컷신 텍스처'), ('credits', '크레딧 로고'), ('JPoe', '닌텐도 로고'),
    ('Jload', '로딩 로고'), ('pa_tex', '이펙트'), ('J_Tony', '기타 텍스처'),
]


def group_of(f):
    for k, v in GROUP:
        if k in f:
            return v
    return '기타'


def thumb(im, maxw=320, maxh=240):
    if im is None:
        return None
    t = im.copy(); t.thumbnail((maxw, maxh))
    bg = Image.new('RGBA', t.size, (72, 70, 80, 255)); bg.alpha_composite(t)
    b = io.BytesIO(); bg.convert('RGB').save(b, 'JPEG', quality=82)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()


def order_key(r):
    return (int(r[2]), int(r[3]))


def align(A, B):
    """두 파일의 그림 열(TPL 오프셋·번호 순)을 순서 보존 정렬. 기준점 = 데이터가 똑같은 그림(md5 같음).
    점수: md5 같음 +10, 크기·형식 같음 +3, 크기 다름 -2, 건너뛰기 -1. 반환 {A의 행 인덱스: B 행}"""
    A = sorted(A, key=order_key); B = sorted(B, key=order_key)
    n, m = len(A), len(B)
    sc = lambda a, b: 10 if a[7] == b[7] else (3 if (a[4], a[5], a[6]) == (b[4], b[5], b[6]) else -2)
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]; bk = [[None] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = -i; bk[i][0] = 'u'
    for j in range(1, m + 1):
        dp[0][j] = -j; bk[0][j] = 'l'
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            c = [(dp[i - 1][j - 1] + sc(A[i - 1], B[j - 1]), 'd'), (dp[i - 1][j] - 1, 'u'), (dp[i][j - 1] - 1, 'l')]
            dp[i][j], bk[i][j] = max(c)
    i, j, out = n, m, {}
    while i > 0 and j > 0:
        if bk[i][j] == 'd':
            out[tuple(A[i - 1][:4])] = B[j - 1]; i -= 1; j -= 1
        elif bk[i][j] == 'u':
            i -= 1
        else:
            j -= 1
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(G.OUT, 'index.tsv'), encoding='utf-8')]
    us_md5 = set(r[7] for r in rows if r[0] == 'us')
    by_file = collections.defaultdict(list)
    for r in rows:
        by_file[r[1]].append(r)
    pairs = [l.rstrip('\n').split('\t') for l in open(os.path.join(G.OUT, 'pairs.tsv'), encoding='utf-8')]
    items = []; aligned = {}
    for p in pairs:
        n, f, off, k, wh, uf, uoff, uk, usc = p
        w, h = wh.split('x')
        jimg = G.load_img(f, int(off), int(k))
        it = dict(id='g%03d' % int(n), group=group_of(f), file=f.split('/', 1)[1], slot='%s[%s]' % (off, k), size=wh,
                  jp=thumb(jimg))
        key = ('jp', f, off, k)
        for tag, tf in (('e', EVAR.get(f)), ('u', USMAP.get(f, uf))):
            if not tf:
                continue
            if (f, tf) not in aligned:
                aligned[f, tf] = align(by_file[f], by_file[tf])
            x = aligned[f, tf].get(key)
            if x is None and tag == 'e':  # 같은 디스크 영어판은 칸 순서가 같아 같은 칸 번호로 보완(북미판은 칸 구성이 달라 안 함)
                same = [r for r in by_file[tf] if r[2] == off and r[3] == k]
                x = same[0] if same else None
            if x is None:
                continue
            im = G.load_img(x[1], int(x[2]), int(x[3]))
            it[tag] = dict(src=x[1].split('/', 1)[1], slot='%s[%s]' % (x[2], x[3]), size='%sx%s' % (x[4], x[5]),
                           same_size=(x[4], x[5]) == (w, h), img=thumb(im))
        items.append(it)
    json.dump(items, open(os.path.join(OUT, 'items.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('항목', len(items), '크기 %.1fMB' % (os.path.getsize(os.path.join(OUT, 'items.json')) / 1e6),
          collections.Counter(i['group'] for i in items))


if __name__ == '__main__':
    main()
