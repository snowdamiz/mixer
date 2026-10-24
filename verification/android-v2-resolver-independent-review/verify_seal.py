#!/usr/bin/env python3
"""Replay review evidence integrity, with optional local compiled-output checks.
This verifies host data evidence only. It cannot grant any native/release authority.
"""
from pathlib import Path
import argparse, gzip, hashlib, json

parser=argparse.ArgumentParser();parser.add_argument('candidate')
parser.add_argument('--check-live',action='store_true');parser.add_argument('--with-binaries',action='store_true')
args=parser.parse_args();here=Path(__file__).resolve().parent;root=here.parents[1];out=here/args.candidate
sha=lambda b:hashlib.sha256(b).hexdigest();receipt=json.loads((out/'receipt.json').read_text());checks=0
assert receipt['format']=='mixer.android-v2-resolver-independent-review.1'
assert receipt['status']=='passed-host-data-independent-review' and receipt['findings']==[]
manifest=receipt['inputManifest'];assert sha(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode())==receipt['inputTreeSHA256']
for relative,digest in manifest.items():
    assert sha((out/'inputs'/relative).read_bytes())==digest,('frozen input',relative);checks+=1
    if args.check_live:assert sha((root/relative).read_bytes())==digest,('live input',relative);checks+=1
for command in receipt['commands']:
    assert command['argv'] and Path(command['cwd']).is_absolute()
    if command['expectedNonzero']:assert command['exitCode']!=0 and command['expectedFailureMarker']
    else:assert command['exitCode']==0
    for stream in ['stdout','stderr']:
        record=command[stream];data=(root/record['path']).read_bytes()
        assert len(data)==record['bytes'] and sha(data)==record['sha256'],('command stream',command['name'],stream);checks+=1
    if command['expectedNonzero']:
        combined=(root/command['stdout']['path']).read_text()+(root/command['stderr']['path']).read_text()
        assert command['expectedFailureMarker'] in combined
for relative,record in receipt['artifacts'].items():
    if '/.build/' in relative and not args.with_binaries:continue
    data=(root/relative).read_bytes();assert len(data)==record['bytes'] and sha(data)==record['sha256'],('artifact',relative);checks+=1
    if relative.endswith('.class'):assert data[:4]==bytes.fromhex('CAFEBABE') and int.from_bytes(data[6:8],'big')==61
for variant,files in receipt['variantSourceManifests'].items():
    for relative,digest in files.items():
        assert digest==manifest[relative],('variant source',variant,relative)
        if args.with_binaries:assert sha((out/'.build'/variant/'inputs'/relative).read_bytes())==digest;checks+=1
assert len(receipt['mutations'])==8
for mutation in receipt['mutations']:
    assert mutation['result']=='detected-by-reviewer-oracle'
    original=(out/'inputs'/mutation['target']).read_text();assert original.count(mutation['original'])==mutation['occurrences']
    altered=original.replace(mutation['original'],mutation['replacement']).encode()
    assert sha(altered)==mutation['sourceManifest'][mutation['target']]
    for relative,digest in mutation['sourceManifest'].items():
        if relative!=mutation['target']:assert digest==manifest[relative]
        if args.with_binaries:assert sha((out/'.build'/'mutations'/mutation['name']/'inputs'/relative).read_bytes())==digest;checks+=1
audit=receipt['producerAudit']
assert audit==json.loads((out/'producer-output-audit.json').read_text())
assert audit['producerReceiptSHA256']==sha((root/'verification/android-appearance-v2-resolution/candidate-5/receipt.json').read_bytes())
for stream in audit['streams'].values():
    path=root/stream['path'];stored=path.read_bytes();assert sha(stored)==stream['storedSHA256']
    data=gzip.decompress(stored) if path.suffix=='.gz' else stored
    assert len(data)==stream['bytes'] and sha(data)==stream['sha256'];checks+=1
assert len(set(receipt['results']))==1 and receipt['results'][0]=='PASS reviewer oracle acceptedPreparations=23 explicitRejections=115 assertions=6279; host pure data only'
assert not any(receipt['physicalDevices'].values()) and not receipt['liveInputChangesSinceSnapshot']
print('PASS independent review evidence seal checks='+str(checks)+'; host pure data only, no native or GA authority')
