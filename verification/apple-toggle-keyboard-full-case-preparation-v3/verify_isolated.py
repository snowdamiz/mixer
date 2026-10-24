#!/usr/bin/env python3
"""Execute the complete sealed preflight with runtime execution/processes forbidden."""
import pathlib
import json
import runpy
import sys
BASE=pathlib.Path(__file__).resolve().parent
PROTECTED={str(BASE/name) for name in json.loads((BASE/'runtime-selection.json').read_bytes())['files'] if name.endswith('.py')}

def audit(event,args):
    if event in ['subprocess.Popen','os.system']:raise RuntimeError('Process/native operation forbidden during sealed preflight')
    if event=='exec':
        name=args[0].co_filename
        if name in PROTECTED:
            raise RuntimeError('Runtime source execution forbidden during sealed preflight')
sys.addaudithook(audit)
sys.argv=[str(BASE/'run.py'),'verify']
runpy.run_path(str(BASE/'run.py'),run_name='__main__')
