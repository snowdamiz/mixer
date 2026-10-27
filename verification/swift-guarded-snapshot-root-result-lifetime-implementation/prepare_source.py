#!/usr/bin/env python3
"""Copy only frozen source146 and byte-identical host11, never evidence/builds."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
BASE = ROOT / 'verification/swift-guarded-snapshot-actual-owner-rust-retirement-correction'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def fingerprint(path):
    data = path.read_bytes()
    return {'path':str(path.relative_to(ROOT)), 'bytes':len(data), 'sha256':digest(data)}

assert digest((BASE/'seal.json').read_bytes()) == '46d811b1264770604106b061386e6eba01ea07e55590240eff722c36af4bcaa0'
assert not (PACKET/'source').exists(), 'Do not replace an existing source candidate'
origin = {'schema':1, 'base_seal':fingerprint(BASE/'seal.json'), 'source_work_only':True, 'source':{}, 'host':{}}
for lane, manifest_name, count in [('vm','source-manifest.json',146),('host','host-manifest.json',11)]:
    manifest=json.loads((BASE/manifest_name).read_text())
    assert manifest['member_count'] == count == len(manifest['members'])
    for member in manifest['members']:
        source=BASE/'source'/lane/member['path']
        data=source.read_bytes()
        assert len(data)==member['bytes'] and digest(data)==member['sha256'], member['path']
        target=PACKET/'source'/lane/member['path']
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
    origin['source' if lane=='vm' else 'host']={'manifest':fingerprint(BASE/manifest_name),'count':count,'tree_sha256':manifest['tree_sha256']}
(PACKET/'source-origin.json').write_text(json.dumps(origin,indent=2)+'\n')
print(json.dumps({'source_members':146,'unchanged_host_members':11,'compiler_execution':False}))
