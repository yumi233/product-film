"""Keyframes on the ChatGPT web app, through the user's logged-in Chrome (browser-skill / `bsk` CLI).

    python3 -u gpt_web.py jobs.json [ID ...]          # no IDs = every job; existing outputs are skipped

jobs.json: {"style": "appended to every prompt", "jobs": [{"id", "out", "refs": [...], "prompt", "style"?}]}
Paths are relative to the current directory. One fresh chat per job, ONE JOB AT A TIME: parallel windows
break the attach menu, and the user's Mac gets slow. Prints "OK <id> <secs>s <out>" / "FAIL <id> <why>".

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


def run(job, style):
    if os.path.exists(job['out']):
        print('SKIP', job['id'], job['out'], flush=True); return True
    tmp = tempfile.mkdtemp(prefix='gw_')
    refs = []
    for k, r in enumerate(job.get('refs', []), 1):  # jpg, max 1600 px: small uploads
        p = os.path.join(tmp, f'ref{k}.jpg')
        subprocess.run(['magick', r, '-resize', '1600x1600>', '-quality', '88', p], check=True)
        refs.append(p)
    sid = json.loads(bsk('session', 'start', '--json', '--name', job['id']))['session_id']
    try:
        bsk('navigate', 'https://chatgpt.com/', '--session', sid, check=False)  # load event may time out
        time.sleep(8)
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
        intro = ('The attached images are references, in order: image 1, image 2, ... '
                 'Generate ONE image now, 16:9 landscape, no text, no questions. ') if refs else \
                'Generate ONE image, 16:9 landscape, no text, no questions. '
        text = intro + job['prompt'] + ' ' + job.get('style', style)
        js = ('(()=>{const e=document.querySelector("[contenteditable=true]");e.focus();'
              'document.execCommand("insertText",false,' + json.dumps(text) + ');return e.innerText.length})()')
        bsk('click', '[contenteditable=true]', '--session', sid)
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
            if int(n) > 0 and busy == 'false':
                break
        else:
            print('TIMEOUT', job['id'], flush=True); return False
        data = bsk('evaluate', SAVE_JS, '--session', sid).strip().splitlines()[-1]
        os.makedirs(os.path.dirname(os.path.abspath(job['out'])) or '.', exist_ok=True)
        open(job['out'], 'wb').write(base64.b64decode(data.split(',', 1)[1]))
        print(f'OK {job["id"]} {int(time.time() - t0)}s {job["out"]}', flush=True); return True
    except Exception as e:
        print(f'FAIL {job["id"]} {e}', flush=True); return False
    finally:
        bsk('session', 'stop', sid, check=False)


if __name__ == '__main__':
    d = json.load(open(sys.argv[1]))
    want = sys.argv[2:]
    for j in [j for j in d['jobs'] if not want or j['id'] in want]:
        if not run(j, d.get('style', '')):   # one retry: most failures are a slow page or a missed click
            run(j, d.get('style', ''))
