#!/usr/bin/env python3
"""Read-only adapter verification with process and V3 runtime execution blocked."""
import json
import pathlib
import runpy
import sys
BASE = pathlib.Path(__file__).resolve().parent
PREP = BASE.parent/'apple-toggle-keyboard-full-case-preparation-v3'
PROTECTED = {str(PREP/name) for name in json.loads((PREP/'runtime-selection.json').read_bytes())['files'] if name.endswith('.py')}


def audit(event, args):
    if event in ['subprocess.Popen', 'os.system', 'os.posix_spawn']:
        raise RuntimeError('Process/native operation forbidden in adapter verification')
    if event == 'exec' and args[0].co_filename in PROTECTED:
        raise RuntimeError('Selected V3 runtime execution forbidden in adapter verification')


sys.addaudithook(audit)
sys.argv = [str(BASE/'adapter.py'), 'verify']
runpy.run_path(str(BASE/'adapter.py'), run_name='__main__')
