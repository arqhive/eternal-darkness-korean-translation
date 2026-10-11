"""오프닝 영상 fmv/fmv0001.avi(VP31 AVI, 512x272 30fps) 끝 로고 부제를 한글로 바꾼 영상 만들기(10/12).

일본판 DOL 은 VP3 영상만 재생한다. VP3 인코더가 따로 없어서 Xiph libtheora 의 VP3 호환 모드
(TH_ENCCTL_SET_VP3_COMPATIBLE: VP3.1 양자화·허프만 표, qi 하나)로 인코딩한 뒤 Theora 데이터 패킷 머리를 VP3 머리로 바꾼다.
  Theora: 키 [0][0][qi6][0][000]  인터 [0][1][qi6][0]
  VP3   : 키 [0][0][qp6][00000000][버전5=1][0][00]  인터 [1][0][qp6]
  나머지 비트는 같고, 원본처럼 4바이트 단위로 0을 채움.
2336번 키프레임부터 끝까지만 다시 인코딩하고 앞부분 칸은 원본 바이트 그대로, 빈 칸(앞 프레임 유지)도 그대로 둔다.
키프레임은 첫 칸 하나(프레임 최대 크기를 원본 최대 15,176바이트 아래로).

준비: tools/fmv/venc.exe — libtheora-1.1.1 + libogg-1.3.5 소스(downloads.xiph.org)로 빌드
  python -m ziglang cc -O2 -target x86_64-windows-gnu -I<theora>/include -I<ogg>/include -I<theora>/lib \\
      tools/fmv/venc.c <theora>/lib/*.c(encoder_disabled.c 제외) <ogg>/src/bitwise.c <ogg>/src/framing.c -o tools/fmv/venc.exe
  (ogg/config_types.h 는 stdint 형으로 직접 만듦). 영상 해독은 imageio-ffmpeg 의 ffmpeg.
사용: python tools/fmv_logo.py <출력.avi>   (build_full.py 가 build/full/fmv/fmv0001.avi 로 부름)
"""
import os
import struct
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fmv import avi, logo_ko  # noqa: E402

ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'extract', 'jp', 'fmv', 'fmv0001.avi')
VENC = os.path.join(HERE, 'fmv', 'venc.exe')
W, H, START = 512, 272, 2336
BITRATE = 1400000


class BW:
    def __init__(s): s.b = bytearray(); s.acc = 0; s.n = 0
    def put(s, v, n):
        for i in range(n - 1, -1, -1):
            s.acc = (s.acc << 1) | ((v >> i) & 1); s.n += 1
            if s.n == 8: s.b.append(s.acc); s.acc = 0; s.n = 0
    def bytes(s):
        if s.n: s.b.append(s.acc << (8 - s.n)); s.acc = 0; s.n = 0
        return bytes(s.b)


def theora_to_vp3(p):
    """반환 (VP3 프레임, 키프레임 여부). 빈 패킷(같은 프레임 반복)은 b''(게임도 빈 칸 = 앞 프레임 유지)."""
    if not p:
        return b'', False
    b = [(x >> i) & 1 for x in p for i in range(7, -1, -1)]
    assert b[0] == 0, '헤더 패킷'
    inter = b[1]; qi = int(''.join(map(str, b[2:8])), 2)
    assert b[8] == 0, 'qi 여러 개(VP3 불가)'
    w = BW()
    if not inter:
        assert b[9:12] == [0, 0, 0]; pos = 12
        w.put(0, 1); w.put(0, 1); w.put(qi, 6); w.put(0, 8); w.put(1, 5); w.put(0, 1); w.put(0, 2)
    else:
        pos = 9
        w.put(1, 1); w.put(0, 1); w.put(qi, 6)
    for x in b[pos:]:
        w.put(x, 1)
    out = w.bytes()
    return out + b'\0' * (-len(out) % 4), not inter


def decode_all(path):
    import imageio_ffmpeg
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-i', path,
                        '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'yuv420p', '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, W * H * 3 // 2)


def encode(frames):
    with tempfile.TemporaryDirectory() as td:
        yuv = os.path.join(td, 'in.yuv'); pk = os.path.join(td, 'out.pkt')
        frames.tofile(yuv)
        subprocess.run([VENC, yuv, pk, str(W), str(H), '48', '1000', str(BITRATE)], check=True, capture_output=True)
        d = open(pk, 'rb').read()
    out = []; o = 0
    while o < len(d):
        n = struct.unpack('>I', d[o:o + 4])[0]; out.append(d[o + 4:o + 4 + n]); o += 4 + n
    return out


def write_avi(d, a, frames, flags, dst):
    movi = bytearray(b'movi'); idx = bytearray()
    for (cid, data), fl in zip(frames, flags):
        off = len(movi)
        movi += cid + struct.pack('<I', len(data)) + data + (b'\0' if len(data) & 1 else b'')
        idx += struct.pack('<4sIII', cid, fl, off, len(data))
    io, isz = a['idx']
    body = a['head'] + b'LIST' + struct.pack('<I', len(movi)) + bytes(movi) + b'idx1' + struct.pack('<I', len(idx)) + bytes(idx) + d[io + 8 + isz:]
    open(dst, 'wb').write(b'RIFF' + struct.pack('<I', len(body) + 4) + b'AVI ' + body)


def build(dst):
    d = open(SRC, 'rb').read(); a = avi.parse(d)
    fr = a['frames']; flags = list(a['flags'])
    assert flags[START] & 0x10, '시작 칸은 키프레임이어야 함'
    slots = [i for i in range(START, len(fr)) if len(fr[i][1])]
    j = sum(1 for f in fr[:START] if len(f[1]))
    seg = decode_all(SRC)[j:j + len(slots)].copy()
    seg_ko = logo_ko.run(seg)[2]
    pk = encode(seg_ko)
    assert len(pk) == len(slots), (len(pk), len(slots))
    frames = [list(f) for f in fr]; mx = 0
    for k, (i, p) in enumerate(zip(slots, pk)):
        v, key = theora_to_vp3(p)
        assert key or k
        frames[i][1] = v; flags[i] = 0x10 if key else 0; mx = max(mx, len(v))
    assert mx <= max(len(f[1]) for f in fr), '원본 최대 프레임보다 큼'
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    write_avi(d, a, frames, flags, dst)
    print('영상 fmv0001: %d칸 다시 인코딩, 프레임 최대 %d바이트 → %s' % (len(slots), mx, dst))


if __name__ == '__main__':
    build(sys.argv[1])
