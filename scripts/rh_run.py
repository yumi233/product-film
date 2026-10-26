"""Run the RunningHub MiniMax-H3 reference-to-video workflow (charged in RH coins, member API key).

Single clip:
    python3 rh_run.py --name 1-2 --prompt "..." --secs 8 ref1.jpg ref2.jpg
Batch (sequential, skips clips already downloaded):
    python3 rh_run.py --batch shots.json          # [{"name", "prompt", "refs": [...], "secs"?}, ...]
Balance:
    python3 rh_run.py --check
Recover a run that was killed after the task was created (ids are logged in <out-dir>/rh_tasks.log):
    python3 rh_run.py --fetch TASK_ID --name 1-2 --out-dir videos/raw

Key: env RUNNINGHUB_API_KEY (never print it). Concurrency is 1 task per account, so clips run one after another.
Output: <out-dir>/<name>.mp4, and one line per clip "SAVED <path> coins <n>".
"""
import argparse, json, os, subprocess, sys, time
from audio_policy import generation_prompt

HOST = 'https://www.runninghub.cn'
# AITUDOU MiniMax H3 ReferenceToVideo workflow and its editable nodes
WORKFLOW = '2113173574050729986'
REF_NODES = ('88', '84', '86', '87')          # LoadImage x4 (ref image 1..4)
PROMPT_NODE, SECS_NODE, MP_NODE, LOWRES_NODE = '94', '85', '63', '111'


def key():
    k = os.environ.get('RUNNINGHUB_API_KEY')
    if not k:
        sys.exit('RUNNINGHUB_API_KEY is not set (add it to ~/.zshrc and run via zsh -ic).')
    return k


def post(path, data, url=None):
    r = subprocess.run(['curl', '-s', '-X', 'POST', url or HOST + path, '-H', 'Content-Type: application/json',
                        '-d', json.dumps(data)], capture_output=True, text=True)
    return json.loads(r.stdout or '{}')


def upload(path):
    r = subprocess.run(['curl', '-s', '-X', 'POST', HOST + '/task/openapi/upload', '-F', f'apiKey={key()}',
                        '-F', f'file=@{path}', '-F', 'fileType=image'], capture_output=True, text=True)
    return json.loads(r.stdout)['data']['fileName']


def check():
    d = post('', {'apikey': key()}, url=HOST + '/uc/openapi/accountStatus').get('data') or {}
    print(json.dumps({'coins': d.get('remainCoins'), 'wallet': d.get('remainMoney'),
                      'running_tasks': d.get('currentTaskCounts')}, ensure_ascii=False))


def run(name, prompt, refs, secs=8, mp=2.07, lowres=0.66, out_dir='.', workflow=WORKFLOW, plus=False):
    out = os.path.join(out_dir, f'{name}.mp4')
    if os.path.exists(out):
        print('SKIP (exists)', out, flush=True); return out
    prompt = generation_prompt(prompt)  # ambience/effects only; narration is mixed separately
    files = [upload(p) for p in refs]
    files = (files * 4)[:4]                    # every LoadImage needs a file; repeat refs to fill 4 slots
    nodes = [{'nodeId': n, 'fieldName': 'image', 'fieldValue': f} for n, f in zip(REF_NODES, files)]
    nodes += [{'nodeId': PROMPT_NODE, 'fieldName': 'text', 'fieldValue': prompt},
              {'nodeId': SECS_NODE, 'fieldName': 'value', 'fieldValue': str(secs)},
              {'nodeId': MP_NODE, 'fieldName': 'megapixels', 'fieldValue': str(mp)},
              {'nodeId': LOWRES_NODE, 'fieldName': 'lowres_scale', 'fieldValue': str(lowres)}]
    for attempt in range(60):                  # TASK_QUEUE_MAXED (421) -> wait for the running task
        body = {'apiKey': key(), 'workflowId': workflow, 'nodeInfoList': nodes}
        if plus:   # 48G 'Plus' machine: avoids OutOfMemory on long / high-res clips; costs more coins
            body['instanceType'] = 'plus'
        c = post('/task/openapi/create', body)
        if c.get('code') == 0: break
        if c.get('code') == 421 or 'QUEUE' in str(c.get('msg')):
            time.sleep(30); continue
        print('CREATE FAILED', name, json.dumps(c, ensure_ascii=False), flush=True); return None
    tid = c['data']['taskId']; print('task', name, tid, flush=True)
    os.makedirs(out_dir, exist_ok=True)  # keep the id on disk: a killed run can be recovered with --fetch
    with open(os.path.join(out_dir, 'rh_tasks.log'), 'a') as log:
        log.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")}\t{name}\t{tid}\n')
    return fetch(name, tid, out_dir)


def fetch(name, tid, out_dir='.'):
    """Wait for task `tid` and download its video to <out_dir>/<name>.mp4 (also used to recover a killed run)."""
    out = os.path.join(out_dir, f'{name}.mp4')
    status = None
    for _ in range(360):
        time.sleep(20)
        status = post('/task/openapi/status', {'apiKey': key(), 'taskId': tid}).get('data')
        if status in ('SUCCESS', 'FAILED'): break
    o = post('/task/openapi/outputs', {'apiKey': key(), 'taskId': tid})
    data = o.get('data')
    if isinstance(data, dict):   # a failed task returns {"failedReason": {...}} instead of a list of files
        fr = data.get('failedReason') or {}
        print('FAILED', name, status, fr.get('exception_type'), '(failed tasks are not charged; usually server '
              'OutOfMemory - rerun, or use --secs 10 / a lower --mp)', flush=True)
        return None
    for f in data or []:
        if str(f.get('fileUrl', '')).endswith('.mp4'):
            os.makedirs(out_dir, exist_ok=True)
            subprocess.run(['curl', '-s', '-o', out, f['fileUrl']])
            print('SAVED', out, 'coins', f.get('consumeCoins'), 'secs', f.get('taskCostTime'), flush=True)
            return out
    print('FAILED', name, status, json.dumps(o, ensure_ascii=False)[:400], flush=True)
    return None


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('refs', nargs='*')
    ap.add_argument('--name'); ap.add_argument('--prompt')
    ap.add_argument('--secs', type=float, default=8)
    ap.add_argument('--mp', type=float, default=2.07, help='final megapixels (2.07 -> 1952x1120)')
    ap.add_argument('--lowres', type=float, default=0.66, help='first-pass scale per side (~0.9 MP first pass)')
    ap.add_argument('--out-dir', default='videos/raw')
    ap.add_argument('--workflow', default=WORKFLOW)
    ap.add_argument('--plus', action='store_true', help='run on the 48G Plus GPU (fewer OOM failures, more coins)')
    ap.add_argument('--batch'); ap.add_argument('--check', action='store_true')
    ap.add_argument('--fetch', metavar='TASK_ID', help='download a finished task by id (see <out-dir>/rh_tasks.log)')
    a = ap.parse_args()
    if a.check:
        check()
    elif a.fetch:
        fetch(a.name, a.fetch, a.out_dir)
    elif a.batch:
        base = os.path.dirname(os.path.abspath(a.batch))
        for s in json.load(open(a.batch)):
            refs = [r if os.path.isabs(r) else os.path.join(base, r) for r in s['refs']]
            run(s['name'], s['prompt'], refs, s.get('secs', a.secs), a.mp, a.lowres, a.out_dir, a.workflow, a.plus)
    else:
        run(a.name, a.prompt, a.refs, a.secs, a.mp, a.lowres, a.out_dir, a.workflow, a.plus)
