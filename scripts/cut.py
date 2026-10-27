"""Rough cut from one JSON config: chained clips + score + narration + ambience + title/seal + subtitles.

    python3 cut.py act1.json

Config (paths relative to the JSON file; times "at" are seconds inside a segment; seg 0 is the intro still if any):
{
  "output": "videos/act1_rough.mp4",
  "intro":   {"image": "frames/P0.jpg", "seconds": 4.5, "xfade": 0.5},           # optional still opener
  "clips":   [{"path": "videos/raw/1-1.mp4", "speed": 1.8, "trim": 0, "end": 8.5}, ...],  # trim/end: keep source seconds trim..end (cut flawed parts)
  "align":   true,      # start each clip at the frame that best matches the previous clip's last frame
  "xfade":   0.25,      # crossfade between chained clips (0.25 hides tiny position jumps; 0.04 ~= hard cut)
  "fade":    [1.0, 1.5],
  "title":   {"seg": 0, "at": 0.6, "until": 4.3, "zh": "节序", "en": "", "style": "vertical",  # or "center"
              "x": 1640, "y": 250, "size": 170, "seal": true},
  "vo":      {"dir": "audio/vo", "tempo": 1.0,
              "lines": [{"id": "L1", "seg": 2, "at": 0.8, "zh": "竹有节，", "en": "Bamboo grows in nodes,"}, ...]},
  # User audio can replace dir/id.wav with a per-line "path": "audio/narration.m4a".
  "music":   [{"seg": 0, "at": 0.3, "phrase": "open"}, ...],                      # phrases: see score.py
  "source_audio": "mute",  # use verified_ambience only after auditioning for unwanted speech
  "ambience": 0.3       # level of retained, verified source ambience
}
Also writes <output>_score.wav. Subtitles: white Songti zh over serif en, soft shadow, gentle dark gradient below.
"""
import json, os, subprocess, sys, tempfile
import numpy as np
from scipy.io import wavfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score
from audio_policy import narration_source, source_audio_mode, validate_audio_inputs

W, H, FPS, SR = 1920, 1080, 24, 44100
SONG = '/System/Library/Fonts/Supplemental/Songti.ttc'
BASK = '/System/Library/Fonts/Supplemental/Baskerville.ttc'


def sh(*a): subprocess.run(a, check=True, capture_output=True)
def dur(p): return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p],
                                        capture_output=True, text=True).stdout)
def find_font(name):
    r = subprocess.run(['find', '/System/Library/AssetsV2', '/System/Library/Fonts', '-name', name], capture_output=True, text=True)
    hits = r.stdout.split(); return hits[0] if hits else SONG
def lowres(path, start, n):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{max(0, start)}', '-i', path, '-vf', 'scale=96:54,format=gray',
                        '-frames:v', str(n), '-f', 'rawvideo', '-'], capture_output=True).stdout
    return np.frombuffer(r, np.uint8).reshape(-1, 54, 96).astype(np.float32)


def main(cfg_path):
    with open(cfg_path) as config_file:
        C = json.load(config_file)
    base = os.path.dirname(os.path.abspath(cfg_path))
    validate_audio_inputs(C, base)  # ask for missing user narration before encoding the video
    P = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    out = P(C['output']); T = tempfile.mkdtemp(prefix='cut_'); os.makedirs(os.path.dirname(out), exist_ok=True)

    # 1. segments ------------------------------------------------------------
    segs, xfs = [], []
    if C.get('intro'):
        it = C['intro']
        sh('ffmpeg', '-y', '-v', 'error', '-loop', '1', '-framerate', str(FPS), '-t', str(it['seconds']), '-i', P(it['image']),
           '-vf', f'scale={W}:{H},format=yuv420p', '-c:v', 'libx264', '-crf', '16', f'{T}/v0.mp4')
        segs.append({'v': f'{T}/v0.mp4', 'a': None, 'd': it['seconds']}); xfs.append(it.get('xfade', 0.5))
    prev = None
    for k, c in enumerate(C['clips']):
        src, sp, st = P(c['path']), c.get('speed', 1.0), c.get('trim', 0.0)
        if C.get('align', True) and prev:
            last = lowres(prev, dur(prev) - 0.1, 1)[0]; cand = lowres(src, 0, 48)
            st = int(np.argmin(((cand - last) ** 2).mean((1, 2)))) / 24
        i = len(segs)
        lim = ['-t', f"{c['end'] - st}"] if c.get('end') else []  # end: keep source up to this second (cut flawed tail)
        sh('ffmpeg', '-y', '-v', 'error', '-ss', f'{st}', *lim, '-i', src, '-vf',
           f'setpts=PTS/{sp},fps={FPS},scale={W}:-2:flags=lanczos,crop={W}:{H},format=yuv420p', '-an', '-c:v', 'libx264', '-crf', '16', f'{T}/v{i}.mp4')
        has_a = 'audio' in subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout
        keep_a = has_a and source_audio_mode(C, c) == 'verified_ambience'
        if keep_a:
            sh('ffmpeg', '-y', '-v', 'error', '-ss', f'{st}', *lim, '-i', src, '-af', f'atempo={sp},aresample={SR}', '-ac', '1', f'{T}/a{i}.wav')
        segs.append({'v': f'{T}/v{i}.mp4', 'a': f'{T}/a{i}.wav' if keep_a else None, 'd': dur(f'{T}/v{i}.mp4'), 'trim': st})
        xfs.append(c.get('xfade', C.get('xfade', 0.25))); prev = src
    starts, t = [], 0.0
    for i, s in enumerate(segs):
        starts.append(t); t += s['d'] - (xfs[i] if i < len(segs) - 1 else 0)
    TOTAL = starts[-1] + segs[-1]['d']; at = lambda e: starts[e['seg']] + e['at']
    print('segments', [round(x, 2) for x in starts], 'total', round(TOTAL, 2))

    fi, fo = C.get('fade', [1.0, 1.5])
    fc, pv = [], '[0:v]'
    for i in range(1, len(segs)):
        fc.append(f'{pv}[{i}:v]xfade=transition=fade:duration={xfs[i-1]}:offset={starts[i]:.3f}[x{i}]'); pv = f'[x{i}]'
    fc.append(f'{pv}fade=t=in:st=0:d={fi},fade=t=out:st={TOTAL-fo:.3f}:d={fo}[vout]')
    sh('ffmpeg', '-y', '-v', 'error', *sum([['-i', s['v']] for s in segs], []), '-filter_complex', ';'.join(fc),
       '-map', '[vout]', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', f'{T}/video.mp4')

    # 2. audio -----------------------------------------------------------------
    N = int(TOTAL * SR)
    def place(buf, sig, t0):
        i = int(t0 * SR); j = min(N, i + len(sig))
        if 0 <= i < N: buf[i:j] += sig[:j - i]
    music = score.render([{'t': at(m), 'phrase': m['phrase']} for m in C.get('music', [])], TOTAL)[:N]
    music = np.pad(music, (0, N - len(music)))
    amb = np.zeros(N)
    for i, s in enumerate(segs):
        if not s['a']: continue
        _, a = wavfile.read(s['a']); a = a.astype(np.float64) / 32768
        f = int(0.4 * SR); env = np.ones(len(a)); env[:f] = np.linspace(0, 1, f); env[-f:] = np.linspace(1, 0, f)
        place(amb, a * env, starts[i])
    vo, spans = np.zeros(N), []
    V = C.get('vo') or {}
    for ln in V.get('lines', []):
        p = f"{T}/{ln['id']}.wav"
        sh('ffmpeg', '-y', '-v', 'error', '-i', str(narration_source(V, ln, base)), '-af',
           'silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,'
           f"atempo={V.get('tempo', 1.0)},aresample={SR},highpass=f=80,acompressor=threshold=-18dB:ratio=3", '-ac', '1', p)
        _, a = wavfile.read(p); a = a.astype(np.float64) / 32768
        t0 = at(ln)
        if t0 < 0 or t0 + len(a) / SR > TOTAL + 0.02:
            raise ValueError(f"Narration {ln['id']} runs outside the edit; adjust its start or provide a shorter recording.")
        place(vo, a / (np.abs(a).max() + 1e-9) * 0.9, t0); spans.append((t0, t0 + len(a) / SR, ln))
    print('vo', [(round(a, 2), round(b, 2), l['id']) for a, b, l in spans])
    duck = np.ones(N)
    for a, b, _ in spans: duck[max(0, int((a - .25) * SR)):int((b + .4) * SR)] = 0.45
    duck = np.convolve(duck, np.ones(int(.25 * SR)) / int(.25 * SR), 'same')
    mix = music * 0.55 * duck + amb * C.get('ambience', 0.3) + vo * 0.85
    e = int((TOTAL - fo) * SR); mix[e:] *= np.linspace(1, 0, N - e)
    mix = np.tanh(mix * 1.1) * 0.9
    wavfile.write(f'{T}/mix.wav', SR, (mix * 32767).astype(np.int16))
    wavfile.write(os.path.splitext(out)[0] + '_score.wav', SR, (music * 0.8 * 32767).astype(np.int16))

    # 3. overlays --------------------------------------------------------------
    layers = []
    def save(im, name): im.save(f'{T}/{name}.png'); return f'{T}/{name}.png'
    tt = C.get('title')
    if tt:
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        if tt.get('style', 'vertical') == 'vertical':
            f = ImageFont.truetype(find_font('Xingkai.ttc'), tt.get('size', 170)); x, y = tt.get('x', W // 2), tt.get('y', 250)
            for k, ch in enumerate(tt['zh']):
                d.text((x - d.textlength(ch, font=f) / 2, y + k * tt.get('size', 170) * 1.12), ch, font=f, fill=(32, 24, 18, 225))
        else:
            fz, fe = ImageFont.truetype(SONG, tt.get('size', 120), index=1), ImageFont.truetype(BASK, 46)
            for txt, f, yy in ((tt['zh'], fz, tt.get('y', 380)), (tt.get('en', ''), fe, tt.get('y', 380) + tt.get('size', 120) + 50)):
                if txt: d.text(((W - d.textlength(txt, font=f)) / 2, yy), txt, font=f, fill=tuple(tt.get('color', [255, 255, 255])) + (240,))
        t0, t1 = at(tt), starts[tt['seg']] + tt['until']
        layers += [(save(lay.filter(ImageFilter.GaussianBlur(9)), 'title_soft'), t0, t1, 1.0), (save(lay, 'title'), t0 + 0.7, t1, 1.0)]
        if tt.get('seal'):
            seal = Image.new('RGBA', (78, 150), (172, 38, 28, 235)); ds = ImageDraw.Draw(seal)
            fk = ImageFont.truetype(find_font('Kaiti.ttc'), 58)
            for k, ch in enumerate(tt['zh'][:2]):
                ds.text((39 - ds.textlength(ch, font=fk) / 2, 8 + k * 68), ch, font=fk, fill=(0, 0, 0, 0))
            a = np.array(seal); m = np.random.default_rng(1).random(a.shape[:2]) < 0.06; a[m, 3] = (a[m, 3] * 0.3).astype(np.uint8)
            sl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            sl.paste(Image.fromarray(a), (tt.get('x', W // 2) + 40, tt.get('y', 250) + len(tt['zh']) * int(tt.get('size', 170) * 1.12) + 40))
            layers.append((save(sl, 'seal'), t0 + 2.1, t1, 0.25))
    fz, fe = ImageFont.truetype(SONG, 44, index=1), ImageFont.truetype(BASK, 28)
    for k, (a, b, ln) in enumerate(spans):
        if not ln.get('zh'): continue
        im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        g = np.zeros((H, W, 4), np.uint8); g[..., 3] = (np.clip((np.arange(H) - 760) / 320, 0, 1) ** 1.3 * 105).astype(np.uint8)[:, None]
        im = Image.alpha_composite(im, Image.fromarray(g))
        shd, tx = Image.new('RGBA', (W, H), (0, 0, 0, 0)), Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ds, dt = ImageDraw.Draw(shd), ImageDraw.Draw(tx)
        for txt, f, yy in ((ln['zh'], fz, 905), (ln.get('en', ''), fe, 967)):
            x = (W - dt.textlength(txt, font=f)) / 2
            ds.text((x, yy + 2), txt, font=f, fill=(0, 0, 0, 200)); dt.text((x, yy), txt, font=f, fill=(255, 255, 255, 245))
        im = Image.alpha_composite(Image.alpha_composite(im, shd.filter(ImageFilter.GaussianBlur(5))), tx)
        layers.append((save(im, f'sub{k}'), a - .1, b + .5, 0.4))
    fc, pv, ins = [], '[0:v]', []
    for k, (png, a, b, fd) in enumerate(layers):
        ins += ['-loop', '1', '-framerate', str(FPS), '-t', f'{TOTAL:.2f}', '-i', png]
        fc.append(f'[{k+1}:v]format=rgba,fade=t=in:st={a:.2f}:d={fd}:alpha=1,fade=t=out:st={b-0.5:.2f}:d=0.5:alpha=1[o{k}]')
        fc.append(f'{pv}[o{k}]overlay=0:0[v{k}]'); pv = f'[v{k}]'
    if not layers: fc, pv = ['[0:v]null[v0]'], '[v0]'
    sh('ffmpeg', '-y', '-v', 'error', '-i', f'{T}/video.mp4', *ins, '-i', f'{T}/mix.wav', '-filter_complex', ';'.join(fc),
       '-map', pv, '-map', f'{len(layers)+1}:a', '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p',
       '-c:a', 'aac', '-b:a', '256k', '-shortest', out)
    print('done', out, round(TOTAL, 2))


if __name__ == '__main__':
    main(sys.argv[1])
