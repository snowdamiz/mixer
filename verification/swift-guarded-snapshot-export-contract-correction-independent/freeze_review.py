#!/usr/bin/env python3
"""Freeze only this owned review after rechecking frozen input custody."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

OWN = Path(__file__).resolve().parent
def sha(b): return hashlib.sha256(b).hexdigest()
def write(p,v): p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
assert not (OWN/'seal.json').exists(), 'Never rewrite a frozen review.'
spec=importlib.util.spec_from_file_location('owned_review_functions', OWN/'run_review.py')
review=importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
observed=review.custody()
assert observed==json.loads((OWN/'input-custody-before.json').read_text())==json.loads((OWN/'input-custody-after.json').read_text())
r=json.loads((OWN/'review-result.json').read_text())
assert r['all_fresh_expectations_met'] and r['new_controls_passed']==106
assert not (OWN/'run.stderr').read_bytes()
assert not list(OWN.rglob('__pycache__'))
write(OWN/'freeze-receipt.json',{
    'schema':1, 'at':datetime.now(timezone.utc).isoformat(),
    'command':[sys.executable,'-B',str(Path(__file__).resolve())],
    'cwd':str(Path.cwd()),'python':sys.version,
    'python_executable_sha256':sha(Path(sys.executable).resolve().read_bytes()),
    'input_custody_reverified':True, 'data_controls_rerun_during_freeze':False,
    'cleanup':r['cleanup'], 'review_result_sha256':sha((OWN/'review-result.json').read_bytes()),
    'scope':'Freeze independent finite review only; no implementation selection or additional acceptance.'})
members=[{'path':p.relative_to(OWN).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
         for p in sorted(OWN.rglob('*')) if p.is_file() and p.name!='seal.json']
assert all(not (OWN/m['path']).is_symlink() for m in members)
seal={'schema':1,'member_count':len(members),'bytes':sum(m['bytes'] for m in members),
      'members':members,'tree_sha256':sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode()),
      'scope':'Frozen independent R1-R3 correction source/data review; original failures retained, no blocking finding; root remains selector; no exporter/native/OTA/GA acceptance.'}
write(OWN/'seal.json',seal)
for m in members:
    p=OWN/m['path'];assert p.stat().st_size==m['bytes'] and sha(p.read_bytes())==m['sha256']
print(json.dumps({'member_count':seal['member_count'],'bytes':seal['bytes'],'tree_sha256':seal['tree_sha256'],'seal_sha256':sha((OWN/'seal.json').read_bytes())},sort_keys=True))
