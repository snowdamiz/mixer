#!/usr/bin/env python3
"""Freeze/check only this independent native review packet."""
import argparse,datetime,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OWN=Path(__file__).resolve().parent
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');a=parser.parse_args()
 manifest=OWN/'manifest.json';files={str(p.relative_to(ROOT)):identity(p) for p in sorted(OWN.rglob('*')) if p.is_file() and p!=manifest}
 acceptance=json.loads((OWN/'acceptance.json').read_text());assert acceptance['decision']=='recommend-accept-exact-bounded-A-native-development-scope'
 for attempt in ('attempt-1','attempt-2'):
  r=json.loads((OWN/attempt/'receipt.json').read_text());assert r['cleanup']['owned_scratch_removed'] and r['cleanup']['owned_children_reaped']
  assert r['frozen_inputs_stable']
 assert json.loads((OWN/'attempt-2/receipt.json').read_text())['status']=='passed-independent-host-crosscompile-and-inspection-only'
 candidate=ROOT/'verification/android-environment-platform-implementation/manifest.json';assert identity(candidate)['sha256']==acceptance['candidate_manifest_sha256']
 v=json.loads(candidate.read_text());assert all(identity(ROOT/p)==expected for p,expected in v['files'].items())
 protected=json.loads((OWN/'attempt-2/custody.json').read_text())['protected'];assert all(identity(ROOT/p)==v['expected'] for p,v in protected.items())
 if not a.check:
  assert not manifest.exists(),'review already frozen'
  m={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':sys.argv,'python':sys.version,'candidate_manifest_sha256':acceptance['candidate_manifest_sha256'],'selected_contract_sha256':acceptance['selected_contract_sha256'],'scope':'independent finite actual-source host/compiler/API/custody review only','files':files,'members':len(files),'native_or_public_or_OTA_or_GA_authority':False,'CLI_read_or_hashed':False}
  manifest.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
 m=json.loads(manifest.read_text());assert m['files']==files,'review packet membership or bytes drift'
 print(json.dumps({'status':'PASS immutable independent native review custody only','manifest':identity(manifest),'members':len(files),'candidate_members_verified':len(v['files']),'protected_files_verified':len(protected),'native_or_release_authority':False},sort_keys=True))
if __name__=='__main__':main()
