"""영상 글자 조사: 일본판 fmv/*.avi 마다 2초 간격 프레임을 모아 한 장(6열)으로 → work/fmv/<이름>.jpg

사용: python fmv_frames.py <ffmpeg.exe 경로>
"""
import glob
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def main(ff):
    ff = os.path.abspath(ff)  # Windows subprocess 는 상대 경로 실행 파일을 못 찾음
    out = os.path.join(ROOT, 'work', 'fmv'); os.makedirs(out, exist_ok=True)
    # 폴더 이름의 [GC] 를 glob 이 패턴으로 읽지 않도록 escape
    for p in sorted(glob.glob(os.path.join(glob.escape(os.path.join(ROOT, 'extract', 'jp', 'fmv')), '*.avi'))):
        name = os.path.splitext(os.path.basename(p))[0]
        dst = os.path.join(out, name + '.jpg')
        # 2초마다 1장, 가로 256px, 6열 타일(최대 60장 = 2분)
        cmd = [ff, '-v', 'error', '-y', '-i', p, '-vf', 'fps=1/2,scale=256:-1,tile=6x10:padding=2', '-frames:v', '1', '-q:v', '4', dst]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        dur = subprocess.run([ff, '-i', p], capture_output=True, text=True, encoding='utf-8', errors='replace').stderr
        d = [l.strip() for l in dur.splitlines() if 'Duration' in l]
        print(name, 'OK' if r.returncode == 0 else 'ERR ' + r.stderr[:200], d[0][:30] if d else '')


if __name__ == '__main__':
    main(sys.argv[1])
