#!/usr/bin/env python3
"""Append an immutable selected-map acceptance binding; do not rewrite receipts."""
from pathlib import Path
import datetime,gzip,hashlib,json,subprocess,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())
def verify(bindings):
 for path,expected in bindings.items():
  assert sha(ROOT/path)==expected,path
 return len(bindings)
producer_path=HERE/'producer-receipt.json';producer=read(producer_path)
freeze_path=HERE/'source-freeze.json';freeze=read(freeze_path)
assert producer['status']=='producer_commands_passed_independent_acceptance_pending'
assert producer['source_manifest_sha256']==freeze['source_manifest_sha256']
counts={'producer_artifacts':verify(producer['bindings']),'current_source':verify(freeze['source_manifest'])}
with tarfile.open(HERE/'frozen-source.tar.gz','r:gz')as archive:
 members=archive.getmembers();assert len(members)==len(freeze['source_manifest'])
 for member in members:
  assert member.isfile()and member.name in freeze['source_manifest']
  assert hashlib.sha256(archive.extractfile(member).read()).hexdigest()==freeze['source_manifest'][member.name]
counts['archive_source_files']=len(members)
root_path=ROOT/'verification/swift-cache-foundation-phase-review/acceptance.json';root=read(root_path)
assert root['decision']=='accepted_selected_whole_slot_phase_map_only'
counts['root_phase_bindings']=verify(root['bindings'])
assert counts['root_phase_bindings']==root['bound_checks']==438
review_path=ROOT/'verification/swift-function-cache-review/candidate2-final-map/decision-receipt.json';review=read(review_path)
counts['independent_map_artifacts']=verify(review['bound_review_artifacts'])
assert review['source_sha256']==freeze['source_manifest']['vm/src/experimental_swift_reactor/cache.rs']
assert review['bounds']=={'construction':57128,'operation':80566,'cleanup':62096,'header':62424,'foundation':16504}
preserved_path=HERE.parent/'candidate-1/preservation-map.json';preserved=read(preserved_path)
for kind in ['source','evidence']:
 for entry in preserved[kind].values():assert sha(ROOT/entry['preserved'])==entry['sha256']
 counts['candidate1_preserved_'+kind]=len(preserved[kind])
paths=[producer_path,freeze_path,root_path,review_path,ROOT/'docs/swift-cache-foundation-phase-addendum.md',Path(__file__).resolve(),preserved_path]
record={'schema':'mixer-swift-cache-candidate2-phase-acceptance-supplement-v1','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'producer_qualified_selected_map_accepted_full_candidate_review_pending','scope':'Additive binding only; original candidate1/candidate2 receipts, maps and source freeze remain unchanged. Root acceptance applies to selected private whole-slot map, not full cache/executor/target/device/release/GA acceptance.','producer_receipt_sha256':sha(producer_path),'source_manifest_sha256':freeze['source_manifest_sha256'],'verified_bindings':counts,'bindings':{str(p.relative_to(ROOT)):sha(p)for p in paths},'tool':subprocess.check_output(['python3','--version'],text=True).strip(),'limits':producer['limits']}
out=HERE/'phase-acceptance-supplement.json';assert not out.exists(), 'supplement already sealed'
out.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'supplement_sha256':sha(out),'verified_bindings':counts},indent=2))
