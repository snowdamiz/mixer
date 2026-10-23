#!/usr/bin/env python3
"""Exact source/evidence audit for the bounded owned-enable follow-on review."""
import datetime,hashlib,json,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CACHE={'.build','.swiftpm','__pycache__','.git'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise RuntimeError(message)
def read(p):return json.loads(p.read_text())
def sealed(p,d):require(sha(p)==d,'receipt seal '+str(p));return read(p)
def manifest(paths):return ''.join(sha(p)+'  '+str(p.relative_to(ROOT))+'\n' for p in sorted(paths))
def audit():
    base_path=ROOT/'experimental-capability-runtime/verification/2026-10-23-enable-deadline-candidate-1/receipt.json'
    base=sealed(base_path,'f5c27573731b7bd7055e66db301400d5b97f06bc328badc12e1512950741a276')
    repair_path=ROOT/'verification/capability-enable-deadline/consumer-repair-1/receipt.json'
    repair=sealed(repair_path,'7c53d6ca4a25a09aee7225f8325b8b1f318e0be74014bf0e70c5cb846cc39286')
    require(base['status']=='failed_check_preserved' and repair['status']=='scoped consumer repair passed','truthful base failure and repair status')
    require(repair['base_sha256']==sha(base_path),'exact base repair binding')
    require(len(base['source'])==72 and set(base['source'])==set(repair['source']),'72 identical paths')
    require([n for n,d in base['source'].items() if repair['source'][n]!=d]==[repair['changed_fixture']],'only consumer fixture changed')
    require(repair['changed_fixture']=='experimental-capability-runtime/verification/CrossProbe/Sources/bridge-lifecycle-probe/main.swift','bounded fixture repair')
    for path,r,key in [(base_path,base,'frozenSourceExport'),(repair_path,repair,'source_export')]:
        frozen=Path(r[key]);pin=r['sourceManifestSHA256' if r is base else 'source_manifest_sha256']
        require(sha(path.parent/'source-manifest.sha256')==pin,'source manifest bytes')
        require((path.parent/'source-manifest.sha256').read_text()==''.join(d+'  '+n+'\n' for n,d in sorted(r['source'].items())),'closed source mapping')
        for name,digest in r['source'].items():
            require(not CACHE.intersection(Path(name).parts) and sha(frozen/name)==digest,'frozen noncache source '+name)
            if r is repair:require(sha(ROOT/name)==digest,'current repaired source '+name)
    logs={};expected_failure=[]
    for row in base['commands']:
        log=base_path.parent/row['log'];raw=log.read_bytes();require(sha(log)==row['logSHA256'],'base command log')
        expected=-5 if row['name']=='host-lifecycle-consumer-run' else 0
        require(row['exitCode']==expected,'base expected status '+row['name'])
        if expected:require(b'Error raised at top level: unsupported' in raw,'preserved malformed consumer failure');expected_failure.append(str(log.relative_to(ROOT)))
        if 'expectedTests' in row:
            counts=[int(n) for n in re.findall(rb'Test run with (\d+) tests? in \d+ suites? passed',raw)]
            require(counts==[row['expectedTests']],'observed base test count')
        require(b'WARNING: ThreadSanitizer' not in raw,'no TSan warning');logs[str(log.relative_to(ROOT))]=sha(log)
    require(len(base['commands'])==23 and len(expected_failure)==1,'exact preserved matrix scope')
    for mode in ['debug','release','tsan']:
        row=next(c for c in base['commands'] if c['name']=='bridge-'+mode);require(row['expectedTests']==35 and row['passedTests']==[35],'35 tests '+mode)
        folder=base_path.parent/(mode+'-loopback');r=read(folder/'receipt.json')
        require(r['exit_code']==0 and sha(folder/'command.log')==r['output_sha256'],'actual loopback output')
        require(r['server_stopped'] and r['observations']['tcp_accepts']>=1 and r['observations']['tls_failures']>=1 and r['observations']['application_requests']==0,'normal-trust TLS rejection')
        for name in ['receipt.json','command.log','certificate-generation.log']:logs[str((folder/name).relative_to(ROOT))]=sha(folder/name)
    require(sha(ROOT/'verification/capability-enable-deadline/repair-consumer.py')==repair['driver_sha256'],'repair driver')
    require(len(repair['commands'])==6 and len(repair['binaries'])==8,'four repaired platform links and two host runs')
    for row in repair['commands']:
        log=repair_path.parent/row['log'];require(row['exit_code']==0 and sha(log)==row['log_sha256'],'actual repaired consumer command');logs[str(log.relative_to(ROOT))]=sha(log)
    require(b'SPI owned enable deadline linked and admitted before cutoff' in (repair_path.parent/'host-bridge-lifecycle-probe.log').read_bytes(),'actual repaired host enable')
    artifacts={}
    for files in base['nativeArtifacts'].values():
        for name,digest in files.items():
            path=Path(base['stageRoot'])/name;require(sha(path)==digest,'retained native artifact '+name);artifacts[str(path)]=digest
    for name,r in repair['binaries'].items():
        path=Path(r['path']);require(sha(path)==r['sha256'] and path.stat().st_size==r['bytes'],'actual repaired consumer '+name);artifacts[str(path)]=r['sha256']
    prefix='experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/'
    unchanged=[]
    for name,digest in base['source'].items():
        if name.startswith('sdk/') or name in [prefix+n for n in ['Lifecycle.swift','Native.swift','Failure.swift','Types.swift','Validation.swift']]:
            original=subprocess.check_output(['git','show',base['repositoryHeadAtRun']+':'+name],cwd=ROOT)
            require(hashlib.sha256(original).hexdigest()==digest,'old additive scope '+name);unchanged.append(name)
    targeted_path=HERE/'2026-10-23-targeted/receipt.json'
    t=sealed(targeted_path,'643e5973930ff0d113e9de39b29225108bcac054a9da46d99eb2b6f0094c97fc')
    require(t['status']=='targeted public and derived Debug/Release checks passed' and t['base_source']==base['source'],'targeted exact base')
    require(t['owner_base_receipt']['sha256']==sha(base_path) and t['repaired_consumer_receipt']['sha256']==sha(repair_path),'targeted composite qualification binding')
    require(sha(HERE/'run.py')==t['driver_sha256'],'targeted driver')
    for name,digest in t['original_inputs'].items():require(sha(HERE/name)==digest and sha(Path(t['source_export'])/name)==digest,'original targeted input '+name)
    derived={n:(Path(base['frozenSourceExport'])/prefix/n).read_bytes() for n in t['derived_module_originals']}
    require(len(derived)==7,'exact seven production Swift files')
    for name,digest in t['derived_module_originals'].items():require(hashlib.sha256(derived[name]).hexdigest()==digest,'derived base file')
    require(len(t['test_only_edits'])==3 and {e[0] for e in t['test_only_edits']}=={'Native.swift','Ownership.swift','Lifecycle.swift'},'three counter-only changes')
    for name,before,after in t['test_only_edits']:
        require(derived[name].count(before.encode())==1,'unique derived anchor');derived[name]=derived[name].replace(before.encode(),after.encode())
    require(sha(targeted_path.parent/'test-only.patch')==t['test_only_patch_sha256'],'counter patch bytes')
    for name,raw in derived.items():require((Path(t['source_export'])/'derived'/name).read_bytes()==raw,'exact counter-only derived file '+name)
    for name,digest in t['derived_source'].items():require(sha(Path(t['source_export'])/name)==digest,'all captured source bytes')
    counts={}
    for row in t['commands']:
        log=ROOT/row['log'];raw=log.read_bytes();require(sha(log)==row['sha256'] and row['exit_code']==row['expected_exit'],'targeted actual command')
        if 'passed_checks' in row:
            found=re.search(rb'passed (\d+) checks',raw);require(found is not None and int(found[1])==row['passed_checks'],'actual original check count');counts[row['name']]=int(found[1])
        logs[str(log.relative_to(ROOT))]=sha(log)
    expected={mode+'-'+name:count for mode in ['debug','release'] for name,count in [('public-run',14),('queued-expiry',8),('future-and-legacy',6),('checked-failure-first',7),('deadline-first',7)]}
    require(counts==expected,'targeted exact count mapping')
    for r in list(t['libraries'].values())+list(t['binaries'].values())+[t['native_archive']]:require(sha(Path(r['path']))==r['sha256'],'targeted actual library/binary');artifacts[r['path']]=r['sha256']
    return dict(status='independent exact source and composite owner evidence audit passed',base_receipt=dict(path=str(base_path.relative_to(ROOT)),sha256=sha(base_path)),repair_receipt=dict(path=str(repair_path.relative_to(ROOT)),sha256=sha(repair_path)),
        targeted_receipt=dict(path=str(targeted_path.relative_to(ROOT)),sha256=sha(targeted_path)),base_source_manifest_sha256=base['sourceManifestSHA256'],repaired_source_manifest_sha256=repair['source_manifest_sha256'],source_paths_verified=72,
        base_export=base['frozenSourceExport'],repaired_export=repair['source_export'],unchanged_preexisting_inputs=unchanged,preserved_owner_consumer_failure=expected_failure,
        verified_command_and_loopback_files=logs,verified_artifacts=artifacts,original_check_counts=counts,derived_production_files=7,derived_counter_edits=3,derived_captured_swift_inputs=len(t['derived_source']),
        source_semantics=['Owned-only SPI; legacy enable has nil cutoff','Exact caller DispatchTime uptime carried through the existing command slot','Expired sampled check skips C enable and publishes fixed first failure before ordinary cleanup','Local deadline branch stays outside native-error catch and does not quarantine','Already closed rejects; existing first checked failure remains immutable','Normal-close priority across separate closed/time samples is not atomic','Same exact native-close/actual-exit/worker/KV/tail retirement gates remain unchanged'])
def main():
    result=audit()
    source_names=['README.md','Fixture.swift','PublicProbe.swift','DerivedHooks.swift','DerivedProbe.swift','default-import.swift','run.py','finalize.py']
    sources=[HERE/n for n in source_names];source_manifest=manifest(sources)
    if '--check' in sys.argv:
        receipt=read(HERE/'final-receipt.json');require(read(HERE/'owner-audit.json')==result,'owner audit stable')
        require((HERE/'review-source.sha256').read_text()==source_manifest,'review source seal')
        for field,name in [('owner_audit_sha256','owner-audit.json'),('review_source_manifest_sha256','review-source.sha256'),('evidence_manifest_sha256','evidence-manifest.sha256')]:require(sha(HERE/name)==receipt[field],'aggregate binding')
        for line in (HERE/'evidence-manifest.sha256').read_text().splitlines():
            digest,name=line.split('  ',1);require(not CACHE.intersection(Path(name).parts) and sha(ROOT/name)==digest,'scoped noncache evidence')
        print('Independent owned-enable seal verified '+sha(HERE/'final-receipt.json'));return
    (HERE/'owner-audit.json').write_text(json.dumps(result,indent=2)+'\n');(HERE/'review-source.sha256').write_text(source_manifest)
    evidence=[p for p in HERE.rglob('*') if p.is_file() and not CACHE.intersection(p.relative_to(HERE).parts) and p.name not in ['final-receipt.json','evidence-manifest.sha256','.DS_Store']]
    (HERE/'evidence-manifest.sha256').write_text(manifest(evidence))
    receipt=dict(status='independent owned-enable cutoff scoped approval; no open actionable findings',completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        owner_audit_sha256=sha(HERE/'owner-audit.json'),review_source_manifest_sha256=sha(HERE/'review-source.sha256'),evidence_manifest_sha256=sha(HERE/'evidence-manifest.sha256'),review_source_files=len(sources),evidence_files=len(evidence),
        owner_base_source_manifest_sha256=result['base_source_manifest_sha256'],repaired_source_manifest_sha256=result['repaired_source_manifest_sha256'],source_paths_verified=72,
        public_checks_per_mode=14,derived_checks_per_mode=28,checked_modes=['debug','release'],ordinary_import_opacity_rejections=1,owner_matrix_tests_per_mode=35,owner_matrix_modes=['debug','release','Swift TSan'],repaired_linked_consumers=8,
        production_edits=False,old_review_seal_edits=False,committed=False,pushed=False,
        limitations=['Sampled cooperative pre-C cutoff, not atomic hard real-time or normal-close priority','Derived counters and private owner/stale-handle faults are labelled; no fabricated native/exit result','Failed-close probes retain capacity in isolated subprocesses; ordinary expiry separately proves exact retirement/reuse','Root consumer harness failure remains preserved; only repaired consumer fixture changed before cross replay','No duplicate package/Rust graph; existing products/native archive reused','No physical devices, authority/health/coordinator, trust or credential changes, production/publication, OS/Task destruction, hard global cap or GA qualification'])
    (HERE/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(final_receipt_sha256=sha(HERE/'final-receipt.json'),review_source_manifest_sha256=receipt['review_source_manifest_sha256'],evidence_manifest_sha256=receipt['evidence_manifest_sha256'],review_source_files=len(sources),evidence_files=len(evidence))))
if __name__=='__main__':main()
