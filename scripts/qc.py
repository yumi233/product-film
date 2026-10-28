"""Measured checks before delivery: frame jitter, audio noise/loudness, reference-image count.

    python3 qc.py jitter clip1.mp4 clip2.mp4 ...      # per clip: coefficient of variation of frame change, jumps, duplicates
    python3 qc.py audio film.mp4 [--compare old.mp4]  # loudness, LRA, low-frequency share, hiss, quietest 5 %
    python3 qc.py refs jobs.json                       # RunningHub jobs with more than 5 reference images (H3 runs out of memory)

Thresholds learned on a real film (see references/pitfalls.md):
- jitter: cv > 0.6 or more than one jump (> 2.5x median change) = visibly juddering; re-generate or smooth.
  Measure clips WITHOUT subtitles: subtitle fades look like jumps.
- audio: model-generated "ambience" is mostly < 120 Hz rumble plus hiss; a film should not sit near -16 LUFS with a
  floor close to its own RMS. Target about -18 LUFS, true peak <= -1.5 dBTP.
"""
import json, re, subprocess, sys
import numpy as np


def frame_diffs(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', 'fps=24,scale=240:135,format=gray', '-f', 'rawvideo', '-'],
                         capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, 135, 240).astype(np.float32)
    return np.abs(np.diff(a, axis=0)).mean((1, 2))


def jitter(paths):
    bad = 0
    for p in paths:
        d = frame_diffs(p)
        m = float(np.median(d)) + 1e-6
        mid = d[len(d) // 10: len(d) - len(d) // 10]           # eased starts/ends are slow on purpose
        cv, jumps, dup = float(np.std(d) / m), int((d > 2.5 * m).sum()), int((mid < 0.25 * m).sum())
        flag = 'JUDDER' if cv > 0.6 or jumps > 1 else ('dup' if dup > 2 else 'ok')
        bad += flag != 'ok'
        print(f'{flag:6s} cv {cv:4.2f} jumps {jumps:3d} dup {dup:3d}  {p}')
    return bad


def vol(path, af):
    out = subprocess.run(['ffmpeg', '-i', path, '-af', af + ',volumedetect' if af else 'volumedetect', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    return float(re.findall(r'mean_volume: (-?[\d.]+)', out)[-1])


def audio(path):
    e = subprocess.run(['ffmpeg', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    i = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', e)[-1]); lra = float(re.findall(r'LRA:\s+(-?[\d.]+) LU', e)[-1])
    tp = float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', e)[-1])
    full, low, hiss = vol(path, ''), vol(path, 'lowpass=f=100'), vol(path, 'highpass=f=5000')
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', '22050', '-f', 's16le', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float64) / 32768
    h = 11025
    db = np.array([20 * np.log10(np.sqrt((x[k:k + h] ** 2).mean()) + 1e-9) for k in range(0, len(x) - h, h)])
    r = dict(lufs=i, lra=lra, true_peak=tp, full_db=full, below_100hz_db=low, above_5khz_db=hiss,
             quietest5pct_db=round(float(np.percentile(db, 5)), 1), jumps_over_8db=int((np.abs(np.diff(db)) > 8).sum()))
    return r


def refs(jobs_path):
    jobs = json.load(open(jobs_path))
    jobs = jobs.get('jobs', jobs) if isinstance(jobs, dict) else jobs
    over = [(j.get('name') or j.get('id'), len(j.get('refs', []))) for j in jobs if len(j.get('refs', [])) > 5]
    for n, k in over:
        print(f'TOO MANY REFS {n}: {k} (max 5)')
    return len(over)


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == 'jitter':
        sys.exit(1 if jitter(args) else 0)
    elif cmd == 'audio':
        files = [args[0]] + ([args[args.index('--compare') + 1]] if '--compare' in args else [])
        for f in files:
            print(f, json.dumps(audio(f), ensure_ascii=False))
    elif cmd == 'refs':
        sys.exit(1 if refs(args[0]) else 0)
    else:
        sys.exit(__doc__)
