"""6단계: plan.tsv 의 그림(번역 대상)을 원래 크기로 뽑는다.
결과: work/gfx/src/<id>_jp.png (일본판), <id>_e.png (같은 디스크 영어판), <id>_u.png (북미판), 보기 좋게 위아래 바로 세움.
python gfx_src.py"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gfx_compare as G
import gfx_review as R

OUT = os.path.join(G.OUT, 'src')


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(G.OUT, 'index.tsv'), encoding='utf-8')]
    by_file = collections.defaultdict(list)
    for r in rows:
        by_file[r[1]].append(r)
    pairs = {'g%03d' % int(p[0]): p for p in (l.rstrip('\n').split('\t') for l in open(os.path.join(G.OUT, 'pairs.tsv'), encoding='utf-8'))}
    plan = [l.rstrip('\n').split('\t') for l in open(os.path.join(G.OUT, 'plan.tsv'), encoding='utf-8')][1:]
    aligned = {}
    for r in plan:
        gid = r[0]
        n, f, off, k, wh, uf, uoff, uk, usc = pairs[gid]
        G.load_img(f, int(off), int(k)).save(os.path.join(OUT, gid + '_jp.png'))
        key = ('jp', f, off, k)
        for tag, tf in (('e', R.EVAR.get(f)), ('u', R.USMAP.get(f, uf))):
            if not tf:
                continue
            if (f, tf) not in aligned:
                aligned[f, tf] = R.align(by_file[f], by_file[tf])
            x = aligned[f, tf].get(key)
            if x is None and tag == 'e':
                same = [q for q in by_file[tf] if q[2] == off and q[3] == k]
                x = same[0] if same else None
            if x is None:
                continue
            im = G.load_img(x[1], int(x[2]), int(x[3]))
            if im is not None:
                im.save(os.path.join(OUT, '%s_%s.png' % (gid, tag)))
    print(len(plan), '장 →', OUT)


if __name__ == '__main__':
    main()
