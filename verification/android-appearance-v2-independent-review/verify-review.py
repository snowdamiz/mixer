#!/usr/bin/env python3
"""Check retained review evidence; --with-binaries also checks local build output.

This checks binding integrity only. It does not rerun product execution or grant
native/signing/release authority.
"""
from pathlib import Path
import argparse,gzip,hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--with-binaries',action='store_true');args=parser.parse_args()
r=json.loads((HERE/'acceptance.json').read_text())
if r['status']!='recommended-data-only':raise RuntimeError('not a scoped recommendation')
checked=0
for path,digest in r['bindings'].items():
    if sha(ROOT/path)!=digest:raise RuntimeError('binding changed '+path)
    checked+=1
for item in r['compressedManifests']:
    raw=gzip.decompress((ROOT/item['path']).read_bytes())
    if hashlib.sha256(raw).hexdigest()!=item['uncompressedSHA256']:raise RuntimeError('compressed manifest mismatch')
    checked+=1
binary_count=0
for relative in ['candidate-2/acceptance.json','byte-boundaries/receipt.json']:
    receipt=json.loads((HERE/relative).read_text())
    if receipt['status'] not in ['recommended-data-only','passed-byte-boundary-data-only']:raise RuntimeError('unqualified receipt')
    for command in receipt['commands']:
        if command['exit']!=0 or sha(ROOT/command['log'])!=command['sha256']:raise RuntimeError('execution log mismatch')
        if Path(command['cwd'])!=HERE/'candidate-2/inputs':raise RuntimeError('unexpected execution cwd')
        checked+=1
    if args.with_binaries:
        for path,digest in receipt['artifacts'].items():
            artifact=ROOT/path
            if sha(artifact)!=digest:raise RuntimeError('binary changed '+path)
            if artifact.suffix=='.class' and artifact.read_bytes()[:8]!=b'\xca\xfe\xba\xbe\x00\x00\x00=':raise RuntimeError('class not Java 17 target')
            binary_count+=1
for relative in ['candidate-2/input-manifest.json','byte-boundaries/input-manifest.json']:
    manifest=json.loads((HERE/relative).read_text())
    for path,digest in manifest.items():
        if relative.startswith('candidate-2/'):
            copies=[ROOT/path,HERE/'candidate-2/inputs'/path]
        else:copies=[ROOT/path]
        for copy in copies:
            if sha(copy)!=digest:raise RuntimeError('frozen input changed '+str(copy))
            checked+=1
print(json.dumps({'status':'retained-review-bindings-valid','bindingsLogsAndCopyChecks':checked,'localClassAndExecutableDigestsChecked':binary_count,'scope':'binding integrity only; retained executed receipts provide host data results'},sort_keys=True))
