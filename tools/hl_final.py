"""책·인벤토리 선택 글씨 최종 만들기(10/20, 사용자 게임 화면으로 하나씩 확인한 방법).

1) 책 옵션 빛 선택 글씨 9장(더하기 합성, 게임이 노란색을 입힘)
   일본판 선택 그림 구조 = 글자는 검정, 글자 둘레·사이는 흰 덩어리(약 200), 덩어리 밖 6px 번짐(116→0).
   글자 자리는 GPT 짝글씨 판 결과의 글자 마스크(제작자료/<id>_共通mask.png). 마스크는 예전 원점 기준이라
   새 원점(일본판 선택 그림의 검은 글자가 판 글씨와 겹치는 자리)으로 옮긴다. 밝기는 일본판 99% 밝기 / 247 배.
   칸 양 끝 15열 안은 한 번 더 흐리게(「한」 왼쪽이 울퉁불퉁하다는 지적).
   「한국어」(g053)는 같은 방법이지만 사용자가 화면 보며 맞춘 자리(내용 왼쪽 3·아래 2) — 새 원점 계산과 같은 값.
2) 켬·끔 판(g046·g047) 평상시 글자: 글자 마스크 속을 일본판 글자 심 색으로(옅게 보인다는 지적).
3) 노란 선택 글씨 8장(투명도 합성, CMPR 이라 투명도 0/255 두 값뿐)
   GPT 그림의 3~4px 반투명 그림자가 압축 뒤 울퉁불퉁한 갈색 덩어리 → 노란 심 + 불투명 갈색 테두리 2px,
   판 회색 글씨가 비칠 자리(판 밝은 글씨 +1px, 심에서 4px 안)는 테두리로 덮음. 그 밖은 투명. (3px 은 더 지저분해서 되돌림)
   16:9 인벤토리도 4:3 그림을 그대로 씀(사용자 확인: JWideInv 그림을 바꿔도 화면 변화 없음). JWideInv 쪽은 wide_sync 자르기만.

입력: work/GPT/짝글씨_판/비교/제작자료/*_共通mask.png, work/GPT/이전/<id>_테두리이전.png·<id>_글자색이전.png (GPT 반영 직후 그림)
python tools/hl_final.py [--check]   → work/gfx/done 에 씀(--check 는 지금 파일과 같은지만 봄)
"""
import os
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import (binary_closing, binary_dilation, binary_fill_holes, distance_transform_edt,
                           gaussian_filter, median_filter)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pair_find as P  # noqa: E402
import wide_sync as W  # noqa: E402
from gpt_hlpair import PAIRS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DONE = os.path.join(ROOT, 'work', 'gfx', 'done')
BAK = os.path.join(ROOT, 'work', 'GPT', '이전')
MASK = os.path.join(ROOT, 'work', 'GPT', '짝글씨_판', '비교', '제작자료', '%s_共通mask.png')

# 빛 선택 글씨 새 원점(일본판 검은 글자 ↔ 판 글씨 겹침 최대, 10/20)
GLOW_ORIGIN = {'g061': (7, 403), 'g059': (106, 392), 'g057': (0, 0), 'g058': (0, 0), 'g052': (254, 60),
               'g053': (167, 60), 'g068': (222, 9), 'g055': (121, 32), 'g056': (119, 4)}
GLOW_MOVE = {'g053': (-3, 2)}   # 사용자 화면 맞춤(예전 원점 기준 내용 이동), 나머지는 원점 차이로 계산
YELLOW = ('g081', 'g087', 'g086', 'g088', 'g089', 'g072', 'g071', 'g035')
PLATE = {'g046': 'g057', 'g047': 'g058'}


def mask(i):
    return np.asarray(Image.open(MASK % i).convert('L')).astype(float) / 255


def glow(mk, scale, left_only=False):
    w = mk.shape[1]; let = mk > 0.15
    dl = distance_transform_edt(~let)
    env = binary_fill_holes(binary_closing(np.pad(binary_dilation(let, iterations=2), 6), np.ones((9, 9))))[6:-6, 6:-6]
    do = distance_transform_edt(~env)
    inside = np.interp(dl, [0, 1, 2, 3, 4, 6], [195, 195, 208, 185, 152, 120])
    outside = np.interp(do, [0, 1, 2, 3, 4, 5, 6], [150, 116, 70, 38, 13, 3, 0])
    v0 = gaussian_filter(np.where(env, inside, outside), 0.5); vs = gaussian_filter(v0, 1.3)
    e = np.arange(w)[None, :] if left_only else np.minimum(np.arange(w), w - 1 - np.arange(w))[None, :]
    wt = np.clip((15 - e) / 6, 0, 1)
    v = (v0 * (1 - wt) + vs * wt) * scale * np.clip(1 - mk * 1.6, 0, 1)
    return np.dstack([v, v, v, np.full(v.shape, 255.)]).round().astype(np.uint8)


def make_glow(i):
    b, ox, oy = PAIRS[i][:3]
    if i == 'g053':   # 첫 시안 그대로(밝기 배율 없음, 왼쪽 15열만 흐리게), 그 뒤 사용자 맞춤 이동
        mk = mask(i)
        a = glow(mk, 1.0, left_only=True)
        dx, dy = GLOW_MOVE[i]
    else:
        nx, ny = GLOW_ORIGIN[i]
        mk = mask(i)
        mk = W.shift((mk * 255).astype(np.uint8)[..., None].repeat(4, 2), ox - nx, oy - ny, black=False)[..., 0] / 255
        a = glow(mk, np.percentile(P.rgba(i, 'src')[..., :3].mean(2), 99) / 247)
        dx = dy = 0
    return W.shift(a, dx, dy, black=True) if (dx or dy) else a


def make_plate(b):
    j = P.rgba(b, 'src').astype(float)
    core = j[(j[..., 3] > 200) & (j[..., :3].mean(2) < 30)][:, :3].mean(0)
    a = np.asarray(Image.open(os.path.join(BAK, b + '_글자색이전.png')).convert('RGBA')).astype(float)
    t = np.clip((mask(PLATE[b]) - 0.3) / 0.5, 0, 1)[..., None]
    a[..., :3] = a[..., :3] * (1 - t) + core * t
    return a.round().astype(np.uint8)


def make_yellow(i, ring_px=2.5):
    b, x, y = PAIRS[i][:3]
    a = np.asarray(Image.open(os.path.join(BAK, i + '_테두리이전.png')).convert('RGBA')).astype(float)
    h, w = a.shape[:2]; al = a[..., 3]
    core = (al > 200) & (a[..., 1] > a[..., 2] + 20) & (a[..., :3].mean(2) > 90)
    d = distance_transform_edt(~core)
    reg = np.pad(P.rgba(b, 'done').astype(float), ((0, 4), (0, 4), (0, 0)))[y:y + h, x:x + w]
    RL = reg[..., :3].mean(2)
    let = binary_dilation((RL > median_filter(RL, size=9) + 10) & (reg[..., 3] > 128), iterations=1)
    ring = ((d > 0) & (d <= ring_px)) | (let & (d > 0) & (d <= ring_px + 2))
    bc = a[(d > 0) & (d <= 1.5) & (al > 200)][:, :3].mean(0)
    a[ring & ((al < 128) | (a[..., :3].mean(2) > bc.mean() + 25)), :3] = bc
    a[ring, 3] = 255; a[~ring & ~core, 3] = 0
    return a.round().astype(np.uint8)


def main():
    check = '--check' in sys.argv
    out = {i: make_glow(i) for i in GLOW_ORIGIN}
    out.update({b: make_plate(b) for b in PLATE})   # 판(g046·g047)은 노란 글씨 판 글씨 마스크 계산보다 먼저
    out.update({i: make_yellow(i) for i in YELLOW})
    bad = 0
    for i, a in out.items():
        p = os.path.join(DONE, i + '.png')
        if check:
            cur = np.asarray(Image.open(p).convert('RGBA'))
            same = cur.shape == a.shape and (cur == a).all()
            bad += not same
            print(i, '같음' if same else '다름')
        else:
            Image.fromarray(a, 'RGBA').save(p)
    if not check:
        for i, (n, dx, dy) in W.WIDE_HL.items():
            W.save(i, W.crop(W.load(n), dx, dy, 64, 32))
    print('다른 그림', bad) if check else print('씀', len(out), '+ 16:9 글씨', len(W.WIDE_HL))


if __name__ == '__main__':
    main()
