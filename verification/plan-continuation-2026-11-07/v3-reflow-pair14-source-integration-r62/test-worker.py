#!/usr/bin/env python3
"""Run unchanged Python controls with their explicit /tmp scratch under userdata."""
import os
import runpy
import sys
import tempfile

# Some existing fixtures explicitly use /tmp rather than respecting TMPDIR.
# This changes only their scratch parent; no assertions or product code change.
original = tempfile.TemporaryDirectory
def owned_temporary_directory(*args, **kwargs):
    if kwargs.get('dir') == '/tmp':
        kwargs['dir'] = os.environ['TMPDIR']
    return original(*args, **kwargs)
tempfile.TemporaryDirectory = owned_temporary_directory
argv = sys.argv[1:]
if argv[:2] == ['-m','unittest']:
    sys.argv = argv[1:]
    runpy.run_module('unittest',run_name='__main__',alter_sys=True)
else:
    sys.argv = argv
    sys.path.insert(0,os.path.dirname(os.path.abspath(argv[0])))
    runpy.run_path(argv[0],run_name='__main__')
