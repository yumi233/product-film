"""Narration with local Qwen3-TTS (mlx-audio) + read-back check with local Qwen3-ASR.

    python3 vo.py lines.json audio/vo/            # lines.json: [{"id": "L1", "text": "竹有节，"}, ...]
    python3 vo.py --say "器物在变，" audio/vo/L5.wav

The Qwen3-TTS folder must hold .venv/ (with mlx-audio) and models/ (Qwen3-TTS-12Hz-0.6B-CustomVoice-4bit,
Qwen3-ASR-0.6B-8bit). It is taken from env QWEN3_TTS_DIR, else the first of ~/qwen3-tts, ~/AI/qwen3-tts* that exists.
Defaults: voice Uncle_Fu, documentary instruct. Slow-down (0.92x) and silence trimming happen in cut.py, not here.
Prints duration and the ASR transcript per line; homophones in the transcript (查/茶) are fine, missing or extra
words are not -> regenerate that line. Lines longer than ~1.4 s per 4 characters usually have long pauses: split them.
"""
import glob, json, os, shutil, subprocess, sys, tempfile

def tts_dir():
    if os.environ.get('QWEN3_TTS_DIR'): return os.path.expanduser(os.environ['QWEN3_TTS_DIR'])
    for c in [os.path.expanduser('~/qwen3-tts')] + sorted(glob.glob(os.path.expanduser('~/AI/qwen3-tts*'))):
        if os.path.isdir(os.path.join(c, 'models')): return c
    sys.exit('Optional Qwen3-TTS was not found. Ask the user for recorded narration (WAV/MP3/M4A/FLAC) '
             'and import it into cut.py with vo.lines[].path. Do not generate narration inside video clips.')


Q = tts_dir()
PY = f'{Q}/.venv/bin/python'
TTS = f'{Q}/models/Qwen3-TTS-12Hz-0.6B-CustomVoice-4bit'
ASR = f'{Q}/models/Qwen3-ASR-0.6B-8bit'
VOICE = os.environ.get('VO_VOICE', 'Uncle_Fu')
INSTRUCT = os.environ.get('VO_INSTRUCT', '用低沉、温润、缓慢的纪录片旁白语气朗读，语气平静克制。')
# Voice clone (recommended for a whole film): VO_REF=ref.wav VO_REF_TEXT="transcript of ref.wav".
# Every line is then spoken by the same cloned voice with the Base model; CustomVoice + instruct re-imagines the
# speaker per line and pitch drifted 86-210 Hz across 13 lines.
REF, REF_TEXT = os.environ.get('VO_REF'), os.environ.get('VO_REF_TEXT', '')
BASE = f'{Q}/models/Qwen3-TTS-12Hz-0.6B-Base-4bit'
TEMP = os.environ.get('VO_TEMP', '0.6')


def say(text, out):
    d = tempfile.mkdtemp(prefix='vo_')
    if REF:
        args = ['--model', BASE, '--ref_audio', REF, '--ref_text', REF_TEXT]
    else:
        args = ['--model', TTS, '--voice', VOICE, '--instruct', INSTRUCT]
    subprocess.run([PY, '-m', 'mlx_audio.tts.generate', *args, '--text', text, '--temperature', TEMP,
                    '--lang_code', 'Chinese', '--output_path', d, '--file_prefix', 'x',
                    '--join_audio', '--audio_format', 'wav'], capture_output=True)
    wav = [f for f in os.listdir(d) if f.endswith('.wav')]
    if not wav: print('FAIL', text); return None
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    shutil.move(os.path.join(d, wav[0]), out)  # move, not rename: out may be on another disk
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', out],
                               capture_output=True, text=True).stdout)
    t = tempfile.mktemp()
    subprocess.run([PY, '-m', 'mlx_audio.stt.generate', '--model', ASR, '--audio', out, '--output-path', t], capture_output=True)
    heard = open(t + '.txt').read().strip() if os.path.exists(t + '.txt') else '?'
    print(f'{os.path.basename(out)}\t{dur:.2f}s\t{text}\t-> {heard}')
    return out


if __name__ == '__main__':
    if sys.argv[1] == '--say':
        say(sys.argv[2], sys.argv[3])
    else:
        for ln in json.load(open(sys.argv[1])):
            say(ln['text'], os.path.join(sys.argv[2], f"{ln['id']}.wav"))
