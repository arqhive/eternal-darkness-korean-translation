"""두 판(일본판·영어판)의 같은 그림에서 글자 자리가 다를 때, 픽셀마다 '글자 기운'이 적은 쪽을 골라 바탕을 되살린다.
글자 기운 = 주변 중앙값(9px)과의 차를 흐린 값. 둘 다 글자면 인페인팅. 작은 질감 그림용(g165·g166). LaMa 전 임시안.
함수 pick2(a, b, box) → (바탕, 둘 다 글자 마스크)"""
import numpy as np
import cv2


def textness(a8, k=9):
    med = cv2.medianBlur(a8, k).astype(np.float32)
    return cv2.GaussianBlur(np.abs(a8.astype(np.float32) - med).sum(2), (0, 0), 1.2)


def pick2(a8, b8, thr=40):
    ta, tb = textness(a8), textness(b8)
    d = np.abs(a8.astype(int) - b8.astype(int)).sum(2) > 24
    d = cv2.dilate(d.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    out = a8.copy()
    use_b = d & (tb < ta)
    out[use_b] = b8[use_b]
    both = d & (np.minimum(ta, tb) > thr)
    out = cv2.inpaint(out, cv2.dilate(both.astype(np.uint8), np.ones((3, 3), np.uint8)), 3, cv2.INPAINT_TELEA)
    return out, both


def lama_fill(a8, b8):
    """10/2: 두 판이 다른 곳(어느 쪽이든 글자·번짐) 전체를 LaMa로 메움"""
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from lama import inpaint
    d = np.abs(a8.astype(int) - b8.astype(int)).sum(2) > 24
    d = cv2.dilate(d.astype(np.uint8), np.ones((5, 5), np.uint8))
    return inpaint(a8, d), d.astype(bool)
