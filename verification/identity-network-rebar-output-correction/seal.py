#!/usr/bin/env python3
"""Seal/check this exact sibling packet; no processes, network or runtime work."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
mode=sys.argv[1]
assert mode in {'create','check'}
def row(body):return {'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
def canon(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
paths=sorted(p for p in BASE.rglob('*') if p.is_file() and p.name!='packet-manifest.json')
assert all(not p.is_symlink() for p in BASE.rglob('*'))
# The copied predecessor packet-manifest is evidence, and must be included.
paths=sorted(p for p in BASE.rglob('*') if p.is_file() and p!=BASE/'packet-manifest.json')
files={str(p.relative_to(BASE)):row(p.read_bytes()) for p in paths}
for path,expected in json.loads((BASE/'source-bindings.json').read_bytes()).items():
 assert row((ROOT/path).read_bytes())==row((BASE/'after'/path).read_bytes())==expected,path
manifest={'schema':1,'files':files,'tree_digest_sha256':canon(files),'scope':'source and pure controls; fresh isolated CI and independent review pending'}
p=BASE/'packet-manifest.json'
if mode=='create':
 assert not p.exists()
 p.write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
assert json.loads(p.read_bytes())==manifest
print(json.dumps({'status':'sealed-and-checked','files':len(files),'tree_digest_sha256':canon(files),'packet_manifest':row(p.read_bytes()),'runtime_qualification':False},sort_keys=True))
