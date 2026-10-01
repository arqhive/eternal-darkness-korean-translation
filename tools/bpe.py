"""Philip Gage 식 BPE(바이트 쌍 부호화) 해제. 텍스트 레코드 본문에 쓰인다."""


def decode(d, pos=0, limit=0x40000):
    """한 블록을 풀어 (결과, 다음 위치)를 돌려준다."""
    left = list(range(256)); right = [0] * 256
    code = 0
    while True:
        c = d[pos]; pos += 1
        if c > 127:
            code += c - 127; c = 0
        if code == 256:
            break
        for _ in range(c + 1):
            left[code] = d[pos]; pos += 1
            if code != left[code]:
                right[code] = d[pos]; pos += 1
            code += 1
        if code == 256:
            break
    size = d[pos] << 8 | d[pos + 1]; pos += 2
    out = bytearray(); stack = []
    end = pos + size
    while pos < end or stack:
        if stack:
            c = stack.pop()
        else:
            c = d[pos]; pos += 1
        if c == left[c]:
            out.append(c)
            if len(out) > limit:
                raise ValueError('BPE 결과가 너무 김(잘못된 블록)')
        else:
            stack.append(right[c]); stack.append(left[c])
            if len(stack) > 4096:
                raise ValueError('BPE 순환(잘못된 블록)')
    return bytes(out), pos


def encode(data):
    """Gage BPE 한 블록으로 압축(본문 65535바이트 이하). 쓰지 않는 바이트 값을 쌍 코드로 쓴다."""
    assert len(data) <= 0xFFFF
    buf = list(data)
    left = list(range(256)); right = [0] * 256
    used = set(buf)
    free = [c for c in range(256) if c not in used]
    for code in free:
        cnt = {}
        for a, b in zip(buf, buf[1:]):
            cnt[(a, b)] = cnt.get((a, b), 0) + 1
        if not cnt:
            break
        pair, n = max(cnt.items(), key=lambda x: x[1])
        if n < 3:
            break
        out = []; i = 0
        while i < len(buf):
            if i + 1 < len(buf) and (buf[i], buf[i + 1]) == pair:
                out.append(code); i += 2
            else:
                out.append(buf[i]); i += 1
        buf = out; left[code], right[code] = pair
    # 쌍 표 쓰기(Gage 형식): 바이트>127 = 그만큼 건너뛴 뒤 항목 1개, 아니면 그 수+1개 항목
    def ent(k):
        return bytes([left[k]]) if left[k] == k else bytes([left[k], right[k]])
    tbl = bytearray(); c = 0
    while c < 256:
        s = c
        while c < 256 and left[c] == c and c - s < 128:
            c += 1
        if c > s:
            tbl.append(127 + c - s)
            if c == 256:
                break
            tbl += ent(c); c += 1
            continue
        r = c
        while r < 256 and left[r] != r and r - c < 128:
            r += 1
        tbl.append(r - c - 1)
        for k in range(c, r):
            tbl += ent(k)
        c = r
    return bytes(tbl) + bytes([len(buf) >> 8, len(buf) & 0xFF]) + bytes(buf)
