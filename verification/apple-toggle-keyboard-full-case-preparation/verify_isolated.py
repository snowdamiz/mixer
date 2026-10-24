#!/usr/bin/env python3
"""Execute the complete sealed preflight with runtime execution/processes forbidden."""
import pathlib
import runpy
import sys
BASE=pathlib.Path(__file__).resolve().parent

def audit(event,args):
    if event in ['subprocess.Popen','os.system']:raise RuntimeError('Process/native operation forbidden during sealed preflight')
    if event=='exec':
        name=args[0].co_filename
        if name==str(BASE/'composition.py') or str(BASE/'inputs/runtime/') in name:
            raise RuntimeError('Runtime source execution forbidden during sealed preflight')
sys.addaudithook(audit)
sys.argv=[str(BASE/'run.py'),'verify']
runpy.run_path(str(BASE/'run.py'),run_name='__main__')
