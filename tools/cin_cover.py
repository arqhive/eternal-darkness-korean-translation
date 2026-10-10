"""프롤로그 장면 Levels/Level16/cin0069 의 책 표지(일본어 로고) → 북미판 표지(Sanity's Requiem). 10/11 사용자 확인.

장면 파일(SK_ASC 해제본) 구조: [0]=길이-4, [0x38]=레코드 수, [0x40]=데이터 시작, [0x48+4k]=표(k>=1: 레코드 k-1 의 압축 크기),
레코드 = 04030201 + Gage BPE 블록(최대 5000바이트), 32바이트 단위 0 채움.
1877번 레코드 안 0x7E0 에 640x480 CMPR TPL(표지). 그림만 북미판 것으로 바꾸고, 0x450 의 2바이트(텍스처 번호로 추정)는
일본판 값을 둔다 — 레코드를 통째로 북미판 것으로 바꾸면 표지가 아예 안 나왔음(시험판 2).
장면 파일 통째 교체는 자막이 사라짐(북미판은 자막 연결이 다름, 시험판 1).

사용: python cin_cover.py <출력 경로>   /  모듈: build(out_path)
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpe

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEC = os.path.join(ROOT, 'extract', 'dec', 'jp')
USDEC = os.path.join(ROOT, 'extract', 'dec', 'us')
K = 1877
MAGIC = b'\x04\x03\x02\x01'


def recs(d):
    """레코드 머리 위치 목록."""
    pos = 0x2584; st = []
    while pos < len(d) - 8:
        while pos < len(d) and d[pos] == 0:
            pos += 1
        if d[pos:pos + 4] == MAGIC:
            st.append(pos); pos += 4
        o, pos = bpe.decode(d, pos)
    return st


def blocks(d, s, e):
    pos = s + 4; out = []
    while pos < e:
        while pos < e and d[pos] == 0:
            pos += 1
        if pos >= e:
            break
        st = pos
        o, pos = bpe.decode(d, pos); out.append((st, pos, o))
    return out


def height(blk):
    """BPE 블록 쌍 표의 펼침 깊이(게임 해제기 스택 사용량)."""
    left = list(range(256)); right = [0] * 256; code = 0; pos = 0
    while True:
        c = blk[pos]; pos += 1
        if c > 127:
            code += c - 127; c = 0
        if code == 256:
            break
        for _ in range(c + 1):
            left[code] = blk[pos]; pos += 1
            if code != left[code]:
                right[code] = blk[pos]; pos += 1
            code += 1
        if code == 256:
            break
    memo = {}

    def h(x):
        if left[x] == x:
            return 0
        if x not in memo:
            memo[x] = 1 + max(h(left[x]), h(right[x]))
        return memo[x]
    return max(h(x) for x in range(256))


def build(out_path):
    J = bytearray(open(os.path.join(DEC, 'Levels', 'Level16', 'cin0069'), 'rb').read())
    U = open(os.path.join(USDEC, 'Cinematics', 'cin0069'), 'rb').read()
    sj, su = recs(J), recs(U)
    bj = blocks(J, sj[K], sj[K + 1]); bu = blocks(U, su[K], su[K + 1])
    dj = b''.join(o for _, _, o in bj); du = b''.join(o for _, _, o in bu)
    new = bytearray(du); new[0x450:0x452] = dj[0x450:0x452]   # 텍스처 번호(추정)는 일본판 값
    assert new[:0x820] == dj[:0x820], '표지 그림 앞부분이 일본판과 다름'
    enc = bytearray(MAGIC); pos = 0
    for n in (len(o) for _, _, o in bj):                     # 원본과 같은 블록 크기
        blk = bpe.encode(bytes(new[pos:pos + n])); pos += n
        assert height(blk) <= 12, '쌍 중첩 깊이가 원본(12)보다 깊음'
        enc += blk
    size = len(enc)
    out = J[:sj[K]] + enc + b'\0' * ((-size) % 32) + J[sj[K + 1]:]
    struct.pack_into('>I', out, 0x48 + 4 * (K + 1), size)     # 표: 레코드 K 의 압축 크기
    struct.pack_into('>I', out, 0, len(out) - 4)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, 'wb').write(out)
    return len(out)


if __name__ == '__main__':
    print(build(sys.argv[1]))
