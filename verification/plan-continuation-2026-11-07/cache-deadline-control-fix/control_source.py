"""Exact new helper derivative; every original test method remains byte-identical."""
import hashlib
from pathlib import Path
from local_support import HERE, original_source


def control_source():
    source = original_source()
    start = source.index(b' def deadline_control(self,stage):\n')
    end = source.index(b' def test_postflight_deadline_is_terminal_and_preserves_scratch', start)
    replacement = (b' def deadline_control(self,stage):\n'
                   b'  from deadline_control import run\n'
                   b'  run(self,r,HERE,stage)\n')
    derived = source[:start] + replacement + source[end:]
    expected = (HERE / 'runner-controls.py').read_bytes()
    if derived != expected:
        raise RuntimeError('Exact deadline helper derivative differs')
    return derived
