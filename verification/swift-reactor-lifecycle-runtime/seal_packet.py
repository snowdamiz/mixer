#!/usr/bin/env python3
"""Seal a preserved failed run and unimplemented proposal exactly once."""
from pathlib import Path
import hashlib, json

HERE=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def enc(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
assert not (HERE/'seal.json').exists()
files={str(p.relative_to(HERE)):sha(p.read_bytes())for p in sorted(HERE.rglob('*'))if p.is_file()}
seal={'schema':'mixer.swift-lifecycle.runtime-failure-seal.1','sourceClosure':'0b36b551e2175aa713d698627493519249b6bfea023f05e13de730e6b06f977f','runtimeAccepted':False,'repairImplemented':False,'closureSHA256':sha(enc(files)),'files':files}
(HERE/'seal.json').write_bytes(enc(seal))
print(json.dumps({'sealSHA256':sha((HERE/'seal.json').read_bytes()),'closureSHA256':seal['closureSHA256'],'files':len(files),'runtimeAccepted':False,'repairImplemented':False},sort_keys=True,indent=2))
