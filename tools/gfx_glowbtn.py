"""검정 바탕 + 흰 빛 덩어리 위 어두운 글자(선택 강조 그림, g052·g053 등).
원본 바탕색으로 전부 덮고, 한글을 어두운 색으로 쓴 뒤 글자 모양을 넓혀 흐린 흰 빛을 밑에 깐다.
python gfx_glowbtn.py g052 ..."""
import json, os, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, 'work', 'gfx')
CFG = {
    'g052': {'text': '영어', 'size': 15, 'tint': True, 'soft': True},
    'g053': {'text': '한국어', 'size': 14, 'tint': True, 'soft': True},
    # 소리 설정(g054) 강조: 빛이 글자 모양을 따라 번짐(halo), 크기는 g054 글자와 같게
    'g055': {'text': '스테레오 서라운드', 'size': 20, 'halo': True},
    'g056': {'text': '모노', 'size': 20, 'halo': True, 'gpct': 99.3},   # 빛 면적이 작아 97%로는 원본보다 어두움
    'g057': {'text': '켬', 'size': 22, 'halo': True},
    'g058': {'text': '끔', 'size': 22, 'halo': True},
    # 진동 설정 이름표: 오른쪽 맞춤(원본 글자 오른쪽 끝에 맞춤)
    'g061': {'text': '영상', 'size': 18, 'left': True, 'tint': True, 'soft': True},   # g060 판 글자처럼 원본 시작점에 왼쪽 맞춤
    'g062': {'text': '부검', 'size': 22, 'tint': True, 'soft': True},
    'g068': {'text': '스테레오', 'size': 17, 'tint': True, 'soft': True},   # 그림 폭 69px에 빛판까지 들어가게(g054 판은 20)
    # 타이틀 「スタート」: 검정 바탕 흰 글자 + 흰 빛 번짐, 원본처럼 왼쪽 맞춤
    'g124': {'text': '시작하기', 'size': 22, 'white': True, 'left': True, 'halo': True},
    'g129': {'text': '불러오기', 'size': 22, 'white': True, 'left': True, 'halo': True},   # 「ロード」, g124와 같은 꼴
    'g130': {'text': '옵션', 'size': 22, 'white': True, 'left': True, 'halo': True},
    'g131': {'text': '챕터 선택', 'size': 22, 'white': True, 'left': True, 'halo': True},
    'g132': {'text': '크레딧', 'size': 22, 'white': True, 'left': True, 'halo': True},
    # 옵션 메뉴(g127) 항목을 고를 때 덮이는 흰 글자: g127 글자와 같은 크기 22, 원본 시작점 왼쪽 맞춤
    'g133': {'text': '진동', 'size': 22, 'white': True, 'left': True, 'halo': True},
    'g134': {'text': '음량 조절', 'size': 22, 'white': True, 'left': True, 'halo': True},
    'g135': {'text': '밝기 조절', 'size': 22, 'white': True, 'left': True, 'halo': True},
    # 옵션 화면 선택지(검정 바탕 흰 글자, 빛 없음): 원본 글자 가운데
    'g139': {'text': '켬', 'size': 22, 'white': True, 'plain': True, 'halo': True, 'bold': True},
    'g140': {'text': '끔', 'size': 22, 'white': True, 'plain': True, 'halo': True, 'bold': True},
    'g143': {'text': '한국어', 'size': 22, 'white': True, 'plain': True, 'halo': True, 'bold': True},
    'g144': {'text': '영어', 'size': 22, 'white': True, 'plain': True, 'halo': True, 'bold': True},
    # 옵션 항목 고를 때(빛 있는 흰 글자): g127 글자와 같은 크기, 원본 시작점 왼쪽 맞춤 / 선택지는 가운데
    'g145': {'text': '자막', 'size': 22, 'white': True, 'left': True, 'halo': True},
    'g149': {'text': '와이드 화면', 'size': 22, 'white': True, 'left': True, 'halo': True},
    'g146': {'text': '켬', 'size': 22, 'white': True, 'halo': True, 'bold': True},
    'g147': {'text': '끔', 'size': 22, 'white': True, 'halo': True, 'bold': True},
    # 오디오 모드 항목(빛 있는 흰 글자): 메뉴 이름 22, 선택지 20, 원본 시작점 왼쪽 맞춤
    'g151': {'text': '오디오 모드', 'size': 22, 'white': True, 'left': True, 'halo': True},
    'g152': {'text': '모노', 'size': 20, 'white': True, 'left': True, 'halo': True},
    'g153': {'text': '스테레오', 'size': 20, 'white': True, 'left': True, 'halo': True},
    'g154': {'text': '스테레오 서라운드', 'size': 20, 'white': True, 'left': True, 'halo': True},
    # 오디오 모드 선택지 빛 없는 판(g152~g154와 같은 자리·크기)
    'g155': {'text': '모노', 'size': 20, 'white': True, 'plain': True, 'left': True, 'halo': True},
    'g156': {'text': '스테레오', 'size': 20, 'white': True, 'plain': True, 'left': True, 'halo': True},
    'g157': {'text': '스테레오 서라운드', 'size': 20, 'white': True, 'plain': True, 'left': True, 'halo': True},
    'g158': {'text': '설정 저장', 'size': 22, 'white': True, 'left': True, 'halo': True},
    # 메모리 카드 빈칸 표시(하늘빛 글자, 빛 없음): g070과 같은 말
    'g159': {'text': '비어 있음', 'size': 20, 'white': True, 'plain': True, 'halo': True, 'color': (160, 224, 238)},
    # 메모리 카드 슬롯 고를 때(청록 빛판 위 어두운 글자): 색은 원본에서 잼
    'g163': {'text': '슬롯 A', 'size': 22, 'tint': True, 'soft': True},
    'g164': {'text': '슬롯 B', 'size': 22, 'tint': True, 'soft': True},
    # 언어 선택(빛 있는 흰 글자): 낱말마다 일본어 자리 / 선택지는 g143·g144와 같은 자리에 빛만 더함
    'g167': {'text': '언어 선택|한국어', 'size': 22, 'white': True, 'halo': True, 'bold': True, 'words': True},
    'g168': {'text': '한국어', 'size': 22, 'white': True, 'halo': True, 'bold': True},
    'g169': {'text': '영어', 'size': 22, 'white': True, 'halo': True, 'bold': True},
    'g059': {'text': '진동  기능:', 'size': 20, 'right': True, 'halo': True, 'bold': True},
}
FONT = os.path.join(ROOT, 'work', 'fonts', 'YeoncheonHeomok.ttf')


def make(gid, c):
    jp = np.asarray(Image.open(os.path.join(G, 'src', gid + '_jp.png')).convert('RGBA')).astype(np.float32)
    H, W = jp.shape[:2]
    L = jp[..., :3].mean(2)
    bg = np.median(np.concatenate([L[0], L[-1], L[:, 0], L[:, -1]]))
    glowmax = np.percentile(L, c.get('gpct', 97))
    # 원본 빛 덩어리 중심(밝은 곳)에 맞춤
    ys, xs = np.where(L > 60)
    cx, cy = (xs.min() + xs.max() + 1) / 2, (ys.min() + ys.max() + 1) / 2
    f = ImageFont.truetype(FONT, c['size'])
    l, t, r, b = f.getbbox(c['text'])
    txt = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(txt)
    ox, oy = round(cx - (r - l) / 2 - l), round(cy - (b - t) / 2 - t)
    if c.get('left'):   # 원본 글자 덩어리 왼쪽 끝에 맞춤
        ox = round(xs.min() + 3 - l)
    if c.get('right'):   # 원본 글자 덩어리 오른쪽 끝에 맞춤
        ox = round(xs.max() - 3 - r)
    for dx, dy in (((0, 0), (1, 0)) if c.get('halo') and not c.get('bold') else ((0, 0), (1, 0), (0, 1), (1, 1))):   # 원본 강조 글자는 굵음: 가로·세로 1px 겹쳐 찍기
        d.text((ox + dx, oy + dy), c['text'], font=f, fill=255)
    if c.get('words'):   # 낱말마다 일본어 낱말 덩어리(가로 틈 8px 이상으로 나눔) 가운데에 따로 씀
        txt = Image.new('L', (W, H), 0)
        d = ImageDraw.Draw(txt)
        cols = np.where((L > 60).any(0))[0]
        groups, start = [], cols[0]
        for a, b in zip(cols[:-1], cols[1:]):
            if b - a > 8:
                groups.append((start, a)); start = b
        groups.append((start, cols[-1]))
        for (gx0, gx1), w in zip(groups, c['text'].split('|')):
            for dx, dy in (((0, 0), (1, 0)) if c.get('halo') and not c.get('bold') else ((0, 0), (1, 0), (0, 1), (1, 1))):
                d.text(((gx0 + gx1 + 1) / 2 + dx, cy + dy), w, font=f, fill=255, anchor='mm')
        print('  낱말 자리', groups)
    m = np.asarray(txt).astype(np.float32) / 255
    # 원본처럼 글자 덩어리 전체를 감싸는 둥근 빛판: 크게 넓혀 구멍을 메운 뒤 가장자리만 흐림
    ty, tx = np.where(m > 0.3)
    mg = c.get('margin', 2)
    if c.get('halo'):   # 글자 모양을 따라 번지는 빛
        gl = cv2.dilate(m, np.ones((5, 5), np.uint8))
        gl = np.clip(cv2.GaussianBlur(gl, (0, 0), 1.8) * c.get('gain', 1.4), 0, 1)
    else:   # 글자 덩어리 전체를 감싸는 둥근 빛판
        box = np.zeros((H, W), np.uint8)
        cv2.rectangle(box, (int(tx.min()) - mg, int(ty.min()) - mg), (int(tx.max()) + mg, int(ty.max()) + mg), 1, -1)
        gl = cv2.GaussianBlur(box.astype(np.float32), (0, 0), 2.0)
    if c.get('white'):   # 흰 글자 + 빛: 색은 원본에서 잰다(10/2 사용자 지적 — 글자 속·빛 색을 원본과 맞출 것)
        rgbj = jp[..., :3]
        core = (L > 200).astype(np.uint8)
        ring = (cv2.dilate(core, np.ones((5, 5), np.uint8)) - core).astype(bool)
        inkc = np.median(rgbj[core.astype(bool)], 0) if core.any() else np.array([255, 255, 255], np.float32)
        glc = np.median(rgbj[ring], 0) if ring.any() else np.array([80, 80, 80], np.float32)
        gw = np.clip(cv2.GaussianBlur(cv2.dilate(m, np.ones((3, 3), np.uint8)), (0, 0), 2.2) * 1.2, 0, 1)
        if c.get('plain'):
            gw = gw * 0
        a = gw[..., None]
        rgb = bg * (1 - a) + np.clip(glc * 1.1, 0, 255) * a   # 글자 바로 둘레가 원본 빛 색이 되게
        rgb = rgb * (1 - m[..., None]) + inkc * m[..., None]
        c = dict(c, color=tuple(int(v) for v in (c.get('color') or inkc)))
        v = rgb.mean(2)
        print('  원본 글자색', inkc.astype(int), '빛 색', glc.astype(int))
    else:
        v = bg + (glowmax - bg) * gl
        v = v * (1 - m) + c.get('ink', 0) * m
        if c.get('tint'):   # 빛판·글자 색을 원본에서 잼(10/2: 회색 가정 금지)
            rgbj = jp[..., :3]
            glc = np.median(rgbj[L >= np.percentile(L, 97)], 0)
            inner = cv2.dilate((L > 60).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & (L < 30)
            inkc = np.median(rgbj[inner], 0) if inner.any() else np.zeros(3, np.float32)
            bgc = np.median(np.concatenate([rgbj[0], rgbj[-1]]), 0)
            g3 = np.clip((gl * (glowmax - bg)) / max(glowmax - bg, 1), 0, 1)[..., None]
            if c.get('soft'):   # 원본처럼 글자 둘레로 넓고 부드럽게 퍼지는 빛(평평한 판 아님)
                near = np.clip(cv2.GaussianBlur(cv2.dilate(m, np.ones((5, 5), np.uint8)), (0, 0), 1.4) * 1.3, 0, 0.95)
                wide = np.clip(cv2.GaussianBlur(cv2.dilate(m, np.ones((9, 9), np.uint8)), (0, 0), 4.0) * 0.9, 0, 1)
                g3 = (1 - (1 - near) * (1 - wide * c.get('wide', 0.6)))[..., None]   # 획 둘레는 밝게, 바깥은 옅게 퍼짐
            rgb = bgc * (1 - g3) + glc * g3
            rgb = rgb * (1 - m[..., None]) + inkc * m[..., None]
            print('  원본 빛 색', glc.astype(int), '글자색', inkc.astype(int))
    out = np.zeros((H, W, 4), np.uint8)
    out[..., :3] = np.clip(v, 0, 255)[..., None]
    if c.get('white') or c.get('tint'):
        out[..., :3] = np.clip(rgb, 0, 255)
    elif c.get('color'):   # 색 글자: 획만 지정 색
        col = np.array(c['color'], np.float32)
        rgb2 = np.clip(v, 0, 255)[..., None] * (1 - m[..., None]) + col * m[..., None]
        out[..., :3] = np.clip(rgb2, 0, 255)
    out[..., 3] = 255
    Image.fromarray(out, 'RGBA').save(os.path.join(G, 'done', gid + '.png'))
    print(gid, '글자 상자', tx.min(), ty.min(), tx.max(), ty.max(), '바탕', bg, '빛 최대', glowmax)


if __name__ == '__main__':
    for g in sys.argv[1:]:
        make(g, CFG[g])
