"""Offline checks for the v16 tools (no account or paid service is called).

    python3 -m unittest discover -s tests -v
"""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import music_phrases, qc, rh_run, stable_window


class V16ToolTests(unittest.TestCase):
    def test_refs_over_five_are_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'jobs.json'
            p.write_text(json.dumps([{'name': 'a', 'refs': ['x'] * 6}, {'name': 'b', 'refs': ['x'] * 5}]))
            self.assertEqual(qc.refs(str(p)), 1)

    def test_rh_run_keeps_at_most_five_refs(self):
        seen = {}
        with tempfile.TemporaryDirectory() as d, \
                patch.object(rh_run, 'upload', side_effect=lambda p: p), \
                patch.object(rh_run, 'post', side_effect=lambda *a, **k: {'code': 1, 'msg': 'stop'}), \
                patch.object(rh_run, 'key', return_value='k'):
            def capture(*a, **k):
                seen['nodes'] = a[1]['nodeInfoList']; return {'code': 1, 'msg': 'stop'}
            rh_run.post.side_effect = capture
            rh_run.run('t', 'p', [f'r{i}' for i in range(7)], out_dir=d)
        images = [n['fieldValue'] for n in seen['nodes'] if n['fieldName'] == 'image']
        self.assertTrue(all(v in [f'r{i}' for i in range(5)] for v in images))

    def test_music_phrase_onsets_follow_entries(self):
        sr = 11025
        x = np.zeros(sr * 20)
        for t in (5, 12):                      # two loud entries after silence
            x[t * sr:(t + 3) * sr] = 0.3 * np.sin(np.arange(3 * sr) * 2 * np.pi * 220 / sr)
        with tempfile.TemporaryDirectory() as d:
            w = Path(d) / 'm.wav'; wavfile.write(w, sr, (x * 32767).astype(np.int16))
            _, on = music_phrases.onsets(str(w))
        self.assertEqual([round(t) for t in on], [5, 12])

    def test_stable_window_avoids_the_jump(self):
        with tempfile.TemporaryDirectory() as d:
            v = Path(d) / 'v.mp4'
            # smooth pan for 4 s, then a hard flash in the last second
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=s=320x180:r=24:d=5',
                            '-vf', "drawbox=enable='gte(t,4)*mod(n,2)':c=white:t=fill", str(v)], check=True)
            t, e, score = stable_window.best_window(str(v), 2.0)
        self.assertLessEqual(e, 4.05)


if __name__ == '__main__':
    unittest.main()
