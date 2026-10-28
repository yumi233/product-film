"""Final sound mix: narration track + music sections + real ambience beds + one-shot effects.

    python3 mix.py mix.json
mix.json (seconds on the final timeline; paths relative to the JSON):
{
  "video": "cut.mp4",              # picture; its audio must be narration only (cut.py with source_audio "mute", music [])
  "output": "film.mp4",
  "music": [{"path": "music/a.mp3", "start": 0, "from": 0, "length": 50, "fade_in": 2, "fade_out": 4},
            {"path": "music/b.mp3", "start": 46, "from": 0, "fade_in": 3, "fade_out": 5}],
  "beds":  [{"path": "amb/rain.mp3", "start": 120.4, "end": 131.0, "db": 0}],      # real recordings, per scene
  "fx":    [{"path": "amb/pour.mp3", "at": 33.2, "db": 0}],
  "music_db": -26, "bed_db": -38, "fx_db": -30,   # base RMS levels (dBFS) before the final gain
  "duck_db": -9,                                   # music under narration
  "target_lufs": -18, "true_peak": -1.5
}
Why this way (measured on a real film): model-generated clip audio is rumble + hiss, so it is not used; a sidechain
compressor makes the music "breathe", so the music follows a smoothed envelope instead; dynamic loudnorm lifts the
noise floor, so the final gain is one linear step from a two-pass loudness measurement.
"""
import json, os, subprocess, sys, tempfile
import numpy as np
from scipy.io import wavfile

SR = 44100
T = tempfile.mkdtemp(prefix='mix_')


def load(path, start=0.0, length=None, hp=None, lp=None):
    af = ['aresample=44100', 'aformat=channel_layouts=stereo'] + ([f'highpass=f={hp}'] if hp else []) + ([f'lowpass=f={lp}'] if lp else [])
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(start)] + (['-t', str(length)] if length else []) +
                   ['-i', path, '-af', ','.join(af), f'{T}/x.wav'], check=True)
    return wavfile.read(f'{T}/x.wav')[1].astype(np.float64) / 32768


def rms_db(x):
    return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-12)


def fade(x, fi, fo):
    e = np.ones(len(x)); a, b = int(fi * SR), int(fo * SR)
    if a: e[:a] = np.linspace(0, 1, min(a, len(x)))[:len(e[:a])]
    if b: e[-b:] = np.minimum(e[-b:], np.linspace(1, 0, b)[-len(e[-b:]):])
    return x * e[:, None]


def place(buf, x, t0):
    i = int(t0 * SR); j = min(len(buf), i + len(x))
    if 0 <= i < len(buf): buf[i:j] += x[:j - i]


def main(cfg_path):
    C = json.load(open(cfg_path)); base = os.path.dirname(os.path.abspath(cfg_path))
    P = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    video = P(C['video'])
    total = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', video],
                                 capture_output=True, text=True).stdout)
    N = int(total * SR)
    vo = np.zeros((N, 2)); x = load(video); vo[:min(N, len(x))] = x[:N]
    env = np.convolve(np.abs(vo).max(1), np.ones(int(.05 * SR)) / int(.05 * SR), 'same')
    g = np.where(env > 10 ** (-40 / 20), 10 ** (C.get('duck_db', -9) / 20), 1.0)
    k = int(.6 * SR); g = np.convolve(np.pad(g, (k, k), mode='edge'), np.ones(k) / k, 'same')[k:-k]

    mus = np.zeros((N, 2))
    for m in C.get('music', []):
        length = m.get('length', total - m['start'])
        place(mus, fade(load(P(m['path']), m.get('from', 0), length, hp=60), m.get('fade_in', 2), m.get('fade_out', 4)), m['start'])
    if mus.any():
        mus *= 10 ** ((C.get('music_db', -26) - rms_db(mus[mus.any(1)])) / 20)
    mus *= g[:, None]

    amb = np.zeros((N, 2)); cache = {}
    for b in C.get('beds', []):
        if b['path'] not in cache:
            y = load(P(b['path']), hp=120, lp=9000); cache[b['path']] = y * 10 ** ((C.get('bed_db', -38) - rms_db(y)) / 20)
        y = cache[b['path']]; n = int((b['end'] - b['start'] + 1.0) * SR)
        if len(y) < n: y = np.tile(y, (n // len(y) + 1, 1))
        place(amb, fade(y[:n] * 10 ** (b.get('db', 0) / 20), .8, 1.0), b['start'] - .3)
    for f in C.get('fx', []):
        y = load(P(f['path']), hp=150)[:int(f.get('max', 3.5) * SR)]
        place(amb, fade(y * 10 ** ((C.get('fx_db', -30) + f.get('db', 0) - rms_db(y)) / 20), .1, .8), f['at'])

    mix = vo * .9 + mus + amb
    e = int((total - 2.5) * SR); mix[e:] *= np.linspace(1, 0, N - e)[:, None]
    wavfile.write(f'{T}/mix.wav', SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
    tgt, tp = C.get('target_lufs', -18), C.get('true_peak', -1.5)
    s = subprocess.run(['ffmpeg', '-i', f'{T}/mix.wav', '-af', f'loudnorm=I={tgt}:TP={tp}:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    j = json.loads(s[s.rfind('{'):s.rfind('}') + 1])
    gain = tgt - float(j['input_i'])
    if float(j['input_tp']) + gain > tp:
        gain = tp - float(j['input_tp'])
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-i', f'{T}/mix.wav', '-map', '0:v', '-map', '1:a',
                    '-af', f'volume={gain:.2f}dB', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-shortest', P(C['output'])], check=True)
    print('done', P(C['output']), round(total, 1), 'gain', round(gain, 1))


if __name__ == '__main__':
    main(sys.argv[1])
