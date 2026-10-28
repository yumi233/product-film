"""Keyframe vs. design renders, side by side, for piece-by-piece checking.

    python3 compare.py <frame.png> <out.jpg> <render> [<render> ...]
The frame goes on top at full width, the v28 renders in a row underneath at equal height.
"""
import sys
from PIL import Image

frame, out, refs = sys.argv[1], sys.argv[2], sys.argv[3:]
W = 1800
top = Image.open(frame).convert('RGB')
top = top.resize((W, round(top.height * W / top.width)))
h = 360
row = []
for p in refs:
    im = Image.open(p).convert('RGB')
    row.append(im.resize((round(im.width * h / im.height), h)))
rw = sum(i.width for i in row) + 8 * (len(row) - 1)
if rw > W:  # shrink the row to fit the width
    k = W / rw
    row = [i.resize((round(i.width * k), round(h * k))) for i in row]
    h = round(h * k)
sheet = Image.new('RGB', (W, top.height + 8 + h), 'white')
sheet.paste(top, (0, 0))
x = 0
for i in row:
    sheet.paste(i, (x, top.height + 8))
    x += i.width + 8
sheet.save(out, quality=88)
