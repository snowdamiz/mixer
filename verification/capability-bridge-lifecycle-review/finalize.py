#!/usr/bin/env python3
"""Audit exact frozen inputs/artifacts and seal only this bounded review lane."""
import datetime,hashlib,json,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CACHE={'.build','.swiftpm','__pycache__','.git'}
PIN='f9e72d973b0cbc389a5b454dbf2126acb2c5e741e4d4ff7c0ec9e0b495daacb9'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(value,message):
    if not value:raise RuntimeError(message)
def read(path):return json.loads(path.read_text())
def sealed(path,pin):require(sha(path)==pin,str(path)+' seal');return read(path)
def manifest(paths):return ''.join(sha(p)+'  '+str(p.relative_to(ROOT))+'\n' for p in sorted(paths))
def rows(receipt,directory,style):
    result={}
    for row in receipt['commands']:
        log=directory/row['log'] if style=='owner' else ROOT/row['log']
        raw=log.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        require(digest==row['logSHA256' if style=='owner' else 'sha256'],'command output digest')
        require(row['exitCode' if style=='owner' else 'exit_code']==(0 if style=='owner' else row.get('expected_exit',0)),'command status')
        require(b'WARNING: ThreadSanitizer' not in raw,'no Swift TSan warning')
        if 'expectedTests' in row:
            counts=[int(n) for n in re.findall(rb'Test run with (\d+) tests? in \d+ suites? passed',raw)]
            require(counts==[row['expectedTests']],'observed test count')
        result[str(log.relative_to(ROOT))]=digest
    return result
def audit():
    aggregate=ROOT/'verification/capability-bridge-lifecycle/2026-10-23-lifecycle-candidate-1.json'
    a=sealed(aggregate,'81e7eeff807132b10ede35e727680c599b38b462bb649ce144d081f9497bd138')
    require(a['status']=='implementer_scoped_checks_passed','owner aggregate status')
    receipts={}
    for kind,ref in a['receipts'].items():
        p=ROOT/ref['path'];receipts[kind]=(p,sealed(p,ref['sha256']))
    mp,m=receipts['matrix'];source=Path(m['frozenSourceExport'])
    require(m['sourceManifestSHA256']==PIN and len(m['source'])==71,'exact source freeze')
    require(sha(mp.parent/'source-manifest.sha256')==PIN,'actual source manifest')
    require((mp.parent/'source-manifest.sha256').read_text()==''.join(d+'  '+n+'\n' for n,d in sorted(m['source'].items())),'source manifest complete mapping')
    for name,digest in m['source'].items():
        require(not CACHE.intersection(Path(name).parts),'source excludes cache')
        require(sha(source/name)==digest and sha(ROOT/name)==digest,'immutable/live source '+name)
    logs=rows(m,mp.parent,'owner');require(len(logs)==23,'matrix command logs')
    for mode in ['debug','release','tsan']:
        c=next(row for row in m['commands'] if row['name']=='bridge-'+mode)
        require(c['expectedTests']==32 and c['passedTests']==[32],'full suite count '+mode)
        directory=mp.parent/(mode+'-loopback');r=read(directory/'receipt.json')
        require(r['exit_code']==0 and sha(directory/'command.log')==r['output_sha256'],'loopback child output')
        require(r['observations']['tcp_accepts']>=1 and r['observations']['tls_failures']>=1 and r['observations']['application_requests']==0 and r['server_stopped'],'actual normal-trust TLS rejection')
        for name in ['receipt.json','command.log','certificate-generation.log']:logs[str((directory/name).relative_to(ROOT))]=sha(directory/name)
    artifacts={}
    for target,files in m['nativeArtifacts'].items():
        for name,digest in files.items():
            path=Path(m['stageRoot'])/name;require(sha(path)==digest,'native artifact '+name);artifacts[str(path)]=digest
    require(len(artifacts)==16,'four qualified native stages')
    for name,r in m['linkedConsumers'].items():
        path=Path(r['path']);require(sha(path)==r['sha256'] and path.stat().st_size==r['bytes'],'actual consumer '+name);artifacts[str(path)]=r['sha256']
    require(len(m['linkedConsumers'])==8,'eight consumer binaries')
    dp,d=receipts['derived'];require(d['baseSource']==m['source'] and d['baseManifestSHA256']==PIN,'derived exact base')
    require(d['status']=='passed' and d['baseUnchanged'] and d['derivedUnchanged'],'derived owner status')
    require(len(d['commands'])==15,'15 isolated derived runs');logs.update(rows(d,dp.parent,'owner'))
    require(all(c['expectedTests']==1 and c['passedTests']==[1] for c in d['commands']),'actual derived probe counts')
    require(sha(dp.parent/'test-only.patch')==d['patchSHA256'],'derived patch seal')
    require(sha(ROOT/'verification/capability-bridge-lifecycle/probes.py')==d['driverSHA256'],'derived frozen driver')
    expected={name:(source/name).read_bytes() for name in m['source']}
    prefix='experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/'
    # Independent exact transformation audit, not acceptance of a patch hash alone.
    edits=[
        ('Session.swift','                    lifecycle?.constructorReturned()','                    LifecycleProbeHooks.beforeConstructorTail()\n                    lifecycle?.constructorReturned()'),
        ('Session.swift','            lifecycle?.expectsNative()','            LifecycleProbeHooks.afterCreate()\n            lifecycle?.expectsNative()'),
        ('Lifecycle.swift','            if let storage { await storage.close() }','            await LifecycleProbeHooks.beforeStorageClose()\n            if let storage { await storage.close() }'),
        ('Lifecycle.swift','return InstalledCapabilityAdapters(http: state.http, storage: state.storage)','return LifecycleProbeHooks.adapters(http: state.http, storage: state.storage)'),
        ('Native.swift','        do {\n            try Self.check(status, report, operation: .construction','        LifecycleProbeHooks.createReport(&report)\n        do {\n            try Self.check(status, report, operation: .construction'),
        ('Native.swift','                let cleanupStatus = mixer_vm_capability_session_close_v1','                LifecycleProbeHooks.nativeClose()\n                let cleanupStatus = mixer_vm_capability_session_close_v1'),
        ('Native.swift','    func close() throws {\n        var report','    func close() throws {\n        LifecycleProbeHooks.nativeClose()\n        var report')]
    for name,before,after in edits:
        key=prefix+name;require(expected[key].count(before.encode())==1,'unique derived anchor');expected[key]=expected[key].replace(before.encode(),after.encode())
    for original,dest in [('Hooks.swift',prefix+'LifecycleProbeHooks.swift'),('Tests.swift','experimental-capability-runtime/Tests/MixerExperimentalCapabilityRuntimeTests/LifecycleProbeTests.swift')]:expected[dest]=(source/'verification/capability-bridge-lifecycle/Probe'/original).read_bytes()
    require(set(expected)==set(d['derivedSource']) and len(expected)==73,'closed derived file mapping')
    for name,raw in expected.items():
        require(hashlib.sha256(raw).hexdigest()==d['derivedSource'][name] and raw==(Path(d['sourceExport'])/name).read_bytes(),'exact derived-only mutation '+name)
    pp,p=receipts['publicReplay'];require(p['status']=='passed' and p['exitCode']==0 and p['expectedTests']==10 and p['baseOwnerManifestSHA256']==PIN,'old public replay')
    require(sha(pp.parent/'public-debug.log')==p['logSHA256'],'old public log');require(b'Executed 10 tests, with 0 failures' in (pp.parent/'public-debug.log').read_bytes(),'actual old public count')
    logs[str((pp.parent/'public-debug.log').relative_to(ROOT))]=p['logSHA256']
    for name,digest in p['source'].items():require(sha(Path(p['cwd'])/name)==digest,'old public export '+name)
    # Old SDK, native checker, validator, models, package and C shim stay exact.
    old=[]
    for name,digest in m['source'].items():
        if name.startswith('sdk/') or name in ['experimental-capability-runtime/Package.swift']+[prefix+n for n in ['Native.swift','Failure.swift','Types.swift','Validation.swift']] or name.startswith('experimental-capability-runtime/Sources/CMixerVMCapability/'):
            original=subprocess.check_output(['git','show',m['repositoryHeadAtRun']+':'+name],cwd=ROOT)
            require(hashlib.sha256(original).hexdigest()==digest,'unchanged pre-existing source '+name);old.append(name)
    original_receipts={}
    for folder in ['2026-10-23-public','2026-10-23-internal']:
        path=HERE/folder/'receipt.json';r=read(path);require(r['owner_source_manifest_sha256']==PIN,'independent probe source binding')
        require('passed' in r['status'],'independent probe status');logs.update(rows(r,path.parent,'review'))
        original_receipts[str(path.relative_to(ROOT))]=sha(path)
        original=HERE/('PublicProbe.swift' if folder.endswith('public') else 'InternalProbe.swift');require(sha(original)==r['original_probe_sha256'],'original independent source')
        driver=HERE/('run.py' if folder.endswith('public') else 'internal.py');require(sha(driver)==r['driver_sha256'],'original independent driver')
        if 'libraries' in r:
            require({k:v['checks'] for k,v in r['binaries'].items()}=={'debug':17,'release':17},'original public count')
            for record in list(r['libraries'].values())+list(r['binaries'].values())+[r['native_archive']]:require(sha(Path(record['path']))==record['sha256'],'public actual artifact')
        else:
            for name,count in [('gates',8),('close-failure',6)]:require(('passed '+str(count)+' checks').encode() in (path.parent/(name+'.log')).read_bytes(),'original internal count')
            for record in [r['library'],r['native_archive'],r['binary']]:require(sha(Path(record['path']))==record['sha256'],'internal actual artifact')
    for folder in ['2026-10-23-public-first-compile','2026-10-23-internal-first-module']:
        path=HERE/folder/'receipt.json';r=read(path);require('failed' in r['status'] and sha(path.parent/'Probe.swift')==r['original_probe_sha256'],'historical failed review source retained')
        for row in r['commands']:
            # Failure directories were renamed intact before their corrected
            # replay. Preserve original receipt bytes and map only the basename.
            raw=(path.parent/Path(row['log']).name).read_bytes();require(hashlib.sha256(raw).hexdigest()==row['sha256'],'historical review log')
    return dict(status='independent frozen lifecycle source/evidence audit passed',owner_aggregate=dict(path=str(aggregate.relative_to(ROOT)),sha256=sha(aggregate)),
        owner_receipts={kind:dict(path=str(path.relative_to(ROOT)),sha256=sha(path)) for kind,(path,_) in receipts.items()},source_manifest_sha256=PIN,source_inputs_verified=71,
        owner_logs_and_loopback_files=logs,owner_native_and_consumer_artifacts=artifacts,derived_inputs_exactly_reconstructed=73,derived_probe_runs=15,
        unchanged_preexisting_inputs=old,baseline_revision=m['repositoryHeadAtRun'],independent_receipts=original_receipts,
        immutable_source=str(source),native_revision=m['nativeRevision'],design_sha256=sha(ROOT/'docs/capability-durable-updater-api-design.md'))
def main():
    result=audit()
    sources=[HERE/'README.md',HERE/'PublicProbe.swift',HERE/'InternalProbe.swift',HERE/'run.py',HERE/'internal.py',Path(__file__)]+list((HERE/'CompileNegative').glob('*.swift'))
    source_manifest=manifest(sources)
    if '--check' in sys.argv:
        require((HERE/'review-source.sha256').read_text()==source_manifest,'review source seal')
        require(read(HERE/'owner-audit.json')==result,'owner audit unchanged')
        receipt=read(HERE/'final-receipt.json')
        require(sha(HERE/'owner-audit.json')==receipt['owner_audit_sha256'],'owner audit binding')
        for field,filename in [('review_source_manifest_sha256','review-source.sha256'),('evidence_manifest_sha256','evidence-manifest.sha256')]:require(sha(HERE/filename)==receipt[field],'final manifest binding')
        for line in (HERE/'evidence-manifest.sha256').read_text().splitlines():
            digest,name=line.split('  ',1);require(not CACHE.intersection(Path(name).parts) and sha(ROOT/name)==digest,'exact scoped evidence '+name)
        print('Final lifecycle review seal verified: '+sha(HERE/'final-receipt.json'));return
    (HERE/'owner-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    (HERE/'review-source.sha256').write_text(source_manifest)
    evidence=[p for p in HERE.rglob('*') if p.is_file() and not CACHE.intersection(p.relative_to(HERE).parts) and p.name not in ['final-receipt.json','evidence-manifest.sha256','.DS_Store']]
    (HERE/'evidence-manifest.sha256').write_text(manifest(evidence))
    receipt=dict(status='independent lifecycle SPI scoped approval; no blocking findings',completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        owner_source_manifest_sha256=PIN,source_inputs=71,owner_audit_sha256=sha(HERE/'owner-audit.json'),review_source_manifest_sha256=sha(HERE/'review-source.sha256'),review_source_files=len(sources),
        evidence_manifest_sha256=sha(HERE/'evidence-manifest.sha256'),evidence_files=len(evidence),public_checks={'debug':17,'release':17},opacity_negative_compiles=4,spi_positive_compiles=1,
        isolated_internal_checks={'synthetic_gates_with_real_KV_close':8,'forced_private_stale_native_close':6},owner_matrix_tests_per_mode=32,owner_modes=['debug','release','Swift TSan'],
        owner_derived_runs=15,owner_old_public_tests=10,owner_linked_consumers=8,production_edits=False,committed=False,pushed=False,
        required_caller_constraints=['Reserve a separately counted whole attempt before adapter setup','Transfer exclusive concrete adapter use without unrelated requests','Use dedicated fixed O(1), nonblocking/nonreentrant sinks without a strong path to group/construction/session','Terminal failure never releases resources; quarantine may retain sinks and permits indefinitely'],
        limitations=['Internal manual nativeDidDrain is synthetic gating, not actual exit','Forced internal stale handle is not reachable through the public API; checked close-failure retention only','Owner derived controls are audited, not unmodified public reproductions','No duplicate broad build; reused exact frozen Swift/native products','Swift TSan does not instrument Rust or system frameworks','No outer coordinator implementation, authority/health, physical devices, runtime Task/allocator/OS destruction, hard global resource caps, publication or GA qualification'])
    (HERE/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(final_receipt_sha256=sha(HERE/'final-receipt.json'),review_source_manifest_sha256=receipt['review_source_manifest_sha256'],evidence_manifest_sha256=receipt['evidence_manifest_sha256'],source_files=len(sources),evidence_files=len(evidence))))
if __name__=='__main__':main()
