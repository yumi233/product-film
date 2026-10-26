"""Environment self-check for product-film. Run it first in any new project (Claude Code or Codex).

    python3 scripts/doctor.py            # prints one line per check: OK / MISSING / WARN + how to fix

Never prints secrets. Does not install anything; it only tells the user (and the agent) what to do.
"""
import glob, importlib.util, json, os, shutil, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
rows = []


def row(name, ok, fix, level='MISSING'):
    rows.append(('OK' if ok else level, name, '' if ok else fix))


def run(*a, timeout=20):
    try:
        return subprocess.run(a, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return None


# 1. Python packages (cut.py / score.py / voicestat.py)
missing = [m for m in ('numpy', 'scipy', 'PIL') if importlib.util.find_spec(m) is None]
row('Python: numpy / scipy / Pillow', not missing,
    f'缺 {", ".join(missing)}。建一个 venv：python3 -m venv .venv && .venv/bin/pip install -r {SKILL}/requirements.txt，'
    '之后剪辑用 .venv/bin/python 跑')

# 2. Command-line tools
for tool, fix in [('ffmpeg', 'brew install ffmpeg'), ('magick', 'brew install imagemagick（需要 ImageMagick 7）')]:
    row(tool, shutil.which(tool) is not None, fix)

# 3. Browser control for ChatGPT / Gemini web
bsk = shutil.which('bsk')
row('browser-skill（bsk 命令）', bsk is not None,
    '安装 browser-skill（bsk CLI + Chrome 扩展）。没有它就只能退回 Codex 生图，见 references/setup.md')
if bsk:
    r = run('bsk', 'browsers')
    connected = bool(r and r.returncode == 0 and len(r.stdout.strip().splitlines()) > 1)
    row('Chrome 扩展已连接', connected, '打开 Chrome，确认 BrowserSkill 扩展已启用；并在扩展详情里打开「允许访问文件网址」',
        'WARN')
rows.append(('CHECK', 'ChatGPT / Gemini 已登录', '由 agent 用 bsk 打开 chatgpt.com、gemini.google.com 查看；未登录请用户自己登录'))

# 4. RunningHub key (presence only, never the value)
zshrc = os.path.expanduser('~/.zshrc')
has_key = bool(os.environ.get('RUNNINGHUB_API_KEY')) or (
    os.path.exists(zshrc) and 'RUNNINGHUB_API_KEY' in open(zshrc, errors='ignore').read())
row('RunningHub 会员 key（RUNNINGHUB_API_KEY）', has_key,
    '请用户自己在 ~/.zshrc 加一行 export RUNNINGHUB_API_KEY=...（不要贴进聊天）。查余额：zsh -ic "python3 scripts/rh_run.py --check"')

# 5. Local TTS / ASR
cands = [os.environ.get('QWEN3_TTS_DIR', '')] + [os.path.expanduser('~/qwen3-tts')] + \
        sorted(glob.glob(os.path.expanduser('~/AI/qwen3-tts*')))
tts = next((c for c in cands if c and os.path.isdir(os.path.join(c, 'models'))), None)
row('可选本机 Qwen3-TTS / ASR', tts is not None,
    '没有模型时向用户索要最终旁白录音（WAV/MP3/M4A/FLAC）及对应文稿，后期直接导入；不必安装Qwen3', 'OPTIONAL')
if tts:
    models = os.listdir(os.path.join(tts, 'models'))
    row('声音克隆模型（Base）', any('Base' in m for m in models),
        '下载 Qwen3-TTS-12Hz-0.6B-Base-4bit 到 models/，用于全片统一音色', 'WARN')
    row('回听模型（ASR）', any('ASR' in m for m in models), '下载 Qwen3-ASR-0.6B-8bit 到 models/', 'WARN')

rows.append(('INPUT', '旁白来源', '确认用户提供成品录音，或选择已有本机TTS；视频模型仅生成环境音效，无旁白/对白/唱歌。'))

# 6. Optional: Codex CLI and companion skills
row('Codex CLI（备选生图）', shutil.which('codex') is not None, '可选：npm i -g @openai/codex', 'WARN')
skill_dirs = [os.path.expanduser('~/.claude/skills'), os.path.expanduser('~/.codex/skills')]
for name, why in [('browser-skill', '网页出图、洗图'), ('hd-image-workflow', '分块高清重建（可选）'),
                  ('human-first-article', '旁白文案去 AI 腔（可选）')]:
    found = any(os.path.isdir(os.path.join(d, name)) for d in skill_dirs)
    row(f'配套技能 {name}', found, f'{why}：请用户安装到 ~/.claude/skills 或 ~/.codex/skills', 'WARN')

w = max(len(r[1]) for r in rows)
for st, name, fix in rows:
    print(f'{st:8s} {name.ljust(w)}  {fix}')
bad = [r for r in rows if r[0] == 'MISSING']
print('\n必需项都在，可以开始。' if not bad else f'\n有 {len(bad)} 个必需项缺失，先按提示补上。')
