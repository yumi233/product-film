"""Per-line median pitch (Hz) and spectral centroid (Hz): a quick proxy for timbre drift."""
import sys, numpy as np
from scipy.io import wavfile
for p in sys.argv[1:]:
    sr, a = wavfile.read(p); a = a.astype(np.float64); a = a if a.ndim == 1 else a.mean(1); a /= np.abs(a).max() + 1e-9
    f0s, cents = [], []
    n = int(0.04 * sr)
    for i in range(0, len(a) - n, n // 2):
        x = a[i:i + n]
        if np.sqrt((x ** 2).mean()) < 0.05: continue
        c = np.correlate(x, x, 'full')[n - 1:]; lo, hi = int(sr / 300), int(sr / 60)
        k = lo + np.argmax(c[lo:hi])
        if c[k] > 0.3 * c[0]: f0s.append(sr / k)
        X = np.abs(np.fft.rfft(x * np.hanning(n))); f = np.fft.rfftfreq(n, 1 / sr); cents.append((X * f).sum() / X.sum())
    print(f"{p.split('/')[-1]:10s} F0 {np.median(f0s):6.1f}Hz  centroid {np.median(cents):6.0f}Hz")
