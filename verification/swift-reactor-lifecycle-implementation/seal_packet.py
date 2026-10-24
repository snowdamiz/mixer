#!/usr/bin/env python3
"""Seal this compiler-only packet after replay; never changes candidate sources."""
import hashlib,json
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
assert not (HERE/'seal.json').exists()
def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
files={str(p.relative_to(HERE)):sha(p.read_bytes()) for p in sorted(HERE.rglob('*')) if p.is_file()}
value={'schema':'mixer.swift-lifecycle.owner-entry-seal.1','observedUTC':datetime.now(timezone.utc).isoformat(),'closureSHA256':sha(encoded(files)),'files':files,'runtimeSelected':False,'accountingAccepted':False}
(HERE/'seal.json').write_bytes(encoded(value))
print(sha((HERE/'seal.json').read_bytes()))
