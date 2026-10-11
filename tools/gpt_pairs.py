"""GPT 반영 전후(지금 → GPT) 문구 대조용 모음 시트. python gpt_pairs.py <이름> <번호...> → work/GPT/비교/_묶음_<이름>.png"""
import os, sys
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GPT = os.path.join(ROOT, 'work', 'GPT')
name, ids = sys.argv[1], sys.argv[2:]
F = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 18)
rows = []
for gid in ids:
    a = Image.open(os.path.join(GPT, '이전', gid + '.png')).convert('RGBA') if os.path.exists(os.path.join(GPT, '이전', gid + '.png')) \
        else Image.open(os.path.join(GPT, '참고', gid + '_현재판.png')).convert('RGBA')
    b = Image.open(os.path.join(ROOT, 'work', 'gfx', 'done', gid + '.png')).convert('RGBA')
    s = max(1, min(4, 420 // max(a.width, a.height)))
    rows.append((gid, a.resize((a.width * s, a.height * s), Image.NEAREST), b.resize((b.width * s, b.height * s), Image.NEAREST)))
W = max(r[1].width for r in rows) * 2 + 30
H = sum(r[1].height + 34 for r in rows)
out = Image.new('RGB', (W, H), (34, 34, 40)); d = ImageDraw.Draw(out); y = 0
for gid, a, b in rows:
    d.text((6, y + 4), gid + '  지금 → GPT', font=F, fill=(255, 214, 120))
    for i, im in enumerate((a, b)):
        bg = Image.new('RGBA', im.size, (70, 70, 76, 255)); bg.alpha_composite(im)
        out.paste(bg.convert('RGB'), (10 + i * (im.width + 10), y + 30))
    y += a.height + 34
p = os.path.join(GPT, '비교', '_묶음_%s.png' % name); out.save(p); print(p, out.size)
