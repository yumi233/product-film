"""Speech-free video prompts and separately supplied post-production narration."""
import math
from pathlib import Path


VIDEO_AUDIO_RULE = (
    'AUDIO REQUIREMENT: Generate only natural non-verbal location ambience and '
    'synchronized sound effects appropriate to the visible scene (for example '
    'wind, water, rain, footsteps, pouring and cups). No narration, no voice-over, '
    'no spoken dialogue, no intelligible speech, no singing and no music. '
    'People remain silent. Narration and music will be added separately in post-production.'
)


def generation_prompt(prompt):
    text = prompt.strip()
    return text if VIDEO_AUDIO_RULE in text else text + '\n\n' + VIDEO_AUDIO_RULE


def source_audio_mode(config, clip):
    """Only source audio explicitly auditioned as speech-free may reach the mix."""
    mode = clip.get('source_audio', config.get('source_audio', 'mute'))
    if mode not in ('mute', 'verified_ambience'):
        raise ValueError('source_audio must be mute or verified_ambience; audition the clip before retaining ambience.')
    return mode


def narration_source(config, line, base):
    if line.get('path'):
        path = Path(line['path'])
    elif config.get('dir') and line.get('id'):
        path = Path(config['dir']) / (line['id'] + '.wav')
    else:
        raise ValueError('Supply narration as vo.lines[].path, or vo.dir plus a line id; Qwen3 is optional.')
    return path if path.is_absolute() else Path(base) / path


def validate_audio_inputs(config, base):
    for clip in config.get('clips', []):
        source_audio_mode(config, clip)
    voice = config.get('vo') or {}
    tempo = float(voice.get('tempo', 1.0))
    if not math.isfinite(tempo) or tempo <= 0:
        raise ValueError('vo.tempo must be a finite positive number.')
    seen = set()
    for line in voice.get('lines', []):
        identifier = line.get('id')
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise ValueError('Each narration line needs a unique non-empty id.')
        seen.add(identifier)
        path = narration_source(voice, line, base)
        if not path.is_file():
            raise FileNotFoundError(f'Please provide the recorded narration audio before mixing: {path}. Qwen3 is optional.')
