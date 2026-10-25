#!/usr/bin/env python3
"""Restore only the two sealed finite-test closures; never execute either one."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile
H=Path(__file__).resolve().parent
subprocess.run([sys.executable,str(H/'verify.py')],check=True)
for label,manifest_name in [('baseline','baseline-test-manifest.json'),('candidate','candidate-manifest.json')]:
    destination=H/label
    assert not destination.exists(),f'refusing existing {destination}'
    expected=json.loads((H/manifest_name).read_text())
    with tarfile.open(H/f'{label}-source.tar.gz','r:gz') as archive:
        members=archive.getmembers()
        assert len(members)==len(expected) and {m.name for m in members}==set(expected)
        payloads={m.name:archive.extractfile(m).read() for m in members if m.isfile()}
    assert {n:hashlib.sha256(b).hexdigest() for n,b in payloads.items()}==expected
    for n,b in payloads.items():
        p=destination/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
print(json.dumps({'restored':['baseline','candidate'],'executedTests':False}))
