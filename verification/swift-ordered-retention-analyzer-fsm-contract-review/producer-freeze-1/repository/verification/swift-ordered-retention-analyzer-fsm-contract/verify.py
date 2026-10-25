#!/usr/bin/env python3
"""Read-only owned seal/upstream verification and finite host model rerun."""
import json
import os
from pathlib import Path
import subprocess
import sys
from run_checks import BASE,ROOT,digest,upstream
assert sys.dont_write_bytecode
assert digest(BASE/'seal.json')==(BASE/'seal.sha256').read_text().strip()
seal=json.loads((BASE/'seal.json').read_bytes())
actual={'docs/swift-ordered-retention-analyzer-fsm-contract.md'}|{
 str(p.relative_to(ROOT)) for p in BASE.rglob('*') if p.is_file() and p.name not in ('seal.json','seal.sha256')}
assert actual=={r['path'] for r in seal['members']}
for row in seal['members']:
 p=ROOT/row['path'];assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256'],row['path']
before=upstream()
r=json.loads((BASE/'commands/run-5/result.json').read_bytes())
assert r['passed'] and r['upstream_before']==r['upstream_after']==before
for row in r['source_snapshot']:
 p=BASE/'inputs/run-5'/row['path'].replace('/','__')
 assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
for row in r['finite_sources']:
 assert digest(ROOT/row['path'])==row['sha256']
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(BASE),'-p','test_model.py','-v'],cwd=ROOT,env=env,check=True,timeout=60)
assert digest(ROOT/r['layout_binary']['path'])==r['layout_binary']['sha256']
subprocess.run([str(ROOT/r['layout_binary']['path'])],cwd=ROOT,env=env,check=True,timeout=60)
assert before==upstream()
print('Verified sealed preparatory fixture FSM contract only; semantic and implementation acceptance unavailable.')
