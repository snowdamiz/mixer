#!/usr/bin/env python3
"""Independent frozen six-Option prerequisite and cache-v3 artifact audit."""
import hashlib,io,json,os,platform,re,subprocess,sys,tarfile,time
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/swift-observation-accounting'
sha=lambda data:hashlib.sha256(data).hexdigest()
inputs={};preserved={};commands=[]
def bind(name,expected=None):
    data=(ROOT/name).read_bytes()
    if expected is not None:assert sha(data)==expected,name
    inputs[name]=data;preserved[name]=sha(data)
    return data
raw=bind('verification/swift-observation-accounting/isolated-1/receipt.json','c5220730687db18698753e62a2c02acec1575290e30a6e92fcec35c097127828')
r=json.loads(raw)
assert r['passed'] and r['base_revision']=='3a1bb5a455973bde841a4b57993277fa2c054569'
bind('verification/swift-observation-accounting/collect.py',r['collector_sha256'])
audit_raw=bind('verification/swift-observation-accounting/root-audit.json')
audit=json.loads(audit_raw)
assert audit['passed'] and audit['receipt_sha256']==sha(raw)
bind('verification/swift-observation-accounting/audit.py',audit['auditor_sha256'])
archive=bind(r['source_archive'],r['source_archive_sha256'])
def members(data):
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        return {m.name:tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
frozen=members(archive)
manifest={name:sha(data) for name,data in frozen.items()}
assert manifest==r['source_files']
assert sha(json.dumps(manifest,sort_keys=True).encode())==r['source_tree_sha256']==audit['source_tree_sha256']=='5aac67fdd716e6b85285bea51e0245284f9a9dbf1971ceebffafcda9f5005b1d'
base_archive=subprocess.check_output(['git','archive',r['base_revision'],'vm'],cwd=ROOT)
baseline=members(base_archive)
assert set(baseline)==set(frozen)
overlays={name:manifest[name] for name in frozen if frozen[name]!=baseline[name]}
assert overlays==audit['source_overlays']=={
    'vm/src/experimental_swift_reactor/control.rs':'55e0e89c5da57347f02fd13dfb97296c19c3ace7d94fc11109dd224c9046b79f',
    'vm/src/experimental_swift_reactor/control_tests.rs':'0618d894583264b194d69f90c7a29a01a6a62f96a6118c337a508c5b910236b7'}
old=baseline['vm/src/experimental_swift_reactor/control.rs']
new=frozen['vm/src/experimental_swift_reactor/control.rs']
expected=old.replace(b'        (2, size_of::<WasiUsage>()),',b'        // Five nested observed-control arguments plus one retained caller\n        // observation. Count each Copy binding, including Option\'s tag; do not\n        // rely on last-use elision or another component\'s cleanup envelope.\n        (6, size_of::<Option<WasiUsage>>()),')
assert new==expected
bindings=2*len(manifest)+len(overlays)+3
counts={}
for command in r['commands']:
    data=bind(command['log'],command['sha256'])
    assert command['exit']==0 and command['source_stable']
    bindings+=1;label=command['label']
    if label in ['debug','release','debug-oracles','release-oracles','debug-minimal-swift','release-minimal-swift']:
        totals=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored',data.decode())
        assert totals and all(int(t[1])==0 for t in totals)
        count=sum(int(t[0]) for t in totals)
        assert count==(9 if 'oracles' in label else 73 if 'minimal' in label else 320)
        counts[label]=count
        if 'oracles' not in label:
            assert b'test experimental_swift_reactor::control::tests::optional_observation_chain_is_reserved_before_runtime_work ... ok' in data
            bindings+=1
for mode in ['debug','release']:
    data=inputs['verification/swift-observation-accounting/isolated-1/'+mode+'-observation-layout.log']
    assert b'running 1 test' in data and b'test result: ok. 1 passed; 0 failed;' in data
    assert b'raw=104 raw_align=8 optional=112 optional_align=8 count=6 old_floor=16040 new_floor=16504 added=464' in data
    bindings+=2
assert bindings==audit['verified_bindings']==859

# Freeze the current v3 proposal receipt separately from archived historical v2.
v3_raw=bind('verification/swift-cache-stage-contract/proposal-receipt.json','94476317a7bf4ea59266e7cad2f75d99bfae8196bd05abd21df4f64ed40628a3')
v3=json.loads(v3_raw)
assert v3['schema']=='mixer-swift-cache-contract-refinement-v3' and v3['passed']
assert v3['implementation_tests']=={'named':18,'accepted':0} and not v3['target_execution_authorized']
bind('verification/swift-observation-accounting/collect-contract.py',v3['collector_sha256'])
for name,digest in v3['bindings'].items():bind(name,digest)
for c in v3['commands']:
    assert c['exit']==0
    bind(c['log'],c['sha256'])
v3archive=bind(v3['source_archive'],v3['source_archive_sha256'])
assert {name:sha(data) for name,data in members(v3archive).items()}==v3['bindings']
plan=json.loads(inputs['verification/swift-cache-stage-contract/acceptance.json'])
assert plan['schema']=='mixer-swift-cache-stage-contract-v3' and plan['proposal_revision']==3
assert plan['cleanup_tail_contract']['foundation_named_counts']=={'SwiftRunFailure':4,'SwiftRunUsage':4,'ReservationTicket':6,'Option<WasiUsage>':6}
assert plan['observation_accounting_amendment']['source_acceptance']=='pending'
for version in ['v1','v2']:
    name='verification/swift-cache-stage-contract/historical-'+version+'/archive-manifest.json'
    history=json.loads(bind(name,plan['historical_'+version+'_manifest_sha256']))
    for item in history['files'].values():bind(item['archived_path'],item['sha256'])
bind(plan['independent_review'],plan['independent_review_sha256'])

source=HERE/'.build/source';artifact_source=HERE/'.build/artifact-source'
for name,data in frozen.items():
    p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
for name,data in inputs.items():
    p=artifact_source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
with tarfile.open(HERE/'review-inputs.tar','w') as tar:
    for name,data in sorted(inputs.items()):
        item=tarfile.TarInfo(name);item.size=len(data);item.mtime=0;tar.addfile(item,io.BytesIO(data))
(HERE/'source-manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
env=dict(os.environ);env['PATH']='/opt/homebrew/opt/rustup/bin:'+env['PATH'];env['CARGO_TARGET_DIR']=str(HERE/'.build/target')
def run(label,argv,cwd,expected_tests=None):
    start=time.monotonic();p=subprocess.run(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    data=p.stdout;(HERE/(label+'.log')).write_bytes(data)
    record={'label':label,'argv':argv,'cwd':str(cwd),'exit':p.returncode,'seconds':time.monotonic()-start,'sha256':sha(data),'log':str((HERE/(label+'.log')).relative_to(ROOT))}
    assert p.returncode==0,data.decode()
    if expected_tests is not None:
        totals=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed;',data.decode())
        assert totals and sum(int(t[0]) for t in totals)==expected_tests and all(int(t[1])==0 for t in totals),data.decode()
        record['passed_tests']=expected_tests
    commands.append(record);print(label,'passed',flush=True)
run('rust-version',['rustc','-Vv'],source)
run('cargo-version',['cargo','-V'],source)
base=['cargo','test','--locked','--manifest-path','vm/Cargo.toml','--features','experimental-swift-reactor','--lib']
fixture='experimental_swift_reactor::control::tests::optional_observation_chain_is_reserved_before_runtime_work'
for mode in ['debug','release']:
    run(mode+'-admission',base+(['--release'] if mode=='release' else [])+[fixture,'--','--exact','--nocapture'],source,1)
test=source/'vm/src/experimental_swift_reactor/control_tests.rs'
count=test.read_text().count('#[test]')+1
test.write_bytes(test.read_bytes()+(HERE/'deep_probes.rs').read_bytes())
probe_manifest={str(p.relative_to(source)):sha(p.read_bytes()) for p in source.rglob('*') if p.is_file()}
for mode in ['debug','release']:
    run(mode+'-deep-and-cleanup',base+(['--release'] if mode=='release' else [])+['experimental_swift_reactor::control::tests::','--','--nocapture'],source,count)
    assert b'review_six_optional_floor_covers_standalone_deep_fault_paths ... ok' in (HERE/(mode+'-deep-and-cleanup.log')).read_bytes()
assert probe_manifest=={str(p.relative_to(source)):sha(p.read_bytes()) for p in source.rglob('*') if p.is_file()}
contract_dir=artifact_source/'verification/swift-cache-stage-contract'
run('v3-contract-check',[sys.executable,'-B',str(contract_dir/'check_contract.py')],artifact_source)
run('v3-artifact-mutations',[sys.executable,'-B',str(HERE/'artifact_runner.py'),str(contract_dir)],artifact_source)
assert b'"rejected_mutations": 36' in (HERE/'v3-artifact-mutations.log').read_bytes()
assert all(sha((ROOT/name).read_bytes())==digest for name,digest in preserved.items())
result={
    'completed_utc':datetime.now(timezone.utc).isoformat(),'reviewer':'/root/swift_executor_prerequisite_review','model':'gpt-6.1-sol','reasoning_effort':'xhigh','python':platform.python_version(),
    'base_revision':r['base_revision'],'source_tree_sha256':r['source_tree_sha256'],'source_overlays':overlays,'audited_root_bindings':bindings,'audited_root_test_counts':counts,
    'producer_receipt_sha256':sha(raw),'root_audit_sha256':sha(audit_raw),'v3_producer_receipt_sha256':sha(v3_raw),'v3_bindings_audited':len(v3['bindings']),'v3_commands_audited':len(v3['commands']),
    'review_archive_sha256':sha((HERE/'review-inputs.tar').read_bytes()),'probe_sha256':sha((HERE/'deep_probes.rs').read_bytes()),'probe_tree_sha256':sha(json.dumps(probe_manifest,sort_keys=True).encode()),'script_sha256':sha(Path(__file__).read_bytes()),
    'commands':commands,'preserved_artifacts':preserved,'producer_and_prior_review_bytes_unchanged':True,
    'artifact_tests_passed':3,'mutants_rejected':36,'decision':'accept-six-optional-control-accounting-correction-and-cache-contract-v3-only',
    'cache_implementation_accepted':False,'executor_accepted':False,'target_execution_authorized':False,'physical_device_runs':False,'ga_gate_changes':False,
    'scope':'Independent frozen shared foundation accounting correction and cache v3 proposal artifacts only. Actual admission/standalone deep fault/cleanup host tests; no guest target instantiation/execution. Concrete composed layout/live-set maps, cache/executor implementation and external qualification remain pending.'}
(HERE/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'decision':result['decision'],'control_tests_each_mode':count,'root_bindings':bindings,'receipt_sha256':sha((HERE/'receipt.json').read_bytes())}))
