"""extract/{jp,us} 의 *SK_ASC* 파일을 전부 extract/dec/{jp,us} 로 해제(같은 상대경로)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skasc

for v in sys.argv[1:] or ['jp', 'us']:
    src = os.path.join('extract', v); n = 0
    for r, ds, fs in os.walk(src):
        for f in sorted(fs):
            p = os.path.join(r, f)
            with open(p, 'rb') as fp:
                if fp.read(8) != b'*SK_ASC*':
                    continue
            dst = os.path.join('extract', 'dec', v, os.path.relpath(p, src))
            if os.path.exists(dst):
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(skasc.decompress(open(p, 'rb').read())); n += 1
    print(v, n, flush=True)
