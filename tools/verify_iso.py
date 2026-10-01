"""빌드 ISO 검증: 교체 파일 = 교체 폴더 내용, 나머지 파일 = 원본과 같음, DOL 일치.
사용: python verify_iso.py <원본.iso> <빌드.iso> <교체폴더>"""
import hashlib
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_iso import read_fst


def main(src, dst, rep):
    fs, fd = open(src, 'rb'), open(dst, 'rb')
    dol_s, _, _, es = read_fst(fs); dol_d, _, _, ed = read_fst(fd)
    es = {p: (a, b) for i, p, a, b in es}; ed = {p: (a, b) for i, p, a, b in ed}
    assert es.keys() == ed.keys()
    changed = same = bad = 0
    for p, (a, b) in ed.items():
        fd.seek(a); got = fd.read(b)
        rp = os.path.join(rep, p)
        if os.path.isfile(rp):
            ok = got == open(rp, 'rb').read(); changed += 1
        else:
            fs.seek(es[p][0]); ok = got == fs.read(es[p][1]); same += 1
        if not ok:
            bad += 1; print('불일치', p)
    dol = open(os.path.join(rep, 'main.dol'), 'rb').read()
    fd.seek(dol_d); dol_ok = fd.read(len(dol)) == dol
    print(f'교체 {changed}개, 원본 그대로 {same}개, 불일치 {bad}개, DOL 일치 {dol_ok}')


if __name__ == '__main__':
    main(*sys.argv[1:4])
