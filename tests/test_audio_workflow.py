"""Offline audio routing checks; no model, account or paid service is called.

Run with the normal numpy/scipy/Pillow dependencies:
    python3 -m unittest discover -s tests -v
"""
import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audio_policy import VIDEO_AUDIO_RULE, narration_source, source_audio_mode, validate_audio_inputs
import rh_run


class AudioInputTests(unittest.TestCase):
    def test_unreviewed_source_is_muted_and_review_can_be_per_clip(self):
        self.assertEqual(source_audio_mode({'ambience': 1}, {}), 'mute')
        self.assertEqual(source_audio_mode({}, {'source_audio': 'verified_ambience'}), 'verified_ambience')
        self.assertEqual(source_audio_mode({'source_audio': 'verified_ambience'}, {'source_audio': 'mute'}), 'mute')

    def test_missing_user_recording_is_reported_before_encoding(self):
        with tempfile.TemporaryDirectory() as base:
            config = {'vo': {'lines': [{'id': 'N01', 'path': 'missing.m4a'}]}}
            with self.assertRaisesRegex(FileNotFoundError, 'provide the recorded narration'):
                validate_audio_inputs(config, base)

    def test_original_qwen_output_layout_remains_compatible(self):
        with tempfile.TemporaryDirectory() as base:
            file = Path(base) / 'vo' / 'N01.wav'
            file.parent.mkdir()
            file.touch()
            config = {'vo': {'dir': 'vo', 'tempo': .92, 'lines': [{'id': 'N01'}]}}
            validate_audio_inputs(config, base)
            self.assertEqual(narration_source(config['vo'], {'id': 'N01'}, base), file)

    def test_video_request_transmits_ambience_only_rule_without_calling_api(self):
        submitted = []
        def fake_post(path, payload):
            submitted.append(payload)
            return {'code': 0, 'data': {'taskId': 'offline-test'}}
        with tempfile.TemporaryDirectory() as base:
            with patch.object(rh_run, 'upload', return_value='reference.jpg'), \
                 patch.object(rh_run, 'post', side_effect=fake_post), \
                 patch.object(rh_run, 'key', return_value='offline-test'), \
                 patch.object(rh_run, 'fetch', return_value='offline.mp4'), \
                 contextlib.redirect_stdout(io.StringIO()):
                rh_run.run('test', 'Pour water into the open teapot.', ['reference.jpg'], out_dir=base)
        node = next(n for n in submitted[0]['nodeInfoList'] if n['nodeId'] == rh_run.PROMPT_NODE)
        self.assertIn(VIDEO_AUDIO_RULE, node['fieldValue'])


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg and ffprobe are required')
class MixIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        import cut
        cls.np, cls.cut = np, cut
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        cls.source = cls.base / 'video-with-source-tone.mp4'
        cls.run_ffmpeg('-f', 'lavfi', '-i', 'color=c=gray:s=320x180:r=24:d=2',
                       '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100:duration=2',
                       '-c:v', 'libx264', '-c:a', 'aac', '-shortest', str(cls.source))
        for suffix in ('wav', 'mp3', 'm4a', 'flac'):
            cls.run_ffmpeg('-f', 'lavfi', '-i', 'sine=frequency=880:sample_rate=44100:duration=0.7',
                           str(cls.base / f'user-recording.{suffix}'))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @staticmethod
    def run_ffmpeg(*args):
        subprocess.run(['ffmpeg', '-y', '-v', 'error', *args], check=True, capture_output=True)

    def level(self, path, frequency):
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-ss', '0.3', '-t', '0.4',
                              '-f', 'f64le', '-ac', '1', '-ar', '44100', '-'], check=True, capture_output=True).stdout
        samples = self.np.frombuffer(raw, dtype='<f8')
        times = self.np.arange(len(samples)) / 44100
        return abs(self.np.mean(samples * self.np.exp(-2j * self.np.pi * frequency * times))) * 2

    def render(self, name, clip_mode=None, voice_suffix=None):
        output = self.base / (name + '.mp4')
        clip = {'path': self.source.name}
        if clip_mode:
            clip['source_audio'] = clip_mode
        config = {'output': output.name, 'clips': [clip], 'align': False, 'fade': [0, .05], 'ambience': 1.0}
        if voice_suffix:
            config['vo'] = {'lines': [{'id': 'N01', 'path': f'user-recording.{voice_suffix}', 'seg': 0, 'at': .1}]}
        file = self.base / (name + '.json')
        file.write_text(json.dumps(config))
        # Isolate the audio sources under test from the independently synthesized score.
        with patch.object(self.cut, 'W', 320), patch.object(self.cut, 'H', 180), \
             patch.object(self.cut.score, 'render', side_effect=lambda cues, total: self.np.zeros(int(total * 44100))), \
             contextlib.redirect_stdout(io.StringIO()):
            self.cut.main(str(file))
        return output

    def test_unreviewed_generated_audio_cannot_leak_into_output(self):
        output = self.render('mute')
        self.assertLess(self.level(output, 440), .001)

    def test_verified_model_ambience_is_retained(self):
        output = self.render('verified', clip_mode='verified_ambience')
        self.assertGreater(self.level(output, 440), .02)

    def test_user_recordings_mix_without_qwen_in_all_supported_formats(self):
        for suffix in ('wav', 'mp3', 'm4a', 'flac'):
            with self.subTest(format=suffix):
                output = self.render('user-' + suffix, voice_suffix=suffix)
                self.assertGreater(self.level(output, 880), .05)
                self.assertLess(self.level(output, 440), .003)

    def test_user_voice_and_verified_model_ambience_can_coexist(self):
        output = self.render('voice-and-ambience', clip_mode='verified_ambience', voice_suffix='wav')
        self.assertGreater(self.level(output, 880), .05)
        self.assertGreater(self.level(output, 440), .01)

    def test_overlong_user_recording_is_not_silently_truncated(self):
        config = {'output': 'overlong.mp4', 'clips': [{'path': self.source.name}],
                  'vo': {'lines': [{'id': 'N01', 'path': 'user-recording.wav', 'seg': 0, 'at': 1.8}]}}
        path = self.base / 'overlong.json'
        path.write_text(json.dumps(config))
        with patch.object(self.cut, 'W', 320), patch.object(self.cut, 'H', 180), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, 'runs outside the edit'):
                self.cut.main(str(path))


if __name__ == '__main__':
    unittest.main()
