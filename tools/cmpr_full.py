"""CMPR(GC DXT1) 전체 인코더(numpy). 폭·높이가 8의 배수가 아니면 8×8 덩어리 단위로 채운다(패딩은 가장자리 복제).
encode(img_rgba_uint8 (H,W,4), 저장 좌표 = TPL 순서) -> bytes
- 끝점: 4×4 칸 색의 주성분 축 위 최솟값·최댓값, 최소제곱으로 2번 다듬음
- 칸 안에 투명(α<128)이 있으면 3색+투명 모드"""
import numpy as np


def _to565(c):
    c = np.clip(np.rint(c), 0, 255).astype(np.int32)
    return (c[..., 0] >> 3) << 11 | (c[..., 1] >> 2) << 5 | (c[..., 2] >> 3)


def _from565(v):
    r = (v >> 11) & 31; g = (v >> 5) & 63; b = v & 31
    return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], -1).astype(np.float32)


def _blocks(img):
    H, W = img.shape[:2]
    H8, W8 = -(-H // 8) * 8, -(-W // 8) * 8
    p = np.pad(img, ((0, H8 - H), (0, W8 - W), (0, 0)), mode='edge')
    # (by, bx, sub(2x2), 16, 4): 8x8 덩어리 안 4x4 칸 순서 = 왼위, 오위, 왼아래, 오아래
    t = p.reshape(H8 // 8, 2, 4, W8 // 8, 2, 4, 4).transpose(0, 3, 1, 4, 2, 5, 6)
    return t.reshape(H8 // 8, W8 // 8, 4, 16, 4), H8, W8


def encode(img):
    img = np.asarray(img, np.uint8)
    B, H8, W8 = _blocks(img)
    sh = B.shape[:3]
    px = B.reshape(-1, 16, 4).astype(np.float32)
    rgb, a = px[..., :3], px[..., 3]
    trans = (a < 128)
    anyt = trans.any(1)
    allt = trans.all(1)
    w = (~trans).astype(np.float32)
    wsum = np.maximum(w.sum(1, keepdims=True), 1)
    mean = (rgb * w[..., None]).sum(1) / wsum
    d = (rgb - mean[:, None]) * w[..., None]
    cov = np.einsum('nki,nkj->nij', d, d)
    axis = np.ones((len(px), 3), np.float32)
    for _ in range(8):
        axis = np.einsum('nij,nj->ni', cov, axis)
        axis /= np.maximum(np.linalg.norm(axis, axis=1, keepdims=True), 1e-6)
    proj = np.einsum('nki,ni->nk', rgb - mean[:, None], axis)
    big = 1e9
    pmin = np.where(w > 0, proj, big).min(1); pmax = np.where(w > 0, proj, -big).max(1)
    pmin = np.where(allt, 0, pmin); pmax = np.where(allt, 0, pmax)
    e0 = mean + axis * pmax[:, None]; e1 = mean + axis * pmin[:, None]
    for _ in range(2):   # 최소제곱 다듬기(4색 모드 기준)
        span = np.maximum(pmax - pmin, 1e-6)
        t = np.clip((proj - pmin[:, None]) / span[:, None], 0, 1)
        t = np.where(anyt[:, None], np.rint(t * 2) / 2, np.rint(t * 3) / 3)
        A = np.stack([t, 1 - t], -1) * w[..., None]
        ata = np.einsum('nki,nkj->nij', A, A) + np.eye(2) * 1e-4
        atb = np.einsum('nki,nkc->nic', A, rgb * w[..., None])
        sol = np.linalg.solve(ata, atb)
        e0, e1 = sol[:, 0], sol[:, 1]
        proj = np.einsum('nki,ni->nk', rgb - e1[:, None], (e0 - e1) / np.maximum(np.linalg.norm(e0 - e1, axis=1, keepdims=True), 1e-6))
        pmin = np.zeros(len(px)); pmax = np.linalg.norm(e0 - e1, axis=1)
    c0 = _to565(e0); c1 = _to565(e1)
    # 4색: c0 > c1, 3색+투명: c0 <= c1
    hi, lo = np.maximum(c0, c1), np.minimum(c0, c1)
    four_c0 = np.where(hi == lo, np.where(hi < 0xFFFF, hi + 1, hi), hi)
    four_c1 = np.where(hi == lo, np.where(hi < 0xFFFF, lo, lo - 1), lo)
    C0 = np.where(anyt, lo, four_c0); C1 = np.where(anyt, hi, four_c1)
    p0, p1 = _from565(C0), _from565(C1)
    pal4 = np.stack([p0, p1, (2 * p0 + p1) / 3, (p0 + 2 * p1) / 3], 1)
    pal3 = np.stack([p0, p1, (p0 + p1) / 2, np.full_like(p0, 1e6)], 1)
    pal = np.where(anyt[:, None, None], pal3, pal4)
    dist = ((rgb[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(-1)
    idx = dist.argmin(-1)
    idx = np.where(anyt[:, None] & trans, 3, idx)
    bits = np.zeros(len(px), np.uint64)
    for k in range(16):
        bits = bits << np.uint64(2) | idx[:, k].astype(np.uint64)
    out = np.zeros((len(px), 8), np.uint8)
    out[:, 0] = C0 >> 8; out[:, 1] = C0 & 255; out[:, 2] = C1 >> 8; out[:, 3] = C1 & 255
    for i in range(4):
        out[:, 4 + i] = ((bits >> np.uint64(8 * (3 - i))) & np.uint64(255)).astype(np.uint8)
    out[allt] = np.array([0, 0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF], np.uint8)
    return out.reshape(sh + (8,)).tobytes()
