#!/usr/bin/env python3
"""Replay unchanged controls; confine test writes and prohibit real toolchain children."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
HERE = Path(__file__).resolve().parent
TARGET = Path(sys.argv[1]).resolve()
_original_temp = tempfile.TemporaryDirectory
_original_popen = subprocess.Popen

def owned_temp(*args, **kwargs):
    kwargs['dir'] = HERE
    return _original_temp(*args, **kwargs)

def bounded_git_only(argv, *args, **kwargs):
    if not (isinstance(argv, (list, tuple)) and str(argv[0]) == 'git' and 'sparse-checkout' in argv and 'check-rules' in argv):
        raise RuntimeError('Review refuses real child command: ' + repr(argv))
    return _original_popen(argv, *args, **kwargs)

def owned_write(event, args):
    if event == 'open':
        path, mode, flags = args
        if isinstance(path, (str, bytes)) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            p = Path(os.fsdecode(path)).absolute().resolve()
            if not p.is_relative_to(HERE):
                raise RuntimeError('Write outside review: ' + str(p))
    if event in ('os.kill', 'os.killpg', 'os.system'):
        raise RuntimeError('Review prohibits process interaction: ' + event)
sys.addaudithook(owned_write)
spec = importlib.util.spec_from_file_location('review_control_module', TARGET)
module = importlib.util.module_from_spec(spec)
with patch.object(tempfile, 'TemporaryDirectory', owned_temp), patch.object(subprocess, 'Popen', bounded_git_only):
    spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
