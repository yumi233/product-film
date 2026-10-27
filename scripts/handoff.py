"""Handoff between agents/terminals (Claude desktop, Claude CLI, Codex): status snapshot + a one-driver lock.

    python3 handoff.py status  PROJECT [--write HANDOFF.md]   # print (or write into the file) what is running / done
    python3 handoff.py claim   PROJECT NAME                   # take the driver seat (browser + RunningHub)
    python3 handoff.py release PROJECT NAME                   # give it back
    python3 handoff.py who     PROJECT                        # who drives now

The snapshot covers: running jobs (rh_run / gpt_web / gemini_wash / vo.py / cut.py), open bsk sessions, the tail of
every RunningHub / web-image / wash log under PROJECT (and which RunningHub task ids have no saved video yet),
and the RH coin balance (never the key). With --write it replaces the block between
<!-- handoff:status:start --> and <!-- handoff:status:end --> in the handoff file (appended if missing).

Only ONE agent may drive the browser and RunningHub at a time (one ChatGPT/Gemini window, one RH task per account).
The lock is a plain file PROJECT/.product-film-driver; it is advisory: always run `who` before starting jobs.
"""
import glob, json, os, re, subprocess, sys, time

START, END = '<!-- handoff:status:start -->', '<!-- handoff:status:end -->'
LOCK = '.product-film-driver'
SKIP_DIRS = ('归档', 'archive', '.git', 'node_modules')
JOBS = r'rh_run\.py|gpt_web\.py|gemini_wash\.py|vo\.py|cut\.py|keyframe\.py'


def sh(*a, timeout=30):
    try:
        return subprocess.run(a, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:
        return ''


def rel(p, root):
    return os.path.relpath(p, root)


def running():
    out = sh('ps', '-axo', 'pid,etime,command')
    rows = []
    for line in out.splitlines()[1:]:
        if re.search(JOBS, line) and 'handoff.py' not in line and 'grep' not in line:
            pid, et, cmd = line.strip().split(None, 2)
            m = re.search(r'(\S*(?:' + JOBS + r'))(.*)', cmd)
            rows.append(f'- pid {pid}，已运行 {et}：`{os.path.basename(m.group(1)) if m else cmd[:40]}{(m.group(2)[:90] if m else "")}`')
    return rows


def rh_logs(root):
    rows = []
    for tl in glob.glob(os.path.join(root, '**/rh_tasks.log'), recursive=True):
        if any(k in tl for k in SKIP_DIRS):
            continue
        d = os.path.dirname(tl)
        pending = []
        for line in open(tl, encoding='utf-8', errors='ignore'):
            parts = line.rstrip('\n').split('\t')
            if len(parts) == 3 and not os.path.exists(os.path.join(d, parts[1] + '.mp4')):
                pending.append(f'{parts[1]}（{parts[2]}）')
        saved = len(glob.glob(os.path.join(d, '*.mp4')))
        rows.append(f'- `{rel(d, root)}`：已下载 {saved} 条' + (f'；**未下载**：{"、".join(pending[-6:])}' if pending else ''))
    return rows


def tail_logs(root):
    rows = []
    pats = ['**/生成.log', '**/洗图.log', '**/*.log']
    seen = set()
    for pat in pats:
        for f in sorted(glob.glob(os.path.join(root, pat), recursive=True), key=os.path.getmtime, reverse=True):
            if f in seen or any(k in f for k in SKIP_DIRS) or f.endswith('rh_tasks.log') or time.time() - os.path.getmtime(f) > 3 * 86400:
                continue
            seen.add(f)
            lines = [l.strip() for l in open(f, encoding='utf-8', errors='ignore')
                     if re.match(r'^(OK|FAIL|SKIP|SAVED|FAILED|TIMEOUT|task |done )', l.strip())]
            if not lines:
                continue
            ok = sum(l.startswith(('OK', 'SAVED')) for l in lines)
            bad = [l for l in lines if l.startswith(('FAIL', 'TIMEOUT'))]
            when = time.strftime('%m-%d %H:%M', time.localtime(os.path.getmtime(f)))
            rows.append(f'- `{rel(f, root)}`（{when}）：成功 {ok}，失败 {len(bad)}；最后一行：`{lines[-1][:110]}`')
    return rows[:12]


def balance():
    here = os.path.dirname(os.path.abspath(__file__))
    out = (sh(sys.executable, os.path.join(here, 'rh_run.py'), '--check', timeout=40) if os.name == 'nt'
           else sh('zsh', '-ic', f'python3 "{here}/rh_run.py" --check', timeout=40))
    m = re.search(r'"coins":\s*"?(\d+)', out)
    return m.group(1) if m else '查询失败'


def who(root):
    p = os.path.join(root, LOCK)
    return open(p, encoding='utf-8').read().strip() if os.path.exists(p) else ''


def status(root):
    now = time.strftime('%Y-%m-%d %H:%M')
    run = running()
    sess = [l for l in sh('bsk', 'session', 'list').splitlines()[1:] if l.strip() and 'no active' not in l]
    parts = [START, f'### 当前状态（自动生成，{now}）', '',
             f'- 执行者锁：{who(root) or "无人占用"}',
             f'- RunningHub 余额：{balance()} 币', '',
             '**正在运行的任务**', *(run or ['- 无']), '',
             '**浏览器会话（bsk）**', *([f'- {s.strip()}' for s in sess] or ['- 无']), '',
             '**RunningHub 视频批次**', *(rh_logs(root) or ['- 无']), '',
             '**最近的日志**', *(tail_logs(root) or ['- 无']), END]
    return '\n'.join(parts)


def write(text, path):
    old = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
    if START in old and END in old:
        new = old[:old.index(START)] + text + old[old.index(END) + len(END):]
    else:
        new = old.rstrip() + '\n\n' + text + '\n'
    open(path, 'w', encoding='utf-8').write(new)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, root = sys.argv[1], os.path.abspath(sys.argv[2])
    if cmd == 'status':
        text = status(root)
        if '--write' in sys.argv:
            write(text, sys.argv[sys.argv.index('--write') + 1]); print('written')
        else:
            print(text)
    elif cmd == 'claim':
        cur = who(root)
        if cur and not cur.startswith(sys.argv[3] + ' '):
            sys.exit(f'已被占用：{cur}。先让对方 release，或确认对方已停止后再 claim --force。') if '--force' not in sys.argv else None
        open(os.path.join(root, LOCK), 'w', encoding='utf-8').write(f'{sys.argv[3]} 自 {time.strftime("%Y-%m-%d %H:%M")}')
        print('claimed by', sys.argv[3])
    elif cmd == 'release':
        p = os.path.join(root, LOCK)
        if os.path.exists(p) and who(root).startswith(sys.argv[3] + ' '):
            os.remove(p); print('released')
        else:
            print('not held by', sys.argv[3], '— current:', who(root) or 'none')
    elif cmd == 'who':
        print(who(root) or '无人占用')
