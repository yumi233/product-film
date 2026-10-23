"""Synthesised plucked-string score (guqin-like) placed on the edit's cue points.

Used by cut.py; can also render alone:  python3 score.py cues.json 42.5 out.wav
cues: [{"t": 0.3, "phrase": "open"}, {"t": 10.4, "phrase": "walk"}, ...]   (t in seconds on the final timeline)

Phrases (D major pentatonic, D E F# A B):
  open    low open string, long ring           -> film / act opening, a reveal
  shimmer two harmonics (泛音)                 -> title, mist, light
  stamp   single mid pluck                     -> seal, a cup set down, a part clicking into place
  walk    3-note phrase with a slide           -> camera arrives at a new scene / landmark
  busy    5 quick notes                        -> action montage (pour, whisk, assembly)
  low     one deep note                        -> weight, pause before silence
  chord   three rising harmonics               -> ending, product hero moment
Design rule: one phrase per landmark or cut; leave air between them; the drone pad is always under it.
"""
import json, sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve, butter, lfilter

SR = 44100
D2, E2, Fs2, A2, B2 = 73.42, 82.41, 92.5, 110.0, 123.47
PHRASES = {
    'open':    [(0.0, 'p', D2, 8, .75, .3, 0)],
    'shimmer': [(0.0, 'h', 587.3, 4, .25), (0.4, 'h', 880, 4, .18)],
    'stamp':   [(0.0, 'p', A2, 5, .5, .4, 0)],
    'walk':    [(0.0, 'p', A2 * 2, 5, .5, .5, 0), (0.5, 'p', B2 * 2, 5, .5, .5, 0), (1.1, 'p', Fs2 * 2, 5, .5, .5, .02)],
    'busy':    [(0.0, 'p', D2 * 2, 4, .5, .5, 0), (0.3, 'p', Fs2 * 2, 4, .5, .5, 0), (0.6, 'p', A2 * 2, 4, .5, .5, 0),
                (1.2, 'p', B2 * 2, 4, .5, .5, -.02), (2.0, 'p', E2 * 2, 4, .5, .5, .02)],
    'low':     [(0.0, 'p', D2, 6, .6, .3, 0)],
    'chord':   [(0.0, 'h', 587.3, 6, .2), (0.25, 'h', 880, 6, .2), (0.5, 'h', 1174.7, 6, .2)],
}


def render(cues, total, seed=11):
    rng = np.random.default_rng(seed); N = int((total + 3) * SR)
    def pluck(freq, dur, amp, bright, slide):
        n = int(dur * SR); p = int(SR / freq)
        buf = lfilter([1], [1, -bright], rng.uniform(-1, 1, p)); out = np.zeros(n)
        for k in range(n):
            out[k] = buf[k % p]; buf[k % p] = 0.4985 * (buf[k % p] + buf[(k + 1) % p])
        if slide:
            idx = np.cumsum(1 + slide * np.clip(np.arange(n) / SR - 0.25, 0, 1)); idx = idx[idx < n - 1]
            out = np.interp(idx, np.arange(n), out)
        out *= np.exp(-np.arange(len(out)) / SR * 0.9)
        b, a = butter(2, 2600 / (SR / 2)); out = lfilter(b, a, out)
        return amp * out / (np.abs(out).max() + 1e-9)
    def harmonic(freq, dur, amp):
        tt = np.arange(int(dur * SR)) / SR
        return amp * (np.sin(2 * np.pi * freq * tt) + 0.3 * np.sin(4 * np.pi * freq * tt)) * np.exp(-tt * 1.6) * (1 - np.exp(-tt * 300))
    music = np.zeros(N)
    def place(sig, at):
        i = int(at * SR); j = min(N, i + len(sig))
        if 0 <= i < N: music[i:j] += sig[:j - i]
    for c in cues:
        for ev in PHRASES[c['phrase']]:
            dt, kind = ev[0], ev[1]
            place(pluck(*ev[2:]) if kind == 'p' else harmonic(*ev[2:]), c['t'] + dt)
    tt = np.arange(N) / SR
    pad = np.sin(2 * np.pi * D2 * tt) + .5 * np.sin(2 * np.pi * A2 * tt) + .25 * np.sin(2 * np.pi * D2 * 2.002 * tt)
    music += pad * 0.05 * (0.6 + 0.4 * np.sin(2 * np.pi * tt / 11)) * np.clip(tt / 4, 0, 1)
    ir_t = np.arange(int(3.2 * SR)) / SR
    ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 2.2); ir[0] = 3
    wet = fftconvolve(music, ir)[:N]
    music = 0.5 * music + 0.5 * wet / (np.abs(wet).max() + 1e-9) * np.abs(music).max()
    music = music[:int(total * SR)]
    return music / (np.abs(music).max() + 1e-9)


if __name__ == '__main__':
    m = render(json.load(open(sys.argv[1])), float(sys.argv[2]))
    wavfile.write(sys.argv[3], SR, (m * 0.8 * 32767).astype(np.int16))
