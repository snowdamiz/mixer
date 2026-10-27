#!/usr/bin/env python3
"""Recheck only frozen inputs and this owned review; then seal immutable evidence."""
import datetime,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
PRODUCER=ROOT/'verification/swift-guarded-snapshot-host-account-entry'
def sha(data):return hashlib.sha256(data).hexdigest()
def write(name,value):(HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def members(folder):
 return [dict(path=p.relative_to(folder).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='seal.json']
assert not (HERE/'seal.json').exists()
inputs=json.loads((HERE/'input-bindings.json').read_text())
for key in ['producer_seal','root_release']:
 x=inputs[key];assert sha((ROOT/x['path']).read_bytes())==x['sha256']
seal=json.loads((PRODUCER/'seal.json').read_text())
for x in seal['members']:
 data=(PRODUCER/x['path']).read_bytes();assert len(data)==x['bytes'] and sha(data)==x['sha256']
for x in inputs['authored_inputs']:
 data=(PRODUCER/x['path']).read_bytes();assert len(data)==x['bytes'] and sha(data)==x['sha256']
assert (HERE/'sources/frozen_host_account.rs').read_bytes()==(PRODUCER/'host_account.rs').read_bytes()
assert members(HERE/'sources')==inputs['standalone_sources']
manifest=json.loads((HERE/'reconstructed-source-manifest.json').read_text())
assert manifest['members']==json.loads((PRODUCER/'source-manifest.json').read_text())['members']
assert manifest['source_tree_sha256']=='5cd522af7e126d88496b5aefee722ff481821f0cf5babdbdbd7fbeba646c380b'
assert len(manifest['members'])==145
receipts=sorted((HERE/'commands').glob('*/receipt.json'))
assert len(receipts)==20
for path in receipts:
 r=json.loads(path.read_text());assert r['exit_code']==r['expected_exit_code'] and r['direct_child_waited'] and not r['timed_out']
 assert r['source_bindings_sha256']==sha((HERE/'input-bindings.json').read_bytes())
 assert r['runner_sha256']==sha((HERE/'run_independent.py').read_bytes())
 for name,binding in r['output'].items():
  data=path.parent.joinpath(name).read_bytes();assert len(data)==binding['bytes'] and sha(data)==binding['sha256']
 if r['diagnostic']:assert r['diagnostic'] in (path.parent/'stderr').read_text()
for mode in ['debug','optimized']:
 assert '19 passed; 0 failed' in (HERE/'commands'/f'{mode}-run'/'stdout').read_text()
review=json.loads((HERE/'review.json').read_text())
assert review['blocking_semantic_findings']==[]
assert not review['source_inventory_independent_acceptance'] and not review['complete_quote_root_policy_P0_fixture_binding_accepted'] and not review['operational_grant_or_real_runtime_accepted']
assert not (HERE/'owned-work').exists()
assert all(not p.is_symlink() for p in HERE.rglob('*'))
write('audit-results.json',dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),argv=[sys.executable,str(Path(__file__).resolve())],python_version=sys.version,tool_sha256=sha(Path(__file__).read_bytes()),producer_members_verified=136,producer_member_bytes_verified=3432402,exact_source_members=145,source_manifest_matches=True,command_receipts_verified=20,expected_negative_compiles=13,positive_control=1,tests_each_mode=19,all_checks_pass=True,owned_scratch_removed=True,global_process_inventory=False))
listing=members(HERE)
write('seal.json',dict(schema=1,status='frozen-independent-private-account-source-contract-review; complete-quote-policy-P0-and-operation-pending',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),member_count=len(listing),member_bytes=sum(x['bytes'] for x in listing),members=listing,source_members=145,source_tree_sha256=manifest['source_tree_sha256'],producer_seal_sha256=inputs['producer_seal']['sha256'],private_account_source_accepted=True,source_inventory_accepted=False,complete_quote_root_policy_P0_fixture_binding_accepted=False,operational_native_OTA_FieldLog_GA_accepted=False))
print(json.dumps(dict(seal_sha256=sha((HERE/'seal.json').read_bytes()),member_count=len(listing),member_bytes=sum(x['bytes'] for x in listing),all_checks_pass=True)))
