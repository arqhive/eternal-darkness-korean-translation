"""무압축 우회 DOL 패치(일본판 main.dol).

SK_ASC 래퍼(0x8014191c)는 앞 8바이트가 '*SK_ASC*'가 아니면 0x80141994 에서 -1 을 돌려준다.
그 자리를 복사 루틴으로 돌려, 표식이 없는 파일은 해제본 그대로(첫 u32=본문 길이) 쓰기 콜백에 넘긴다.
복사 루틴 자리: 0x80100248(TRKTargetSupportRequest, 디버거 전용 — bi2 디버그 플래그 0이라 실행 안 됨).
래퍼 레지스터: r27=파일 크기, r28=읽기(buf,n,ctx), r29=쓰기(buf,n,ctx; 0=계속,1=중단), r30=ctx, r31=작업 메모리, r1+8=이미 읽은 8바이트.

사용: python patch_dol.py <원본 main.dol> <출력 main.dol>
"""
import struct
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dol import Dol

HOOK, COPY, RET = 0x80141994, 0x80100248, 0x80141998


def b(src, dst, link=0):
    return 0x48000000 | ((dst - src) & 0x03FFFFFC) | link


def bc(src, dst, bo, bi):
    return 0x40000000 | bo << 21 | bi << 16 | ((dst - src) & 0xFFFC)


def addi(rd, ra, imm): return 14 << 26 | rd << 21 | ra << 16 | (imm & 0xFFFF)
def li(rd, imm): return addi(rd, 0, imm)
def mr(rd, rs): return 31 << 26 | rs << 21 | rd << 16 | rs << 11 | 444 << 1
def mtctr(rs): return 31 << 26 | rs << 21 | 9 << 16 | 467 << 1
def cmpwi(ra, imm): return 11 << 26 | ra << 16 | (imm & 0xFFFF)
def subf(rd, ra, rb): return 31 << 26 | rd << 21 | ra << 16 | rb << 11 | 40 << 1
BCTRL = 0x4E800421
# 조건 분기: cr0 비트 0=lt 1=gt 2=eq. bo 12=참이면, 4=거짓이면
def beq(s, d): return bc(s, d, 12, 2)
def bne(s, d): return bc(s, d, 4, 2)
def ble(s, d): return bc(s, d, 4, 1)


def routine():
    code = []; labels = {}
    def emit(f):
        code.append(f)
    A = lambda i: COPY + 4 * i
    # 두 번 훑어 라벨 주소 확정
    for pass_ in range(2):
        code.clear(); L = labels
        g = lambda name: L.get(name, COPY)
        emit(lambda a: addi(3, 1, 8)); emit(lambda a: li(4, 8)); emit(lambda a: mr(5, 30))
        emit(lambda a: mtctr(29)); emit(lambda a: BCTRL)
        emit(lambda a: cmpwi(3, 0)); emit(lambda a: bne(a, g('done')))
        emit(lambda a: addi(27, 27, -8))
        L['loop'] = A(len(code))
        emit(lambda a: cmpwi(27, 0)); emit(lambda a: ble(a, g('done')))
        emit(lambda a: mr(4, 27)); emit(lambda a: cmpwi(4, 0x1000)); emit(lambda a: ble(a, a + 8)); emit(lambda a: li(4, 0x1000))
        emit(lambda a: mr(3, 31)); emit(lambda a: mr(5, 30)); emit(lambda a: mtctr(28)); emit(lambda a: BCTRL)
        emit(lambda a: mr(4, 27)); emit(lambda a: cmpwi(4, 0x1000)); emit(lambda a: ble(a, a + 8)); emit(lambda a: li(4, 0x1000))
        emit(lambda a: subf(27, 4, 27))
        emit(lambda a: mr(3, 31)); emit(lambda a: mr(5, 30)); emit(lambda a: mtctr(29)); emit(lambda a: BCTRL)
        emit(lambda a: cmpwi(3, 0)); emit(lambda a: beq(a, g('loop')))
        L['done'] = A(len(code))
        emit(lambda a: li(3, 0)); emit(lambda a: b(a, RET))
    return b''.join(struct.pack('>I', f(A(i))) for i, f in enumerate(code))


def patch(d):
    D = Dol.__new__(Dol); D.d = d
    Dol.__init__(D, None) if False else None
    return d


def main(src, dst):
    D = Dol(src); d = bytearray(D.d)
    assert struct.unpack('>I', D.read(HOOK, 4))[0] == 0x3860FFFF, '훅 자리가 li r3,-1 이 아님'
    code = routine()
    d[D.a2o(COPY):D.a2o(COPY) + len(code)] = code
    d[D.a2o(HOOK):D.a2o(HOOK) + 4] = struct.pack('>I', b(HOOK, COPY))
    open(dst, 'wb').write(d)
    print('패치 완료: 복사 루틴 %d명령' % (len(code) // 4))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
