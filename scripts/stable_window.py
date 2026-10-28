"""For each clip, find the steadiest window of a given length (speed 1.0) inside an allowed range.

    python3 stable_window.py shots.json out.json
shots.json: [{"shot", "path", "len", "lo"?, "hi"?}]  (seconds; lo/hi bound the usable part of the source)
Score per window = 10 * sudden jumps + coefficient of variation of frame-to-frame change
(a smooth camera move has an even per-frame change; jitter and jumps make it uneven).
Writes the same list with "trim", "end" and the score; prints a table.
"""
import json, subprocess, sys
import numpy as np

W, H = 240, 135


def frames(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'fps=24,scale={W}:{H},format=gray',
                          '-f', 'rawvideo', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)


def best_window(path, length, lo=0.0, hi=None):
    f = frames(path)
    d = np.abs(np.diff(f, axis=0)).mean((1, 2))
    n = int(round(length * 24))
    a = int(lo * 24)
    b = len(d) - n if hi is None else min(len(d) - n, int(hi * 24) - n)
    best = None
    for s in range(a, max(a, b) + 1, 2):
        w = d[s:s + n]
        if len(w) < n:
            break
        m = np.median(w) + 1e-6
        score = 10 * int((w > 2.2 * m).sum()) + float(np.std(w) / m)
        if best is None or score < best[0]:
            best = (score, s)
    score, s = best
    return round(s / 24, 2), round((s + n) / 24, 2), round(score, 2)


if __name__ == '__main__':
    shots = json.load(open(sys.argv[1]))
    for sh in shots:
        if sh.get('still'):
            continue
        t, e, sc = best_window(sh['path'], sh['len'], sh.get('lo', 0.0), sh.get('hi'))
        sh.update(trim=t, end=e, score=sc)
        print(f"{sh['shot']:5s} {sh['path'].split('/')[-1][:24]:24s} {t:5.2f}-{e:5.2f}  score {sc}")
    json.dump(shots, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
