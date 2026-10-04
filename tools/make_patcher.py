"""배포용 파일 단위 패처 생성기 (게임큐브, disc-file-patcher 스킬의 이터널 다크니스판).

원본 일본판 ISO와 한글 빌드 ISO(build_iso.py --pack 결과)를 FST 기준으로 비교해, 바뀐 파일과 DOL마다 xdelta 차분을 만든다.
이 게임은 압축(SK_ASC)을 푼 파일을 넣어 파일이 커지므로, 빌드가 바뀌는 파일 자리를 모두 비운 뒤 큰 파일부터 빈자리에 다시 놓는다.
그 새 위치를 manifest 에 그대로 적어 두고, 사용자용 patch.ps1 은
  원본 복사 → DOL 제자리 덮어쓰기 → 바뀐 파일을 적힌 위치에 쓰기 → FST 항목(위치·크기) 고치기
만 한다. 정본 ISO에 적용하면 빌드와 바이트까지 같은 ISO가 나온다.

사용:
  python tools/make_patcher.py --orig "Eternal Darkness - Manekareta 13-nin (Japan).iso" --build build/ED_KR_v0.1.iso \\
      --out release/EternalDarkness-KO-v0.1 --version 0.1 --wit <wit 폴더> --xdelta <xdelta3.exe> --readme patcher/README.txt
"""
import argparse
import hashlib
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_iso import read_fst, DISC_SIZE  # noqa: E402

WIT_FILES = ('bin/wit.exe', 'bin/cygwin1.dll', 'bin/cygz.dll', 'bin/cygcrypto-1.1.dll', 'bin/cygncursesw-10.dll')


def md5(b):
    return hashlib.md5(b).hexdigest()


def read_at(path, off, size):
    with open(path, 'rb') as f:
        f.seek(off)
        return f.read(size)


def dol_size(head):
    offs = struct.unpack('>18I', head[0:0x48]); sizes = struct.unpack('>18I', head[0x90:0xD8])
    return max(o + s for o, s in zip(offs, sizes))


def disc(path):
    with open(path, 'rb') as f:
        dol, fst_off, fst, ents = read_fst(f)
    hdr = read_at(path, 0, 0x440)
    return dict(hdr=hdr, gid=hdr[:6].decode('ascii'), dol=dol, fst_off=fst_off, fst=bytes(fst),
                dol_bytes=read_at(path, dol, dol_size(read_at(path, dol, 0x100))),
                by_path={p: (o, s) for i, p, o, s in ents})


def main():
    ap = argparse.ArgumentParser()
    for k in ('orig', 'build', 'out', 'version', 'wit', 'xdelta'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--title', default='이터널 다크니스')
    ap.add_argument('--result', default='Eternal Darkness (Korean)')
    ap.add_argument('--readme')
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    o, b = disc(a.orig), disc(a.build)
    out = Path(a.out)
    xdelta = str(Path(a.xdelta).resolve())   # 상대경로 그대로면 Windows에서 실행 파일을 못 찾음

    assert os.path.getsize(a.orig) == DISC_SIZE and os.path.getsize(a.build) == DISC_SIZE
    assert o['hdr'] == b['hdr'], '헤더가 다름(이 패처는 헤더를 바꾸지 않음)'
    assert o['dol'] == b['dol'] and len(o['dol_bytes']) == len(b['dol_bytes']), 'DOL 위치·크기가 다름'
    assert o['fst_off'] == b['fst_off'] and len(o['fst']) == len(b['fst']), 'FST 위치·크기가 다름'
    assert set(o['by_path']) == set(b['by_path']), '파일 목록이 다름(추가·삭제 파일은 지원 안 함)'
    changed = []
    for p, (oo, os_) in o['by_path'].items():
        bo, bs = b['by_path'][p]
        if (oo, os_) != (bo, bs) or read_at(a.orig, oo, os_) != read_at(a.build, bo, bs):
            changed.append(p)
    # 바뀌지 않은 파일은 원래 자리 그대로여야 함
    for p, v in o['by_path'].items():
        if p not in changed:
            assert v == b['by_path'][p], p
    # FST: 바뀐 파일 항목의 위치·크기만 다름
    fst = bytearray(o['fst'])
    n = struct.unpack('>I', fst[8:12])[0]
    st = n * 12

    def name(no):
        e = st + no
        while fst[e]:
            e += 1
        return fst[st + no:e].decode('shift_jis')

    paths = {}

    def walk(i, stop, pre):
        while i < stop:
            no = struct.unpack('>I', fst[i * 12:i * 12 + 4])[0] & 0xFFFFFF
            nxt = struct.unpack('>I', fst[i * 12 + 8:i * 12 + 12])[0]
            if fst[i * 12]:
                walk(i + 1, nxt, pre + name(no) + '/'); i = nxt
            else:
                paths[pre + name(no)] = i; i += 1
    walk(1, n, '')
    for p in changed:
        struct.pack_into('>II', fst, paths[p] * 12 + 4, *b['by_path'][p])
    assert bytes(fst) == b['fst'], 'FST 차이가 바뀐 파일 위치·크기 말고도 있음'

    if out.exists():
        shutil.rmtree(out)
    (out / 'data').mkdir(parents=True)
    tmp = Path(tempfile.mkdtemp())
    lines = []
    items = [('dol', 'main.dol', o['dol_bytes'], b['dol_bytes'], o['dol'])]
    items += [('raw', p, read_at(a.orig, *o['by_path'][p]), read_at(a.build, *b['by_path'][p]), b['by_path'][p][0])
              for p in sorted(changed, key=lambda q: b['by_path'][q][0])]
    for i, (mode, p, A, B, pos) in enumerate(items):
        (tmp / 'a').write_bytes(A); (tmp / 'b').write_bytes(B)
        patch = f'{i:03d}.xdelta'
        # -A= : 헤더에 파일 경로(PC 사용자 이름 포함)를 적지 않음
        subprocess.run([xdelta, '-e', '-f', '-9', '-S', 'djw', '-A=', '-s', str(tmp / 'a'), str(tmp / 'b'),
                        str(out / 'data' / patch)], check=True)
        lines.append('\t'.join((mode, patch, p, md5(A), md5(B), str(pos))))
    shutil.rmtree(tmp)
    (out / 'data' / 'manifest.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    h = hashlib.md5()
    with open(a.build, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 24), b''):
            h.update(chunk)
    (out / 'data' / 'config.txt').write_text(
        f'id={o["gid"]}\nrev={o["hdr"][7]}\ntitle={a.title}\nversion={a.version}\nresult={a.result}\n'
        f'disc_size={DISC_SIZE}\nfst_md5={md5(o["fst"])}\nresult_md5={h.hexdigest()}\n', encoding='utf-8')

    tpl = HERE.parent / 'patcher'
    shutil.copy2(tpl / 'patch.ps1', out / 'patch.ps1')
    shutil.copy2(tpl / '패치하기.bat', out / '패치하기.bat')
    if a.readme:
        shutil.copy2(a.readme, out / 'README.txt')
    (out / 'bin').mkdir()
    for f in WIT_FILES:
        shutil.copy2(Path(a.wit) / f, out / 'bin' / Path(f).name)
    shutil.copy2(Path(a.wit) / 'bin' / 'wit-gpl-2.0.txt', out / 'bin' / 'wit-gpl-2.0.txt')
    shutil.copy2(xdelta, out / 'bin' / 'xdelta3.exe')

    zpath = out.parent / (out.name + '.zip')   # with_suffix 는 'v0.1' 의 '.1' 을 확장자로 봄
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for dp, _, fs in os.walk(out):
            for f in sorted(fs):
                q = Path(dp) / f
                z.write(q, Path(out.name) / q.relative_to(out))
    size = sum(f.stat().st_size for f in (out / 'data').iterdir())
    print(f'DOL + 파일 {len(changed)}개, 차분 합계 {size / 1e6:.2f} MB, zip {zpath.stat().st_size / 1e6:.2f} MB')
    print(f'패처: {out}')


if __name__ == '__main__':
    main()
