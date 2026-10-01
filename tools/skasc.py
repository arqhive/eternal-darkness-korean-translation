"""*SK_ASC* 산술부호 압축 해제 — 일본판 main.dol 의 해제 루틴(0x8014191c)을 unicorn 으로 실행.

사용: python skasc.py <입력> <출력>   /  모듈: decompress(bytes) -> bytes
래퍼 인자: r3=전체 크기, r4=읽기콜백(buf,n,ctx), r5=쓰기콜백(buf,n,ctx), r6=ctx, r7=작업 메모리
"""
import os
import struct
import sys
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
from unicorn.ppc_const import UC_PPC_REG_PC, UC_PPC_REG_LR, UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5, UC_PPC_REG_6, UC_PPC_REG_7

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dol import Dol

DOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'extract', 'jp', 'main.dol')
WRAP = 0x8014191C
RD, WR, END = 0x81000000, 0x81000010, 0x81000020   # 콜백·종료 표식 주소
WORK, STACK = 0x80800000, 0x80F00000

_uc = None


def _machine(dol=None):
    global _uc
    if _uc:
        return _uc
    D = Dol(dol or DOL)
    uc = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    uc.mem_map(0x80000000, 0x01800000)
    for i, o, base, s in D.secs:
        uc.mem_write(base, D.d[o:o + s])
    uc.mem_write(RD, b'\x4E\x80\x00\x20' * 12)  # blr (훅에서 처리 후 복귀)
    _uc = uc
    return uc


def decompress(data, dol=None, raw_ok=False):
    assert raw_ok or data[:8] == b"*SK_ASC*"
    uc = _machine(dol)
    st = {'pos': 0, 'out': bytearray()}

    def hook(uc, addr, size, _):
        if addr == RD:
            buf, n = uc.reg_read(UC_PPC_REG_3), uc.reg_read(UC_PPC_REG_4)
            chunk = data[st['pos']:st['pos'] + n]; st['pos'] += len(chunk)
            uc.mem_write(buf, chunk); uc.reg_write(UC_PPC_REG_3, len(chunk))
        elif addr == WR:
            buf, n = uc.reg_read(UC_PPC_REG_3), uc.reg_read(UC_PPC_REG_4)
            st['out'] += uc.mem_read(buf, n); uc.reg_write(UC_PPC_REG_3, 0)
        elif addr == END:
            uc.emu_stop()

    h = uc.hook_add(UC_HOOK_CODE, hook, begin=RD, end=END + 4)
    uc.mem_write(WORK, bytes(0x10000))
    uc.reg_write(UC_PPC_REG_1, STACK)
    uc.reg_write(UC_PPC_REG_3, len(data)); uc.reg_write(UC_PPC_REG_4, RD); uc.reg_write(UC_PPC_REG_5, WR)
    uc.reg_write(UC_PPC_REG_6, 0); uc.reg_write(UC_PPC_REG_7, WORK)
    uc.reg_write(UC_PPC_REG_LR, END)
    uc.emu_start(WRAP, END)
    uc.hook_del(h)
    return bytes(st['out'])


if __name__ == '__main__':
    open(sys.argv[2], 'wb').write(decompress(open(sys.argv[1], 'rb').read()))
