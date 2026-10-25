#!/usr/bin/env python3
"""Read-only finite-support verification; no full replay/analyzer qualification."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while b:=f.read(65536):h.update(b)
    return h.hexdigest()
assert sys.dont_write_bytecode
assert digest(BASE/'seal.json')==(BASE/'seal.sha256').read_text().strip()
seal=json.loads((BASE/'seal.json').read_bytes())
actual={'docs/swift-ordered-retention-analyzer.md'}|{
    str(p.relative_to(ROOT)) for p in BASE.rglob('*') if p.is_file()
    and p.name not in ('seal.json','seal.sha256')}
assert actual=={m['path'] for m in seal['members']}
for row in seal['members']:
    p=ROOT/row['path'];assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
result=json.loads((BASE/'result.json').read_bytes())
for upstream in result['upstream_after']:
    p=ROOT/upstream['seal'];assert digest(p)==upstream['sha256']
    for row in json.loads(p.read_bytes())['members']:
        member=ROOT/row['path'];assert member.stat().st_size==row['bytes']
        assert digest(member)==row['sha256']
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(BASE),
                '-p','test_model.py','-v'],cwd=ROOT,env=env,check=True,timeout=60)
binary=ROOT/result['binary']['path'];assert digest(binary)==result['binary']['sha256']
carried=result.get('carried_layout')
if carried:
    assert digest(ROOT/carried['receipt'])==carried['receipt_sha256']
    assert digest(BASE/'layout.rs')==carried['layout_source_sha256']
    assert digest(Path(result['tools']['rustc']['path']))==carried['compiler_sha256']
    assert carried['actual_compile_or_layout_rerun'] is False
else:
    subprocess.run([str(binary)],cwd=ROOT,env=env,check=True,timeout=60)
print('Verified sealed finite design controls only; full analyzer and target acceptance pending.')
