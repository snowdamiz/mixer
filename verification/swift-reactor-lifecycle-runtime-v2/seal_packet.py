#!/usr/bin/env python3
"""Freeze the V2 failure evidence exactly once; no source/test execution."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def enc(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
assert not (HERE/'seal.json').exists()
files={str(p.relative_to(HERE)):sha(p.read_bytes())for p in sorted(HERE.rglob('*'))if p.is_file()}
value={'schema':'mixer.swift-lifecycle.runtime-v2-failure-seal.1','candidateClosure':'0fa7ae254ac2b3aa3390e6fbc935e920422fc9024db220256074ec6ef4e3cd56','closureSHA256':sha(enc(files)),'files':files,'runtimeAccepted':False,'nextRepairImplemented':False}
destination=HERE/'seal.json';destination.write_bytes(enc(value));print(json.dumps({'sealSHA256':sha(destination.read_bytes()),'closureSHA256':value['closureSHA256'],'files':len(files)},sort_keys=True,indent=2))
