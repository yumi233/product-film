"""Contact sheet for QA: N evenly spaced frames of each video, one row per video.

    python3 contact.py sheet.png clip1.mp4 clip2.mp4 ... [--n 6] [--w 400]

Look at it for: motion strength, product shape drift (legs, joints, materials), style drift, and whether the
last frame lands where the next clip starts.
"""
import subprocess, sys, tempfile, os


def sheet(out, videos, n=6, w=400):
    rows = []
    for v in videos:
        frames = int(subprocess.run(['ffprobe', '-v', 'error', '-count_packets', '-select_streams', 'v:0', '-show_entries',
                                     'stream=nb_read_packets', '-of', 'csv=p=0', v], capture_output=True, text=True).stdout.strip() or 0)
        step = max(1, frames // n)
        r = tempfile.mktemp(suffix='.png')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', v, '-vf',
                        f"select='not(mod(n\\,{step}))',scale={w}:-2,tile={n}x1", '-frames:v', '1', r], check=True)
        rows.append(r)
    ins = sum([['-i', r] for r in rows], [])
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex',
                    f'vstack={len(rows)}' if len(rows) > 1 else 'null', out], check=True)
    for r in rows: os.remove(r)
    print('sheet', out)


if __name__ == '__main__':
    args = sys.argv[1:]; n = w = None
    if '--n' in args: i = args.index('--n'); n = int(args[i + 1]); del args[i:i + 2]
    if '--w' in args: i = args.index('--w'); w = int(args[i + 1]); del args[i:i + 2]
    sheet(args[0], args[1:], n or 6, w or 400)
