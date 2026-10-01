"""글자가 바탕을 넓게 덮은 그림의 바탕 메우기(간단한 조각 이어 붙이기).
마스크 안을 B×B 조각 단위로, 이미 알려진 둘레 픽셀과 가장 잘 맞는 '깨끗한 곳' 조각을 골라 붙인다(겹침 3px 섞기).
LaMa 같은 학습형 복원을 쓰기 전 임시안. 함수 quilt(img, mask) → img"""
import numpy as np
import cv2


def quilt(img, mask, B=10, OV=3, cand=600, seed=3):
    img = img.astype(np.float32).copy()
    H, W = mask.shape
    known = (mask == 0)
    rng = np.random.default_rng(seed)
    src_ok = cv2.erode(known.astype(np.uint8), np.ones((B + 2 * OV + 2,) * 2, np.uint8)) > 0
    sy, sx = np.where(src_ok[OV:H - B - OV, OV:W - B - OV])
    sy, sx = sy + OV, sx + OV
    if len(sy) == 0:
        raise ValueError('깨끗한 바탕 조각이 없음')
    pick = rng.choice(len(sy), min(cand, len(sy)), replace=False)
    sy, sx = sy[pick], sx[pick]
    S = B + 2 * OV
    srcs = np.stack([img[y - OV:y - OV + S, x - OV:x - OV + S] for y, x in zip(sy, sx)])
    done = known.copy()
    ys, xs = np.where(mask > 0)
    for by in range(ys.min() // B * B, ys.max() + 1, B):
        for bx in range(xs.min() // B * B, xs.max() + 1, B):
            if not mask[by:by + B, bx:bx + B].any():
                continue
            y0, x0 = by - OV, bx - OV
            if y0 < 0 or x0 < 0 or y0 + S > H or x0 + S > W:
                continue
            tgt = img[y0:y0 + S, x0:x0 + S]
            w = done[y0:y0 + S, x0:x0 + S].astype(np.float32)
            if w.sum() < 5:
                k = rng.integers(len(srcs))
            else:
                err = (((srcs - tgt[None]) ** 2).sum(3) * w[None]).sum((1, 2)) / w.sum()
                best = np.argsort(err)[:5]
                k = rng.choice(best)
            patch = srcs[k]
            # 이미 알려진 픽셀은 둘레 쪽으로 섞고, 조각 가운데는 새 조각
            a = np.ones((S, S), np.float32)
            a[:OV, :] *= np.linspace(0, 1, OV + 2)[1:-1][:, None]
            a[-OV:, :] *= np.linspace(1, 0, OV + 2)[1:-1][:, None]
            a[:, :OV] *= np.linspace(0, 1, OV + 2)[1:-1][None, :]
            a[:, -OV:] *= np.linspace(1, 0, OV + 2)[1:-1][None, :]
            a = np.where(w > 0, a, 1.0)
            m = mask[y0:y0 + S, x0:x0 + S] > 0
            a = np.where(m | (w == 0), a, a * 0.5)
            img[y0:y0 + S, x0:x0 + S] = tgt * (1 - a[..., None]) + patch * a[..., None]
            done[y0:y0 + S, x0:x0 + S] = True
    return np.clip(img, 0, 255).astype(np.uint8)
