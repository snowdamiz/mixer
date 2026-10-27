#!/usr/bin/env python3
"""Record the finite model command; never execute product code or a compiler."""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import subprocess
import sys

here = Path(__file__).resolve().parent
root = here.parent.parent
mode = sys.argv[1] if len(sys.argv)>1 else 'derive'
assert mode in ('derive','check-only')
directory = here / ('command' if mode == 'derive' else 'check-command')
directory.mkdir(exist_ok=True)
command = [sys.executable,str(here/'derive.py')]+(['--check-only'] if mode=='check-only' else [])
before = (here/'derive.py').read_bytes()
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
result = subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
(directory/'stdout').write_bytes(result.stdout)
(directory/'stderr').write_bytes(result.stderr)
receipt = {'schema':1,'command':command,'cwd':str(root),'started':started,
           'finished':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'exit_code':result.returncode,'tool':'Python','version':platform.python_version(),
           'driver_sha256':hashlib.sha256(before).hexdigest(),
           'driver_unchanged':before==(here/'derive.py').read_bytes(),
           'source_tree_sha256':'5cd522af7e126d88496b5aefee722ff481821f0cf5babdbdbd7fbeba646c380b',
           'stdout_bytes':len(result.stdout),'stdout_sha256':hashlib.sha256(result.stdout).hexdigest(),
           'stderr_bytes':len(result.stderr),'stderr_sha256':hashlib.sha256(result.stderr).hexdigest(),
           'compiler_run':False,'product_or_native_run':False,
           'scope':'frozen source/MIR/layout data and pure finite arithmetic only'}
(directory/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
print(result.stdout.decode(),end='')
print(result.stderr.decode(),end='',file=sys.stderr)
sys.exit(result.returncode)
