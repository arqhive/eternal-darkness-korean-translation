"""GPT 가 다시 그린 그림을 게임 크기로 맞춰 반영하고 비교 시트를 만든다(목록은 work/GPT/목록.json, gpt_prepare 가 만듦).

  work/GPT/결과/<번호>.png
    g###  → work/gfx/done/<번호>.png (바꾸기 전 파일은 work/GPT/이전/ 에 보관)
            g126(지금 영어판 교체)은 plan.tsv 를 「번역 / 확정(GPT)」으로 바꾼다(이전 plan 은 work/GPT/이전/plan.tsv)
    cover → work/gfx/done/cover.png (tools/cin_cover.py 가 있으면 이걸 표지로 씀, 북미판 대신)
  비교 시트: work/GPT/비교/<번호>.png (원본 | 현재 | GPT 반영, GPT 반영은 CMPR 로 바꿨다 푼 모양)

맞추는 방식(결과가 이미 게임 크기면 그대로): 그림 전체를 게임 크기로(LANCZOS). 원본에 투명이 있으면 투명도는 원본 것.
사용: python tools/gpt_import.py                결과 폴더에 있는 것 전부
      python tools/gpt_import.py g014 cover      번호 지정
      python tools/gpt_import.py --dry …        비교 시트만 만들고 아무것도 바꾸지 않음
반영 뒤 빌드(build_full → build_iso)는 따로 한다.
"""
import json
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cmpr_full
import tpl

ROOT = os.path.normpath(os.path.join(HERE, '..'))
GPT = os.path.join(ROOT, 'work', 'GPT')
G = os.path.join(ROOT, 'work', 'gfx')


def premul_resize(im, size):
    a = np.asarray(im.convert('RGBA'), np.float32) / 255
    a[..., :3] *= a[..., 3:4]
    ch = [Image.fromarray(a[..., i], 'F').resize(size, Image.LANCZOS) for i in range(4)]
    r = np.stack([np.asarray(c, np.float32) for c in ch], -1).clip(0, 1)
    r[..., :3] = np.where(r[..., 3:4] > 1e-4, r[..., :3] / np.maximum(r[..., 3:4], 1e-4), 0)
    return Image.fromarray((r * 255 + .5).clip(0, 255).astype(np.uint8), 'RGBA')


def fit(gpt, orig, transparent):
    w, h = orig.size
    g = gpt.convert('RGBA')
    gr, orr = g.width / g.height, w / h
    if abs(gr - orr) / orr > 0.02:
        print('  경고: 비율이 다름 GPT %.3f / 원본 %.3f — 그림 전체를 게임 크기로 줄임' % (gr, orr))
    if g.size != (w, h):
        g = premul_resize(g, (w, h))
    a = np.asarray(g).copy()
    own = gpt.mode in ('RGBA', 'LA', 'PA') and np.asarray(gpt.convert('RGBA'))[..., 3].min() < 250
    if transparent and not own:
        a[..., 3] = np.asarray(orig.convert('RGBA'))[..., 3]
    elif not transparent:
        a[..., 3] = 255
    # 투명 그림인데 GPT 그림에 투명도가 있으면 그것을 씀(10/12: 글자가 바뀐 글자 조각에 원본 투명도를 씌우면 깨짐)
    return Image.fromarray(a, 'RGBA')


def roundtrip(img):
    """CMPR 로 바꿨다 푼 모양(게임에서 보이는 것)."""
    a = np.asarray(img.convert('RGBA'))
    enc = cmpr_full.encode(np.ascontiguousarray(a))
    return tpl.decode(enc, 0, img.width, img.height, 14).convert('RGBA')


def sheet(job, orig, cur, new, path):
    F = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 16)
    ims = [orig, cur, new]; labs = ['일본판 원본', '지금', 'GPT 반영(게임 형식)']
    s = 1 if max(job['w'], job['h']) >= 320 else (2 if max(job['w'], job['h']) >= 160 else 4)
    W, H = job['w'] * s, job['h'] * s
    out = Image.new('RGB', (W * 3 + 40, H + 60), (34, 34, 40)); d = ImageDraw.Draw(out)
    d.text((10, 6), '%s %s  %d×%d' % (job['id'], job['title'], job['w'], job['h']), font=F, fill=(255, 214, 120))
    for i, (im, lab) in enumerate(zip(ims, labs)):
        x = 10 + i * (W + 10)
        bg = Image.new('RGBA', im.size, (60, 60, 66, 255)); bg.alpha_composite(im.convert('RGBA'))
        out.paste(bg.convert('RGB').resize((W, H), Image.NEAREST), (x, 50))
        d.text((x, 28), lab, font=F, fill=(200, 200, 210))
    out.save(path)


def set_plan(gid):
    p = os.path.join(G, 'plan.tsv')
    rows = [l.rstrip('\n').split('\t') for l in open(p, encoding='utf-8')]
    os.makedirs(os.path.join(GPT, '이전'), exist_ok=True)
    if not os.path.exists(os.path.join(GPT, '이전', 'plan.tsv')):
        shutil.copy2(p, os.path.join(GPT, '이전', 'plan.tsv'))
    for r in rows:
        if r[0] == gid:
            r[5] = '번역'; r[6] = ''; r[-1] = '확정(GPT)'
    open(p, 'w', encoding='utf-8', newline='\n').write('\n'.join('\t'.join(r) for r in rows) + '\n')


def main(args):
    dry = '--dry' in args
    want = [a for a in args if not a.startswith('--')]
    jobs = {j['id']: j for j in json.load(open(os.path.join(GPT, '목록.json'), encoding='utf-8'))}
    res = os.path.join(GPT, '결과')
    ids = want or sorted(f[:-4] for f in os.listdir(res) if f.lower().endswith('.png') and f[:-4] in jobs)
    if not ids:
        print('결과 폴더에 반영할 그림이 없음'); return
    done = []
    for gid in ids:
        job = jobs[gid]
        p = os.path.join(res, gid + '.png')
        if not os.path.exists(p):
            print(gid, '결과 없음'); continue
        orig = Image.open(os.path.join(GPT, '원본', '%s_원본_%dx%d.png' % (gid, job['w'], job['h']))).convert('RGBA')
        cur = Image.open(os.path.join(GPT, '참고', job['ref'])).convert('RGBA')
        new = fit(Image.open(p), orig, job['transparent'])
        sheet(job, orig, cur, roundtrip(new), os.path.join(GPT, '비교', gid + '.png'))
        if not dry:
            dst = os.path.join(G, 'done', gid + '.png')
            if os.path.exists(dst):
                os.makedirs(os.path.join(GPT, '이전'), exist_ok=True)
                bk = os.path.join(GPT, '이전', gid + '.png')
                if not os.path.exists(bk):
                    shutil.copy2(dst, bk)
            new.save(dst)
            if gid == 'g126':
                set_plan(gid)
        done.append(gid)
        print(gid, '비교 시트' if dry else '반영 + 비교 시트', os.path.join(GPT, '비교', gid + '.png'))
    print('%d개 %s' % (len(done), '(시트만)' if dry else '반영 — 빌드는 따로'))


if __name__ == '__main__':
    main(sys.argv[1:])
