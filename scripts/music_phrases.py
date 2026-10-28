"""Find phrase entries in a music track so chapter starts can land on them.

    python3 music_phrases.py track.mp3 [--gap 3]
Prints the loudness every 5 s and the onset times (a 0.5 s window at least 6 dB above the previous 2 s, louder than
-40 dBFS, onsets at least --gap seconds apart). Feed the onsets to mix/cut planning: stretch an empty shot before each
chapter so the chapter's first shot starts on the nearest onset.
"""
import subprocess, sys
import numpy as np


def onsets(path, gap=3.0):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', '11025', '-f', 's16le', '-'], capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float64) / 32768
    h = 11025 // 2
    db = 20 * np.log10(np.array([np.sqrt((a[i:i + h] ** 2).mean()) + 1e-12 for i in range(0, len(a) - h, h)]))
    on = [i * 0.5 for i in range(4, len(db)) if db[i] - db[i - 4:i].mean() > 6 and db[i] > -40]
    out = []
    for t in on:
        if not out or t - out[-1] > gap:
            out.append(t)
    return db, out


if __name__ == '__main__':
    gap = float(sys.argv[sys.argv.index('--gap') + 1]) if '--gap' in sys.argv else 3.0
    db, out = onsets(sys.argv[1], gap)
    print('dB every 5 s:', ' '.join('%d' % x for x in [db[i:i + 10].mean() for i in range(0, len(db), 10)]))
    print('onsets:', out)
