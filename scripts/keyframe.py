"""Generate one keyframe / painting panel with the Codex CLI image tool.

    python3 keyframe.py OUT.png "prompt" [ref1 ref2 ...] [--painting]

- Each call works in its own temp dir (Codex writes OUT.png there), then the result is copied to OUT.png.
- The prompt goes in on stdin: Codex's -i flag swallows a positional prompt.
- Refs are passed in order; refer to them in the prompt as "reference image 1", "reference image 2", ...
- --painting switches the suffix from photoreal to painted/outpaint wording and asks for 2400x1350.
Several keyframes can run in parallel (separate processes); RunningHub is not involved.
"""
import os, shutil, subprocess, sys, tempfile

PHOTO = ('Use your image generation tool. Output ONE photorealistic image, 16:9 landscape, at least 1920x1080, '
         'saved in the current directory as OUT.png. No text, no watermark, no logos.')
PAINT = ('Use your image generation / editing tool. Output ONE image, 16:9 landscape, 2400x1350 or larger, saved in '
         'the current directory as OUT.png. Absolutely no text, no calligraphy, no seals, no signatures, no watermark.')


def keyframe(out, prompt, refs=(), painting=False):
    d = tempfile.mkdtemp(prefix='kf_')
    args = []
    for i, r in enumerate(refs, 1):
        ext = os.path.splitext(r)[1] or '.png'
        shutil.copy(r, os.path.join(d, f'ref{i}{ext}')); args += ['-i', f'ref{i}{ext}']
    text = f'{prompt}\n\n{PAINT if painting else PHOTO}'
    with open(os.path.join(d, 'log.txt'), 'w') as log:
        subprocess.run(['codex', 'exec', '--skip-git-repo-check', '--sandbox', 'workspace-write', *args],
                       input=text, text=True, cwd=d, stdout=log, stderr=subprocess.STDOUT)
    src = os.path.join(d, 'OUT.png')
    if not os.path.exists(src):
        print('FAIL', out, 'see', os.path.join(d, 'log.txt')); return None
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    shutil.copy(src, out); print('OK', out); return out


if __name__ == '__main__':
    painting = '--painting' in sys.argv
    argv = [a for a in sys.argv[1:] if a != '--painting']
    keyframe(argv[0], argv[1], argv[2:], painting)
