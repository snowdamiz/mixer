#!/usr/bin/env python3
"""Seal/verify this lane only; never mutates product, old packets or root metadata."""
from pathlib import Path
import datetime,hashlib,json,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DOC=ROOT/'docs/android-private-owner-candidate5-review.md'
EXCLUDED={HERE/name for name in ['manifest.json','manifest.sha256','seal-result.json','verify-result.json']}
def record(p):
 b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_text())
def main():
 mode=sys.argv[1];assert mode in ['--seal','--check']
 old=HERE.parent/'implementation-review-3';assert record(old/'manifest.json')['sha256']=='f4afff4105d08642e74f1e5a3255015828e57c2a703b023bdd91ce709be18bc2'
 prior=read(old/'manifest.json')
 for name,expected in prior['files'].items():assert record(ROOT/name)==expected,('prior packet changed',name)
 candidate=HERE/'candidate-5';assert record(candidate/'manifest.json')['sha256']=='59a820bd3cd7e01ead02114293028985f64a42eebc36094cef9d76f516eee1f1'
 admitted=read(candidate/'manifest.json')
 for name,expected in admitted['files'].items():assert record(candidate/name)==expected,('admitted candidate changed',name)
 checkpoint=HERE/'checkpoint/manifest.json';assert record(checkpoint)['sha256']=='26c1cb83525eb94d524ae10e92d4d1aa506ebe4934a5e3f7c3994b1f7edb4554'
 for name,expected in read(checkpoint)['files'].items():assert record(HERE/name)==expected,('early checkpoint changed',name)
 files={str(p.relative_to(ROOT)):record(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p not in EXCLUDED};files[str(DOC.relative_to(ROOT))]=record(DOC)
 assert not any(p.is_dir() and 'scratch' in p.name for p in HERE.iterdir())
 if mode=='--seal':
  assert not (HERE/'manifest.json').exists(),'seal is immutable; use --check'
  value=dict(schema=1,scope='Independent C5 private owner bounded host/source development review; no native/publicV2/OTA/GA acceptance',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=[sys.executable,'-B',str(Path(__file__).resolve()),mode],python=sys.version,interpreter=record(Path(sys.executable).resolve()),context_revision_only=read(HERE/'custody.json')['context_revision_only'],selected_source_map_sha256='da250cd1e7560f8d702753769a132b70f60ea05477d133c32afd0c7372c542a1',candidate_manifest_sha256=record(candidate/'manifest.json')['sha256'],prior_review3_manifest_sha256=record(old/'manifest.json')['sha256'],prior_review3_all_members_verified_unchanged=prior['members'],early_checkpoint_manifest_sha256=record(checkpoint)['sha256'],excluded_root_metadata=[str(p.relative_to(HERE)) for p in sorted(EXCLUDED)],members=len(files),bytes=sum(v['bytes'] for v in files.values()),external_owned_document=str(DOC.relative_to(ROOT)),files=files)
  (HERE/'manifest.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');(HERE/'manifest.sha256').write_text(record(HERE/'manifest.json')['sha256']+'\n')
 else:
  value=read(HERE/'manifest.json');assert value['files']==files,'exclusive owned packet membership/bytes changed';assert value['members']==len(files) and value['bytes']==sum(v['bytes'] for v in files.values());assert (HERE/'manifest.sha256').read_text().strip()==record(HERE/'manifest.json')['sha256']
 result=dict(mode=mode,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),manifest_sha256=record(HERE/'manifest.json')['sha256'],members=len(files),bytes=sum(v['bytes'] for v in files.values()),prior_all3589_members_unchanged=True,admitted_candidate_all1772_members_unchanged=True,early_checkpoint_all664_members_unchanged=True,all_exclusive_scratch_removed=True,native_capture_UI_or_process_discovery_started=False,product_or_leaf_modified=False,committed_or_pushed=False,scope='Bounded private development recommendation; root acceptance separate; native/source-only gates pending')
 (HERE/('seal-result.json' if mode=='--seal' else 'verify-result.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
