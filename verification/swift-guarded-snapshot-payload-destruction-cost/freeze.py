#!/usr/bin/env python3
"""Freeze/check this packet only; never mutate an immutable input packet."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def digest(raw): return hashlib.sha256(raw).hexdigest()
def canonical(obj): return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()
def members():
    answer=[]
    for path in sorted(HERE.rglob('*')):
        if not path.is_file() or path==HERE/'seal.json': continue
        if '__pycache__' in path.parts: raise AssertionError('unexpected bytecode cache')
        raw=path.read_bytes()
        answer.append({'path':str(path.relative_to(HERE)),'bytes':len(raw),'sha256':digest(raw)})
    return answer
if '--check-only' in sys.argv:
    seal=json.loads((HERE/'seal.json').read_bytes())
    observed=members()
    assert seal['members']==observed
    assert seal['tree_sha256']==digest(canonical(observed))
    assert seal['member_count']==len(observed)
    assert seal['member_bytes']==sum(r['bytes'] for r in observed)
    print('payload packet seal verified: '+str(len(observed))+' members')
else:
    assert not (HERE/'seal.json').exists(), 'already frozen'
    stdout=b'payload packet seal written\n'
    (HERE/'freeze.stdout').write_bytes(stdout)
    (HERE/'freeze.stderr').write_bytes(b'')
    receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'argv':[sys.executable,str(HERE/'freeze.py')],'cwd':str(Path.cwd()),
        'python':platform.python_version(),'python_executable':str(Path(sys.executable).resolve()),
        'python_executable_sha256':digest(Path(sys.executable).resolve().read_bytes()),
        'freeze_program_sha256':digest((HERE/'freeze.py').read_bytes()),
        'stdout_sha256':digest(stdout),'stderr_sha256':digest(b''),'exit_code':0,
        'scope':'hash only the owned completed packet; no subprocess/runtime or input mutation'}
    (HERE/'freeze-command.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    observed=members()
    seal={'schema':1,'member_count':len(observed),'member_bytes':sum(r['bytes'] for r in observed),
          'tree_sha256':digest(canonical(observed)),'members':observed,
          'scope':'conditional source146 payload-cost interface candidate; no whole-host acceptance'}
    (HERE/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
    sys.stdout.buffer.write(stdout)
