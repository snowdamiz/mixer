#!/usr/bin/env python3
"""Verify frozen inputs, exact command streams, corpus and optionally local outputs."""
from pathlib import Path
import argparse, gzip, hashlib, json
parser=argparse.ArgumentParser();parser.add_argument('candidate');parser.add_argument('--with-binaries',action='store_true');parser.add_argument('--check-live',action='store_true');args=parser.parse_args()
here=Path(__file__).resolve().parent;root=here.parents[1];candidate=here/args.candidate
receipt=json.loads((candidate/'receipt.json').read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
assert receipt['status']=='passed-pure-data-only-awaiting-independent-review',receipt['status']
manifest=receipt['inputManifest'];assert sha(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode())==receipt['inputTreeSHA256']
checks=0
for relative,digest in manifest.items():
 assert sha((candidate/'inputs'/relative).read_bytes())==digest,('frozen input',relative);checks+=1
 if args.check_live:assert sha((root/relative).read_bytes())==digest,('live input',relative);checks+=1
for command in receipt['commands']:
 assert command['exitCode']==0,('command',command['name'])
 assert Path(command['cwd']).is_absolute() and command['argv'],('command provenance',command['name'])
 for stream in ['stdout','stderr']:
  info=command[stream];path=root/info['path'];stored=path.read_bytes();assert sha(stored)==info['storedSHA256'],path
  raw=gzip.decompress(stored) if path.suffix=='.gz' else stored
  assert len(raw)==info['bytes'] and sha(raw)==info['sha256'],path;checks+=1
for relative,info in receipt['artifacts'].items():
 if '/.build/' in relative and not args.with_binaries:continue
 path=root/relative;data=path.read_bytes();assert len(data)==info['bytes'] and sha(data)==info['sha256'],path;checks+=1
for variant,files in receipt.get('variantSourceManifests',{}).items():
 for relative,digest in files.items():
  assert digest==manifest[relative],('variant source differs',variant,relative)
  if args.with_binaries:
   path=here/'.build'/args.candidate/variant/'inputs'/relative
   assert sha(path.read_bytes())==digest,path;checks+=1
for path in candidate.glob('mismatches-*.json'):assert json.loads(path.read_text())==[],path
assert len(receipt['differentialModes'])==2
assert len({(v['cases'],v['accepted'],v['rejected']) for v in receipt['differentialModes']})==1
print('PASS frozen data evidence seal checks='+str(checks)+'; no native or GA authority')
