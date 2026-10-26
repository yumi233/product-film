"""Wash images through the Gemini web app (user's logged-in Chrome, via bsk): same content, higher resolution.

    python3 -u gemini_wash.py OUT_DIR IMG[::REF[,REF]] ...

Each image goes to a fresh Gemini chat in image mode with its product renders as references and the user's own
re-render prompt ("参考家具单体细节，重新渲染……提升结构和材质的清晰度"). The full-size result (about 2752x1536)
lands in ~/Downloads and is moved to OUT_DIR/<name>_gemini.jpg. One image at a time; existing outputs are skipped.
Needs `bsk` + BrowserSkill (file URLs allowed) and the user signed in to gemini.google.com. Chinese or English UI.
Always compare the washed image with the input: Gemini may re-crop or simplify a part; reject such washes.
"""
import glob, json, os, re, shutil, subprocess, sys, time

PROMPT = ('参考家具单体细节（后面几张是家具的白底渲染图），重新渲染第一张图，提升结构和材质的清晰度。'
          '构图、机位、空间、光线、天气、植物和水面都与第一张完全一致；家具的位置、大小、透视和每一个零件都保持不变，'
          '只把细节和材质渲染得更清晰。输出 16:9 横幅、尽量高的分辨率。不要加文字，不要加人，不要增减家具。')
DL = os.path.expanduser('~/Downloads')


def bsk(*a, check=True):
    r = subprocess.run(['bsk', *a], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f'bsk {a[0]}: {r.stdout[-300:]} {r.stderr[-300:]}')
    return r.stdout


# UI labels, Chinese | English
L = {'tools': r'(上传和工具|Upload and tools|Tools)', 'upload': r'(上传文件|Upload files)',
     'image': r'(制作图片|Create image|Create images)', 'busy': r'(正在上传|正在加载图片|Uploading|Loading image)',
     'stop': r'(停止回答|Stop response)', 'download': r'(下载完整尺寸的图片|Download full size image|Download full-size)'}


def ref_of(sid, pattern):
    m = re.search(r'(@e\d+) [\w]+ "' + pattern, bsk('observe', '--session', sid))
    return m and m.group(1)


def wait_until(sid, gone=None, present=None, limit=600, step=3):
    t0 = time.time()
    while time.time() - t0 < limit:
        page = bsk('observe', '--session', sid)
        if (gone and not re.search(gone, page)) or (present and re.search(present, page)):
            return page
        time.sleep(step)
    raise RuntimeError(f'timeout waiting for {gone or present}')


def wash(img, refs, out_dir):
    name = os.path.splitext(os.path.basename(img))[0]
    if glob.glob(os.path.join(out_dir, name + '_gemini.*')):
        print('SKIP', name, flush=True); return True
    sid = json.loads(bsk('session', 'start', '--json', '--name', 'wash-' + name))['session_id']
    try:
        bsk('navigate', 'https://gemini.google.com/app', '--session', sid, check=False)
        time.sleep(5)
        bsk('click', ref_of(sid, L['tools']), '--session', sid)
        time.sleep(1.5)
        bsk('upload', ref_of(sid, L['upload']), *sum((['--file', p] for p in [img, *refs]), []), '--session', sid)
        bsk('click', ref_of(sid, L['tools']), '--session', sid)   # switch the composer to image mode
        time.sleep(1.5)
        bsk('click', ref_of(sid, L['image']), '--session', sid)
        wait_until(sid, gone=L['busy'])
        js = ('(()=>{const e=document.querySelector("div[contenteditable=true]");e.focus();'
              'document.execCommand("insertText",false,' + json.dumps(PROMPT) + ');return e.innerText.length})()')
        bsk('evaluate', js, '--session', sid)
        time.sleep(1)
        bsk('press', 'Enter', '--session', sid)
        t0 = time.time()
        wait_until(sid, present=L['stop'], limit=60)
        page = wait_until(sid, gone=L['stop'], limit=600, step=5)
        before = set(glob.glob(os.path.join(DL, 'Gemini_Generated_Image_*')))
        bsk('click', ref_of(sid, L['download']), '--session', sid)
        for _ in range(60):                    # the full-size file lands in ~/Downloads
            time.sleep(2)
            new = [f for f in set(glob.glob(os.path.join(DL, 'Gemini_Generated_Image_*'))) - before
                   if not f.endswith('.crdownload')]
            if new:
                break
        else:
            raise RuntimeError('download not found')
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, name + '_gemini' + os.path.splitext(new[0])[1].replace('jpeg', 'jpg'))
        shutil.move(new[0], out)
        size = subprocess.run(['magick', 'identify', '-format', '%wx%h', out], capture_output=True, text=True).stdout
        print(f'OK {name} {int(time.time() - t0)}s {size} {out}', flush=True); return True
    except Exception as e:
        print(f'FAIL {name} {e}', flush=True); return False
    finally:
        bsk('session', 'stop', sid, check=False)


if __name__ == '__main__':
    out_dir = sys.argv[1]
    for arg in sys.argv[2:]:
        img, _, refs = arg.partition('::')
        refs = [r for r in refs.split(',') if r]
        if not wash(img, refs, out_dir):   # one retry
            wash(img, refs, out_dir)
