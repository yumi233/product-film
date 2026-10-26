"""Keyframes on the ChatGPT web app, through the user's logged-in Chrome (browser-skill / `bsk` CLI).

    python3 -u gpt_web.py jobs.json [ID ...] [--per-chat=8]   # no IDs = every job; existing outputs are skipped

jobs.json: {"style": "appended to every prompt", "jobs": [{"id", "out", "refs": [...], "prompt", "style"?}]}
Paths are relative to the current directory. ONE JOB AT A TIME in ONE chat: images keep coming in the same
conversation; after --per-chat images (default 8) or after a failure it opens a fresh chat. Never run several
windows in parallel: that breaks the attach menu and slows the user's Mac. Prints "OK <id> <secs>s <out>" / "FAIL <id> <why>".

Needs: `bsk` CLI + BrowserSkill extension in Chrome with "Allow access to file URLs" on, and the user
signed in to chatgpt.com. Works with the Chinese or English ChatGPT UI. See references/web-image.md.
Output is ~1672x941; wash approved frames to high resolution with gemini_wash.py.
"""
import base64, json, os, re, subprocess, sys, tempfile, time

# UI labels, Chinese | English
ATTACH = r'(添加文件等内容|Add files and more|Add photos)'
UPLOAD_ITEM = r'(添加照片和文件|Add photos (&|and) files|Upload from computer)'
PENDING = r'(待处理|Uploading|pending)'
SEND = r'(发送|Send prompt|Send)'
EMPTY = r'(询问 ChatGPT|Ask anything|Message ChatGPT)" \[empty\]'
STOP = r'(停止|Stop)'
GEN_ALT = '["已生成图像", "Generated image"]'
SAVE_JS = ('(async () => { const a=' + GEN_ALT + '; const i=[...document.querySelectorAll("main img")]'
           '.filter(i=>a.some(s=>i.alt.startsWith(s))).pop(); const b=await (await fetch(i.src)).blob();'
           ' return await new Promise(r=>{const f=new FileReader(); f.onload=()=>r(f.result); f.readAsDataURL(b)}); })()')
STATE_JS = ('(() => { const a=' + GEN_ALT + '; const n=[...document.querySelectorAll("main img")]'
            '.filter(i=>a.some(s=>i.alt.startsWith(s)) && i.naturalWidth>500).length;'
            ' const busy=!!document.querySelector("[data-testid=stop-button]"); return n+" "+busy; })()')


def bsk(*a, check=True):
    r = subprocess.run(['bsk', *a], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f'bsk {a[0]}: {r.stdout[-300:]} {r.stderr[-300:]}')
    return r.stdout


def ref_of(sid, pattern, page=None):
    m = re.search(r'(@e\d+) \w+ "' + pattern, page or bsk('observe', '--session', sid))
    return m and m.group(1)


class Chat:
    """One Agent Window with one ChatGPT conversation, reused for up to PER_CHAT images, then a fresh chat.
    Reusing the chat skips the page load and keeps the style context; a new chat every ~8 images keeps the
    page light and stops earlier images from leaking into later ones."""

    def __init__(self, per_chat):
        self.per_chat, self.sid, self.used = per_chat, None, 0

    def page(self):
        if self.sid is None:
            self.sid = json.loads(bsk('session', 'start', '--json', '--name', 'gpt-web'))['session_id']
        if self.used == 0 or self.used >= self.per_chat:
            bsk('navigate', 'https://chatgpt.com/', '--session', self.sid, check=False)  # new chat; load may time out
            time.sleep(8)
            self.used = 0
        return self.sid

    def reset(self):  # after a failure, start over in a fresh chat
        self.used = 0

    def close(self):
        if self.sid:
            bsk('session', 'stop', self.sid, check=False)


def count_images(sid):
    return int(bsk('evaluate', STATE_JS, '--session', sid).strip().splitlines()[-1].split()[0])


def run(job, style, chat):
    if os.path.exists(job['out']):
        print('SKIP', job['id'], job['out'], flush=True); return True
    tmp = tempfile.mkdtemp(prefix='gw_')
    refs = []
    for k, r in enumerate(job.get('refs', []), 1):  # jpg, max 1600 px: small uploads
        p = os.path.join(tmp, f'ref{k}.jpg')
        subprocess.run(['magick', r, '-resize', '1600x1600>', '-quality', '88', p], check=True)
        refs.append(p)
    try:
        sid = chat.page()
        before = count_images(sid)
        if refs:
            for _ in range(6):  # page may still be loading: reopen the attach menu until the item shows
                btn = ref_of(sid, ATTACH)
                if btn:
                    bsk('click', btn, '--session', sid, check=False)
                time.sleep(2)
                item = ref_of(sid, UPLOAD_ITEM)
                if item:
                    break
                bsk('press', 'Escape', '--session', sid, check=False)
            else:
                raise RuntimeError('attach menu not found')
            bsk('upload', item, *sum((['--file', p] for p in refs), []), '--session', sid)
            for _ in range(60):  # let uploads finish before writing the prompt
                time.sleep(2)
                if not re.search(PENDING, bsk('observe', '--session', sid)):
                    break
        intro = ('NEW, SEPARATE IMAGE. Ignore earlier images in this chat unless attached again. ' if chat.used else '') + (
                ('The attached images are references, in order: image 1, image 2, ... '
                 'Generate ONE image now, 16:9 landscape, no text, no questions. ') if refs else
                'Generate ONE image, 16:9 landscape, no text, no questions. ')
        text = intro + job['prompt'] + ' ' + job.get('style', style)
        js = ('(()=>{const e=[...document.querySelectorAll("[contenteditable=true]")].filter(x=>x.offsetParent).pop();e.focus();'
              'document.execCommand("insertText",false,' + json.dumps(text) + ');return e.innerText.length})()')
        bsk('click', '#prompt-textarea', '--session', sid, check=False)   # later turns: a hidden editor may also match
        bsk('evaluate', js, '--session', sid)   # `bsk fill` loses focus in ChatGPT's editor; insertText works
        time.sleep(1)
        bsk('press', 'Enter', '--session', sid)
        for _ in range(10):  # Enter is ignored while an upload settles: fall back to the send button
            time.sleep(3)
            page = bsk('observe', '--session', sid)
            if re.search(EMPTY, page) or re.search(r'button "' + STOP, page):
                break
            send = ref_of(sid, SEND, page)
            if send:
                bsk('click', send, '--session', sid, check=False)
        t0 = time.time()
        while time.time() - t0 < 900:
            time.sleep(10)
            n, busy = bsk('evaluate', STATE_JS, '--session', sid).strip().splitlines()[-1].split()
            if int(n) > before and busy == 'false':   # a NEW image in this chat, generation finished
                break
        else:
            print('TIMEOUT', job['id'], flush=True); chat.reset(); return False
        data = bsk('evaluate', SAVE_JS, '--session', sid).strip().splitlines()[-1]   # SAVE_JS takes the last image
        os.makedirs(os.path.dirname(os.path.abspath(job['out'])) or '.', exist_ok=True)
        open(job['out'], 'wb').write(base64.b64decode(data.split(',', 1)[1]))
        chat.used += 1
        print(f'OK {job["id"]} {int(time.time() - t0)}s {job["out"]}', flush=True); return True
    except Exception as e:
        print(f'FAIL {job["id"]} {e}', flush=True); chat.reset(); return False


if __name__ == '__main__':
    d = json.load(open(sys.argv[1]))
    want = [a for a in sys.argv[2:] if not a.startswith('--per-chat')]
    per = int(next((a.split('=')[1] for a in sys.argv[2:] if a.startswith('--per-chat=')), 8))
    chat = Chat(per)
    try:
        for j in [j for j in d['jobs'] if not want or j['id'] in want]:
            if not run(j, d.get('style', ''), chat):   # one retry in a fresh chat
                run(j, d.get('style', ''), chat)
    finally:
        chat.close()
