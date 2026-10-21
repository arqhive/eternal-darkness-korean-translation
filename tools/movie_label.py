"""책 옵션 「영상」 글씨 키우기(10/21 사용자: 해부서만큼 크게).

GPT 짝글씨 판(g060)과 같은 방식: 연천허목체를 실제 크기 정수 px로 직접 그리고 오른쪽 1px 겹쳐 굵게, 평상시 색 (57,40,24).
18px → 24px(해부서 g069 글자 높이 24px), 글자 가운데는 예전 자리(32,413 크기 31x19의 가운데) 그대로.
판 글씨는 글자 지운 판(g060_clean)으로 예전 글자 자리를 되돌린 뒤 새 글자를 칠하고,
빛 선택 글씨(g061)용 글자 마스크를 칸 좌표(판 10,405 기준)로 따로 저장 → hl_final 이 이 마스크로 빛을 만든다.
python tools/movie_label.py   → work/gfx/done/g060.png, 제작자료/g061_共通mask_24px.png (예전 판은 work/GPT/이전/g060_영상18px.png)
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_dilation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, 'work', 'GPT', '짝글씨_판', '비교', '제작자료')
DONE = os.path.join(ROOT, 'work', 'gfx', 'done')
BAK = os.path.join(ROOT, 'work', 'GPT', '이전')
FONT = os.path.join(os.environ['LOCALAPPDATA'], 'Microsoft', 'Windows', 'Fonts', 'YeoncheonHeomok.ttf')
TEXT, OLD_PX, NEW_PX = '영상', 18, 24
OLD_POS = (32, 413)          # 검증_제작정보.json glyph_position
SLOT = (10, 405, 81, 38)     # g061 칸(판 좌표 x, y, 너비, 높이)
INK = (57, 40, 24)


def glyph(size):
    f = ImageFont.truetype(FONT, size)
    im = Image.new('L', (256, size * 4))
    ImageDraw.Draw(im).text((16, 16), TEXT, font=f, fill=255)
    a = np.array(im); s = np.zeros_like(a); s[:, 1:] = a[:, :-1]
    a = np.maximum(a, s)
    return np.array(Image.fromarray(a).crop(Image.fromarray(a).getbbox()))


def main():
    bak = os.path.join(BAK, 'g060_영상18px.png')
    if not os.path.exists(bak):
        Image.open(os.path.join(DONE, 'g060.png')).save(bak)
    board = np.asarray(Image.open(bak).convert('RGBA')).copy()
    clean = np.asarray(Image.open(os.path.join(ART, 'g060_clean.png')).convert('RGBA'))
    old = glyph(OLD_PX); oh, ow = old.shape
    area = np.zeros(board.shape[:2], bool)
    area[OLD_POS[1]:OLD_POS[1] + oh, OLD_POS[0]:OLD_POS[0] + ow] = old > 0
    area = binary_dilation(area, iterations=1)
    board[area] = clean[area]
    new = glyph(NEW_PX); nh, nw = new.shape
    cx, cy = OLD_POS[0] + ow / 2, OLD_POS[1] + oh / 2
    x0, y0 = int(round(cx - nw / 2)), int(round(cy - nh / 2))
    a = new.astype(float)[..., None] / 255
    reg = board[y0:y0 + nh, x0:x0 + nw, :3].astype(float)
    board[y0:y0 + nh, x0:x0 + nw, :3] = np.round(reg * (1 - a) + np.array(INK) * a).astype(np.uint8)
    Image.fromarray(board, 'RGBA').save(os.path.join(DONE, 'g060.png'))
    sx, sy, sw, sh = SLOT
    m = np.zeros((sh, sw), np.uint8)
    m[y0 - sy:y0 - sy + nh, x0 - sx:x0 - sx + nw] = new
    Image.fromarray(m, 'L').save(os.path.join(ART, 'g061_共通mask_24px.png'))
    print('영상 %dpx → %dpx, 판 자리 (%d,%d) 크기 %dx%d, 칸 안 (%d,%d)' % (OLD_PX, NEW_PX, x0, y0, nw, nh, x0 - sx, y0 - sy))


if __name__ == '__main__':
    main()
