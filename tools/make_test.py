"""2단계 출력 시험 파일 생성.

  python make_test.py A   : 무압축 우회 DOL + 방 문구 2줄·시스템 문구 1줄·컷신 자막 1줄 한글(폰트 6번 장 0xA0~ 칸)
  python make_test.py B   : A + 폰트 8번째 장(0x07xx) 추가, 폭 표 0x800칸으로 확장, 방 문구 1줄에 8번째 장 글자 사용
결과: build/test_<A|B>/ 아래 디스크 경로 그대로(교체 파일) + main.dol
"""
import os
import shutil
import struct
import sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpe
import cmpr
import edtext
import tpl
import txtpak
import patch_dol

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
EX = os.path.join(ROOT, 'extract', 'jp'); DEC = os.path.join(ROOT, 'extract', 'dec', 'jp')
FONT = 'C:/Windows/Fonts/malgun.ttf'
CELL = 28
KO_BASE = 0x06A0          # 6번 장 0xA0~0xD7 (두 폭 표 1752·1763 범위 안)
SHEET7 = 0x0700
BOOTS = ['JBootPak.bin', 'JBootPkW.bin', 'JBtPakES.bin', 'JBtPakJS.bin']
FONTS = ['JFonts.tpl', 'JfontsEAD.tpl']

TEXTS = {
    'room': {  # 현관 홀(방 69): 들어가자마자 조사 가능
        'PORTRAITS': '조상들의 초상화가 걸려 있다.\n한글 출력 시험 첫째 줄입니다.',
        'CLOCK': '아름다운 \\ay탁상시계\\aw다. 바늘이 멈춰 있다.',
    },
    'boot': '지금은 쓸 수 없다.',
    'cin': {
        'ALEX_Uh_Hello': '어... 여보세요?',
        'LEGRASSE_Miss_Alexandra_Roivas': '알렉산드라 로이바스 씨입니까?',
    },
}
B_LINE = ('PORTRAITS', '조상들의 초상화가 걸려 있다.\n팔번째 장 시험입니다.', '팔번째')


# ---------- 글자 배정·부호화 ----------
class Charset:
    def __init__(self):
        self.map = {}; self.next6 = KO_BASE; self.next7 = SHEET7

    def code(self, ch, sheet7=False):
        key = (ch, sheet7)
        if key not in self.map:
            if sheet7:
                self.map[key] = self.next7; self.next7 += 1
            else:
                assert self.next6 <= 0x06D7, '시험용 칸 부족'
                self.map[key] = self.next6; self.next6 += 1
        return self.map[key]

    def encode(self, s, sheet7_chars=''):
        out = bytearray()
        for ch in s:
            if ord(ch) < 0x80:
                out += struct.pack('>H', ord(ch))
            else:
                out += struct.pack('>H', self.code(ch, ch in sheet7_chars))
        return bytes(out)


def glyph(ch):
    """28x28 흰 글자 + 오른쪽 아래 어두운 그림자(원본 폰트 모양)."""
    S = 4
    f = ImageFont.truetype(FONT, 23 * S)
    m = Image.new('L', (CELL * S, CELL * S), 0)
    ImageDraw.Draw(m).text((CELL * S // 2, CELL * S // 2 + S), ch, font=f, fill=255, anchor='mm')
    m = m.resize((CELL, CELL), Image.LANCZOS)
    sh = Image.new('L', (CELL, CELL), 0); sh.paste(m, (1, 1))
    out = Image.new('RGBA', (CELL, CELL), (0, 0, 0, 0))
    mp, sp, op = m.load(), sh.load(), out.load()
    for y in range(CELL):
        for x in range(CELL):
            a = mp[x, y]
            if a >= 150:
                op[x, y] = (255, 255, 255, 255)
            elif a >= 70:
                op[x, y] = (164, 164, 164, 255)
            elif sp[x, y] >= 110:
                op[x, y] = (74, 72, 74, 255)
    return out


def build_font(path, cs, dst):
    d = bytearray(open(path, 'rb').read())
    imgs = list(tpl.images(bytes(d)))
    need7 = any(c >= SHEET7 for c in cs.map.values())
    if need7:
        d = add_sheet(d)
        imgs = list(tpl.images(bytes(d)))
    for (ch, _), code in cs.map.items():
        sheet, cell = code >> 8, code & 0xFF
        i, w, h, fmt, doff = imgs[sheet]
        img = tpl.decode(bytes(d), doff, w, h, fmt)  # 원본 좌표(저장 순서)
        g = glyph(ch).transpose(Image.FLIP_TOP_BOTTOM)  # 저장은 위아래 뒤집힌 상태
        x0 = (cell % 16) * CELL; y0 = h - (cell // 16 + 1) * CELL
        img.paste(Image.new('RGBA', (CELL, CELL), (0, 0, 0, 0)), (x0, y0))
        img.paste(g, (x0, y0))
        cmpr.patch(d, doff, w, h, img, [(x0, y0, x0 + CELL, y0 + CELL)])
    open(dst, 'wb').write(d)


def add_sheet(d):
    """TPL 끝에 빈(투명) 448x448 CMPR 장을 하나 붙인다. 이미지 헤더는 기존 마지막 것 복사."""
    n, tbl = struct.unpack('>II', d[4:12])
    ents = [struct.unpack('>II', d[tbl + 8 * i:tbl + 8 * i + 8]) for i in range(n)]
    # 표가 이미지 헤더·데이터 앞에 있어 늘리면 모두 밀림 → 새로 짠다
    heads = [bytes(d[io:io + 0x24]) for io, po in ents]
    datas = []
    for io, po in ents:
        h, w, fmt, doff = struct.unpack('>HHII', d[io:io + 12])
        datas.append(bytes(d[doff:doff + w * h // 2]))
    w = h = 448
    blank = struct.pack('>HHI', 0, 0xFFFF, 0xFFFFFFFF) * (w * h // 16)
    heads.append(heads[-1]); datas.append(blank)
    n2 = n + 1
    out = bytearray(d[:12]); struct.pack_into('>I', out, 4, n2)
    tbl2 = 12
    pos = tbl2 + 8 * n2
    head_pos = []
    for hd in heads:
        pos = (pos + 0x1F) & ~0x1F; head_pos.append(pos); pos += len(hd)
    data_pos = []
    for dt in datas:
        pos = (pos + 0x3F) & ~0x3F; data_pos.append(pos); pos += len(dt)
    out += bytes(pos - len(out))
    for i in range(n2):
        struct.pack_into('>II', out, tbl2 + 8 * i, head_pos[i], 0)
        hd = bytearray(heads[i]); struct.pack_into('>I', hd, 8, data_pos[i])
        out[head_pos[i]:head_pos[i] + len(hd)] = hd
        out[data_pos[i]:data_pos[i] + len(datas[i])] = datas[i]
    assert struct.unpack('>I', d[8:12])[0] == 12 and all(po == 0 for io, po in ents), 'TPL 형태 가정이 다름'
    return out


# ---------- 레코드 수정 ----------
def new_body(body, text_bytes):
    """본문 안 텍스트만 바꾼다(헤더·라벨·끝 0 유지)."""
    p = 0x18 + 2
    label, old = edtext.parse_body(0, body, True)
    if edtext._is_label(body[p:p + 32]) and edtext._is_label(body[p + 32:p + 96]) and body[p + 32]:
        p += 96
    return body[:p] + text_bytes + body[p + len(old):]


def is_ja(t):
    return any(b for b in t[0::2])


def inplace(d, st, idx, text_bytes):
    """문자열표 st 의 idx 레코드를 같은 자리에 다시 쓴다(원래 길이 이하일 때만)."""
    o, l = struct.unpack('>II', d[st + 8 + 8 * idx:st + 16 + 8 * idx])
    rec = bytes(d[st + o:st + o + l])
    body, _ = bpe.decode(rec, 4)
    nb = rec[:4] + bpe.encode(new_body(body, text_bytes))
    assert len(nb) <= l, '레코드가 원래보다 김(%d > %d)' % (len(nb), l)
    d[st + o:st + o + len(nb)] = nb
    struct.pack_into('>I', d, st + 12 + 8 * idx, len(nb))


def patch_room(cs, sheet7_line=None):
    p = os.path.join(DEC, 'Levels', 'Level00', 'JRmTxt00.cmp')
    tabs = txtpak.parse(open(p, 'rb').read())
    done = set()
    for t in tabs:
        for k, it in enumerate(t):
            if isinstance(it, tuple):
                continue
            body, _ = bpe.decode(it, 4)
            label, txt = edtext.parse_body(struct.unpack('>I', it[:4])[0], body, True)
            name = label.split('/')[-1] if label else ''
            if name in TEXTS['room'] and name not in done:
                s = TEXTS['room'][name]; s7 = ''
                if sheet7_line and name == sheet7_line[0]:
                    s, s7 = sheet7_line[1], sheet7_line[2]
                t[k] = it[:4] + bpe.encode(new_body(body, cs.encode(s, s7)))
                done.add(name)
    assert done == set(TEXTS['room']), done
    return txtpak.build(tabs)


def patch_boot(name, cs):
    """시스템 묶음의 텍스트 블록에서 CannotUse(일본어) 문구를 바꾼다. 반환: (원본, {블록번호: 새 블록}, 바꾼 수)"""
    d = open(os.path.join(EX, name), 'rb').read()
    n = struct.unpack('>I', d[:4])[0]
    repl = {}; hit = 0
    for i in range(n):
        o, s = struct.unpack('>II', d[8 + 8 * i:16 + 8 * i])
        if not s:
            continue
        blk = d[o:o + s]
        try:
            tabs = txtpak.parse(struct.pack('>I', len(blk)) + blk)
        except Exception:
            continue
        ch = False
        for t in tabs:
            for k, it in enumerate(t):
                if isinstance(it, tuple):
                    continue
                body, _ = bpe.decode(it, 4)
                label, txt = edtext.parse_body(struct.unpack('>I', it[:4])[0], body, True)
                if label and label.endswith('/CannotUse') and is_ja(txt):
                    t[k] = it[:4] + bpe.encode(new_body(body, cs.encode(TEXTS['boot']))); hit += 1; ch = True
        if ch:
            repl[i] = txtpak.build(tabs)[4:]
    assert hit >= 1, name
    return bytearray(d), repl, hit


def width_block(d, codes, extend=False):
    """폭 표(최상위 2번 블록): [개수 u32][기본 폭 1바이트][글자별 폭 × 개수]. 한글 칸 폭 26. extend 면 0x800칸으로 늘린다."""
    o, s = struct.unpack('>II', d[8 + 16:8 + 24])
    blk = bytearray(d[o:o + s]); cnt = struct.unpack('>I', blk[:4])[0]
    if extend:
        tail = blk[5 + cnt:]
        blk = blk[:5 + cnt] + bytes([26]) * (0x800 - cnt) + tail
        struct.pack_into('>I', blk, 0, 0x800); cnt = 0x800
    for c in codes:
        assert c < cnt, '폭 표 범위 밖 0x%X' % c
        blk[5 + c] = 26
    return bytes(blk)


def repack(d, repl):
    """최상위 0x6B5 묶음을 0x20 정렬로 다시 짠다(블록 내용은 각자 상대 오프셋이라 그대로 옮김)."""
    n = struct.unpack('>I', d[:4])[0]
    ents = [struct.unpack('>II', d[8 + 8 * i:16 + 8 * i]) for i in range(n)]
    first = min(o for o, s in ents if s)
    out = bytearray(d[:first])
    for i, (o, s) in enumerate(ents):
        if not s:
            continue
        b = repl.get(i, d[o:o + s])
        out += bytes((-len(out)) % 0x20)
        struct.pack_into('>II', out, 8 + 8 * i, len(out), len(b))
        out += b
    last = max(o + s for o, s in ents if s)
    out += d[last:]  # 끝 꼬리(있다면) 유지
    return out


def patch_cin(cs):
    """첫 컷신(Act01) 일본어 자막 묶음을 다시 짠다(길이 제한 없음)."""
    p = os.path.join(DEC, 'Levels', 'Level00', 'cin0005.bin')
    d = open(p, 'rb').read()
    parts = txtpak.cin_parts(d); repl = {}; done = []
    for i in range(1, len(parts)):
        if not parts[i][1]:
            continue
        tabs = txtpak.cin_text(d, i); hit = False
        for t in tabs:
            for k, it in enumerate(t):
                if isinstance(it, tuple):
                    continue
                body, _ = bpe.decode(it, 4)
                label, txt = edtext.parse_body(struct.unpack('>I', it[:4])[0], body, True)
                name = label.split('/')[-1] if label else ''
                if name in TEXTS['cin'] and is_ja(txt):
                    t[k] = it[:4] + bpe.encode(new_body(body, cs.encode(TEXTS['cin'][name])))
                    done.append(name); hit = True
        if hit:
            repl[i] = tabs
    assert len(done) == len(TEXTS['cin']), done
    return txtpak.cin_build(d, repl), ', '.join(done)


def ruler(px):
    """'600:가가…|' 형태로 폭이 px 에 가장 가까운 눈금 줄(한글 26px·폭 표 기준)."""
    import check_overflow
    s = '%d:' % px
    while check_overflow.line_px(s + '가|') <= px:
        s += '가'
    return s + '|'


def measure_texts():
    """3단계 측정판(M) 문구: 창 폭 눈금·자동 줄바꿈·줄 수·자막 길이/두 줄."""
    return {
        'room': {
            'PORTRAITS': '\n'.join(ruler(p) for p in (600, 650, 700, 780)),
            'CLOCK': ' '.join('%d번 자동 줄바꿈 시험 문장입니다.' % i for i in range(1, 6)),
            'WINDOWS': '\n'.join('%d줄' % i for i in range(1, 17)),
        },
        'boot': TEXTS['boot'],
        'cin': {
            'ALEX_Uh_Hello': ruler(780),
            'LEGRASSE_Miss_Alexandra_Roivas': '두 줄 자막 시험 첫째 줄\n두 줄 자막 시험 둘째 줄',
            'ALEX_Uh_Yeah_Who_is_this': ruler(700),
        },
    }


def main(kind):
    if kind == 'M':
        m = measure_texts(); TEXTS.clear(); TEXTS.update(m)
        for k, v in TEXTS['room'].items():
            print('방', k, repr(v))
        for k, v in TEXTS['cin'].items():
            print('자막', k, repr(v))
    out = os.path.join(ROOT, 'build', 'test_' + kind)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, 'Levels', 'Level00'))
    cs = Charset()
    room = patch_room(cs, B_LINE if kind == 'B' else None)
    open(os.path.join(out, 'Levels', 'Level00', 'JRmTxt00.cmp'), 'wb').write(room)
    cin, label = patch_cin(cs)
    open(os.path.join(out, 'Levels', 'Level00', 'cin0005.bin'), 'wb').write(cin)
    boots = {b: patch_boot(b, cs) for b in BOOTS}
    codes = sorted(cs.map.values())
    for b, (d, repl, hit) in boots.items():
        repl[2] = width_block(d, codes, extend=(kind == 'B'))
        open(os.path.join(out, b), 'wb').write(repack(d, repl))
        print(b, '시험 문구', hit, '곳')
    for f in FONTS:
        build_font(os.path.join(EX, f), cs, os.path.join(out, f))
    patch_dol.main(os.path.join(EX, 'main.dol'), os.path.join(out, 'main.dol'))
    print('컷신 레코드', label, '/ 한글 글자', len(cs.map), '자:', ''.join(c for c, _ in cs.map),
          '/ 칸 0x%X~0x%X' % (min(codes), max(codes)))


if __name__ == '__main__':
    main(sys.argv[1])
