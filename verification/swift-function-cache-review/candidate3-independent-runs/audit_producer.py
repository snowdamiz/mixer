#!/usr/bin/env python3
from pathlib import Path
import hashlib,io,json,re,subprocess,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];P=ROOT/'verification/swift-function-cache/candidate-3'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(name):return json.loads((P/name).read_text())
def check_bindings(bindings):
 for name,h in bindings.items():assert sha((ROOT/name).read_bytes())==h,name
 return len(bindings)
r=read('producer-receipt.json');assert sha((P/'producer-receipt.json').read_bytes())=='32a7485b2be208dd12d165a6ce61fa4ace6f2013031e28c2f68ab54cf6f5bdc6'
count=check_bindings(r['bindings']);f=read('source-freeze.json');manifest=f['source_manifest'];assert len(manifest)==118 and len(f['overlays'])==10
assert sha(json.dumps(manifest,sort_keys=True).encode())==f['source_manifest_sha256']==r['source_manifest_sha256']=='fd939d26dfe6465af839c5e1a1f71a8ccacc52668591d5d09650eddb024582c3'
check_bindings(manifest)
with tarfile.open(P/'frozen-source.tar.gz','r:gz') as t:
 assert len(t.getmembers())==118
 for item in t.getmembers():
  assert item.isfile() and not Path(item.name).is_absolute() and '..' not in Path(item.name).parts
  data=t.extractfile(item).read();assert sha(data)==manifest[item.name],item.name
baseline={}
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','archive',f['baseline_revision']],cwd=ROOT))) as t:
 for item in t.getmembers():
  if item.isfile():baseline[item.name]=sha(t.extractfile(item).read())
for name,h in manifest.items():
 old=baseline.get(name)
 if name in f['overlays']:
  assert f['overlays'][name]=={'baseline_sha256':old,'frozen_sha256':h},name
 else:assert old==h,name
inputs=json.loads((HERE/'full-input-manifest.json').read_text())
assert len(inputs)==420
for name,h in inputs.items():
 if name in manifest:assert h==manifest[name],name
 else:assert h==baseline[name],name
for label,expected in [('qualification/regressions.json',116),('qualification/named/receipt.json',111),('qualification/additional-reference-receipt.json',116)]:
 q=read(label);assert len(q['source_manifest'])==expected
 assert sha(json.dumps(q['source_manifest'],sort_keys=True).encode())==q['source_manifest_sha256']
 assert all(manifest[n]==h for n,h in q['source_manifest'].items())
 if 'source_manifest_after' in q:assert q['source_manifest_after']==q['source_manifest']
 if 'unchanged_source' in q:assert q['unchanged_source'] is True
 assert all(c['exit_code']==0 for c in q['commands']),label
reg=read('qualification/regressions.json');named=read('qualification/named/receipt.json');extra=read('qualification/additional-reference-receipt.json')
assert len(reg['commands'])==21 and len(named['commands'])==36 and len(extra['commands'])==2
for actual,expected in zip(reg['commands'][:16],r['feature_matrix']):
 assert actual['argv']==expected['argv']
 assert sum(map(int,re.findall(r'test result: ok\. (\d+) passed;',actual['stdout'])))==expected['passed']
for c in reg['commands'][16:18]:assert sum(map(int,re.findall(r'test result: ok\. (\d+) passed;',c['stdout'])))==7
for c in extra['commands']:assert sum(map(int,re.findall(r'test result: ok\. (\d+) passed;',c['stdout'])))==2
for c in named['commands']:assert re.search(r'test result: ok\. 1 passed; 0 failed;',c['stdout'])
cases=read('coverage-map.json');assert len(cases['tests'])==18
names={t['name'] for t in cases['tests']}
for mode in [False,True]:
 selected=[c for c in named['commands'] if ('--release' in c['argv'])==mode];assert len(selected)==18
 assert {next(a.rsplit('::',1)[-1] for a in c['argv'] if a.startswith('experimental_swift_reactor::cache_tests::')) for c in selected}==names
surface=read('surface-receipt.json');assert len(surface['original_exports'])==len(surface['current_exports'])==28 and surface['original_exports']==surface['current_exports']
for name,h in surface['headers'].items():assert sha((ROOT/'vm/include'/name).read_bytes())==h==baseline['vm/include/'+name]
assert all(c['exit_code']==0 for c in surface['commands'])
legacy=read('legacy-parity-receipt.json');assert len(legacy['comparisons'])==4 and all(c['equal'] for c in legacy['comparisons']);assert all(c['exit_code']==0 for c in legacy['commands'])
map_json=read('preflight-root-tail-map.json');layout=read('layout-map.json')
assert all(layout['layouts'][k]=={q:v[q] for q in ['size','align']} for k,v in map_json['layouts'].items())
assert layout['phase_map_sha256']==sha((P/'preflight-root-tail-map.json').read_bytes())
old=json.loads((ROOT/'verification/swift-function-cache-review/candidate-1-review-receipt.json').read_text());check_bindings(old['bound_artifacts'])
preserved=json.loads((ROOT/'verification/swift-function-cache/candidate-1/preservation-map.json').read_text())
for original,row in preserved['evidence'].items():
 assert sha((ROOT/row['preserved']).read_bytes())==row['sha256']==sha((ROOT/original).read_bytes()),original
for original,row in preserved['source'].items():
 assert sha((ROOT/row['preserved']).read_bytes())==row['sha256'],original
changed={n:{'candidate1':h,'candidate2':manifest[n]} for n,h in json.loads((ROOT/'verification/swift-function-cache/source-freeze.json').read_text())['source_manifest'].items() if manifest[n]!=h}
assert set(changed)=={'vm/src/experimental/cache/borrowed.rs','vm/src/experimental_swift_reactor/cache.rs','vm/src/experimental_swift_reactor/cache_tests.rs'}
result={'producer_receipt_sha256':sha((P/'producer-receipt.json').read_bytes()),'source_freeze_digest':f['source_manifest_sha256'],'source_files':118,'exact_baseline_overlays':10,'full_independent_vm_inputs':420,'producer_artifact_bindings_verified':count,'regression_source_subset':116,'named_source_subset':111,'regression_commands_audited':21,'additional_reference_commands_audited':2,'named_commands_audited':36,'producer_reference_tests_per_mode':9,'native_exports_equal':28,'native_headers_equal':3,'historical_c2_root_phase_bindings_verified':438,'candidate1_bound_artifacts_unchanged':len(old['bound_artifacts']),'candidate1_preserved_evidence_verified':len(preserved['evidence']),'candidate1_preserved_source_verified':len(preserved['source']),'changed_since_candidate1':changed,'pending_required_assertions':[],'source_and_artifact_stability':True,'scope':'independent source/artifact and output audit; producer commands are audited evidence, not relabeled independent execution'}
mandatory=read('mandatory-assertion-receipt.json');check_bindings(mandatory['bindings'])
control=(HERE/'tree/vm/src/experimental_swift_reactor/control.rs').read_text()
kinds=re.findall(r'^    (\w+),$',control.split('pub enum SwiftRunFailureKind {',1)[1].split('}',1)[0],re.M);assert len(kinds)==21
traces=[]
for mode in ['debug','release']:
 text=(HERE/('named-'+mode+'-sticky_failure_has_no_new_effects.log')).read_text()
 rows=re.findall(r'sticky terminal kind=(\w+) phase_repeats=(\d+) full_pin_repeats=(\d+) prepare_repeats=(\d+) decode_delta=0 service_delta=0 allocation_requests=0 work_delta=0 honest_cleanup=true',text)
 assert [x[0] for x in rows]==kinds and all(x[1:]==('5','5','5') for x in rows),mode
 owner=(HERE/('named-'+mode+'-foreign_stale_nonce_and_control_ownership.log')).read_text()
 assert re.findall(r'owner allocator exhaustion attempt=(\d+) private_counter=MAX actual_constructor_allocations=3 partial_drained=true no_duplicate_authority=true',owner)==['0','1','2']
 traces.append({'mode':mode,'terminal_kinds':kinds,'repeat_routes':sum(sum(map(int,x[1:])) for x in rows),'actual_constructor_owner_exhaustions':3})
prior=read('prior-candidate-preservation.json');check_bindings(prior['candidate2_artifacts'])
c2freeze=json.loads((ROOT/'verification/swift-function-cache/candidate-2/source-freeze.json').read_text());c2archived={}
with tarfile.open(ROOT/'verification/swift-function-cache/candidate-2/frozen-source.tar.gz','r:gz') as archive:
 assert len(archive.getmembers())==118
 for member in archive.getmembers():
  data=archive.extractfile(member).read();assert sha(data)==c2freeze['source_manifest'][member.name];c2archived[member.name]=data
root_phase=json.loads((ROOT/'verification/swift-cache-foundation-phase-review/acceptance.json').read_text());assert len(root_phase['bindings'])==438
resolved=[]
for name,digest in root_phase['bindings'].items():
 if sha((ROOT/name).read_bytes())!=digest:
  assert name in c2archived and sha(c2archived[name])==digest,name;resolved.append(name)
assert set(resolved)=={'vm/src/experimental_swift_reactor/cache.rs','vm/src/experimental_swift_reactor/cache_tests.rs'}
result['historical_c2_root_source_bindings_resolved_to_immutable_archive']=resolved
result['candidate2_archived_source_members_verified']=118
c2=json.loads((ROOT/'verification/swift-function-cache-review/candidate-2-review-receipt.json').read_text());check_bindings(c2['bound_review_artifacts'])
result['candidate2_artifacts_unchanged']=len(prior['candidate2_artifacts']);result['candidate2_review_bindings_unchanged']=len(c2['bound_review_artifacts']);result['independent_mandatory_traces']=traces
(HERE/'producer-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
