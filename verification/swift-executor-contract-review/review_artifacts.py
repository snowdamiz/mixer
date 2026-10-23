#!/usr/bin/env python3
"""Independently bind/replay proposal checks; never invoke its collector."""
import hashlib, io, json, os, platform, subprocess, sys, tarfile
from datetime import datetime, timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/swift-executor-stage-contract'
EXPECTED_RECEIPT='62f825ab418b207c057f384b2c0afdbfabb3fee50e0db75e945f0d3448f092de'
sha=lambda data:hashlib.sha256(data).hexdigest()
raw=(PRODUCER/'receipt.json').read_bytes()
assert sha(raw)==EXPECTED_RECEIPT
receipt=json.loads(raw)
preserved={str((PRODUCER/'receipt.json').relative_to(ROOT)):sha(raw)}
inputs={str((PRODUCER/'receipt.json').relative_to(ROOT)):raw}
bindings=[]
def bind(item):
    data=(ROOT/item['path']).read_bytes()
    assert len(data)==item['bytes'] and sha(data)==item['sha256'],item['path']
    preserved[item['path']]=sha(data)
    inputs[item['path']]=data
    bindings.append(item['path'])
for item in [receipt['source_binding']]+receipt['reference_bindings']+receipt['artifact_bindings']:
    bind(item)
for command in receipt['commands']:
    assert command['exit_code']==0
    bind(command['stdout']);bind(command['stderr'])
assert len(receipt['commands'])==9
source_manifest=json.loads(inputs[receipt['source_binding']['path']])
for item in source_manifest['files']:
    blob=subprocess.check_output(['git','show',item['revision']+':'+item['path']],cwd=ROOT)
    assert len(blob)==item['bytes'] and sha(blob)==item['sha256'],item['path']
    inputs['baseline/'+item['path']]=blob
    bindings.append('git:'+item['revision']+':'+item['path'])
acceptance=json.loads(inputs['verification/swift-executor-stage-contract/acceptance.json'])
tests=acceptance['required_synthetic_tests']
assert len(tests)==20 and sum(len(t['assertions']) for t in tests)==75
assert all(t['status']=='pending' and t['profiles']==['debug','release'] for t in tests)
assert all(m['status']=='pending' and m['measurements'] is None and m['simultaneous_counts'] is None for m in acceptance['measured_layout_map'])
snapshot=HERE/'.build/artifact-source'
for name,data in inputs.items():
    path=snapshot/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
# Evolving cache is frozen for static analysis only, excluded from build/run.
for name in ['vm/src/experimental_swift_reactor/cache.rs','vm/src/experimental_wasi/accounted.rs','vm/src/experimental_swift_reactor/control.rs']:
    inputs['analysis/'+name]=(ROOT/name).read_bytes()
with tarfile.open(HERE/'review-inputs.tar','w') as tar:
    for name,data in sorted(inputs.items()):
        info=tarfile.TarInfo(name);info.size=len(data);info.mtime=0
        tar.addfile(info,io.BytesIO(data))
manifest={name:sha(data) for name,data in sorted(inputs.items())}
(HERE/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
commands=[]
checker=snapshot/'verification/swift-executor-stage-contract/check_contract.py'
for label,options in [('contract-check',[]),('contract-mutations',['--mutation-checks'])]:
    argv=[sys.executable,'-B',str(checker),*options]
    proc=subprocess.run(argv,cwd=snapshot,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (HERE/(label+'.stdout.json')).write_bytes(proc.stdout)
    (HERE/(label+'.stderr.txt')).write_bytes(proc.stderr)
    assert proc.returncode==0,proc.stderr.decode()
    result=json.loads(proc.stdout)
    assert result['contract_checks_passed'] and result['implementation_tests_executed']==0
    if options:assert len(result['mutation_checks'])==15 and all(m['rejected'] for m in result['mutation_checks'])
    commands.append({'argv':argv,'cwd':str(snapshot),'exit':proc.returncode,'stdout_sha256':sha(proc.stdout),'stderr_sha256':sha(proc.stderr),'label':label})
assert all(sha((ROOT/name).read_bytes())==digest for name,digest in preserved.items())
result={
    'observed_utc':datetime.now(timezone.utc).isoformat(), 'reviewer':'/root/swift_executor_prerequisite_review',
    'model':'gpt-6.1-sol','reasoning_effort':'xhigh','python':platform.python_version(),
    'producer_receipt_sha256':sha(raw),'source_tree_sha256':sha(json.dumps(manifest,sort_keys=True).encode()),
    'source_archive_sha256':sha((HERE/'review-inputs.tar').read_bytes()),'source_manifest_sha256':sha((HERE/'source-manifest.json').read_bytes()),
    'verified_bindings':len(bindings),'producer_commands_audited':9,'synthetic_tests_pending':20,'assertions_pending':75,
    'implementation_tests_executed':0,'artifact_checker_passed':True,'mutations_rejected':15,'commands':commands,
    'producer_artifacts_unchanged':True,'preserved_artifacts':preserved,'script_sha256':sha(Path(__file__).read_bytes()),
    'scope':'Proposal-only artifact and static-source review. Additional frozen foundation named-layout test is separate in layout-receipt.json. No cache/executor acceptance or target/device run.',
    'decision':'changes-required-for-measured-foundation-tail-accounting',
    'blocking_finding':'R1: foundation and contract require 3 Option<WasiUsage> success-tail shapes, not frozen 2 plain WasiUsage; +128 bytes on measured host. Root owns refinement. Future composed tail needs its explicit disjoint full live-set map.',
    'remaining_pending':acceptance['explicit_pending']
}
(HERE/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['verified_bindings','artifact_checker_passed','mutations_rejected','decision']}))
