"""Smooth push-in on a still, rendered with sub-pixel accuracy (ffmpeg zoompan steps in whole pixels and stutters).

    python3 still_push.py <image> <out.mp4> <seconds> [zoom_end=1.06]
Each frame is resampled from the full-resolution source with a float crop box, then piped to ffmpeg at 24 fps.
"""
import subprocess, sys
from PIL import Image

src, out, secs = sys.argv[1], sys.argv[2], float(sys.argv[3])
z1 = float(sys.argv[4]) if len(sys.argv) > 4 else 1.06
W, H, FPS = 1920, 1080, 24
im = Image.open(src).convert('RGB')
# cover-fit to 16:9 at source resolution
s = max(W / im.width, H / im.height)
cw, ch = W / s, H / s                       # crop box (source pixels) at zoom 1
cx, cy = im.width / 2, im.height / 2
n = int(round(secs * FPS))
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                      '-i', '-', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
for k in range(n):
    t = k / (n - 1)
    e = t * t * (3 - 2 * t)                 # ease in-out
    z = 1 + (z1 - 1) * e
    w, h = cw / z, ch / z
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    p.stdin.write(im.resize((W, H), Image.LANCZOS, box=box).tobytes())
p.stdin.close(); p.wait()
