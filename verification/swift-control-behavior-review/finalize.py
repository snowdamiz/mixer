#!/usr/bin/env python3
"""Bind observations, retain executables, then remove only owned host scratch."""
from pathlib import Path
import datetime,gzip,hashlib,json,re,shutil,subprocess
from review import HERE,ROOT,PRODUCER,SCRATCH,VM,BASE,PROBES,enc,sha,digest,manifest

inputs=json.loads((HERE/'inputs.json').read_text())
assert digest(manifest(ROOT/'vm'))==inputs['baselineClosure']
assert digest(manifest(VM))==inputs['candidateClosure']
assert digest(manifest(BASE))==inputs['baselineClosure']
assert manifest(PROBES)==json.loads((HERE/'probe-manifest.json').read_text())
for name,expected in inputs['inputs'].items():assert sha(ROOT/name)==expected,name
commands=[]
for path in sorted((HERE/'commands').glob('*/receipt.json')):
    r=json.loads(path.read_text());r['receipt']=str(path.relative_to(HERE))
    out=gzip.decompress((path.parent/'stdout.gz').read_bytes());err=gzip.decompress((path.parent/'stderr.gz').read_bytes())
    assert hashlib.sha256(out).hexdigest()==r['stdoutSHA256'];assert hashlib.sha256(err).hexdigest()==r['stderrSHA256']
    summaries=re.findall(r'test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;',out.decode())
    if summaries:r.update(passedTests=int(summaries[-1][1]),failedTests=int(summaries[-1][2]),ignoredTests=int(summaries[-1][3]))
    commands.append(r)
latest={r['name']:r for r in commands}
required=[]
for config in ['swift','all']:
    for profile in ['debug','release']:
        required += [(f'{config}-{profile}',46),(f'probes-{config}-{profile}',7),(f'isolated-full-lib-{config}-{profile}',168 if config=='swift' else 197)]
for config in ['span','all']:
    for profile in ['debug','release']:required.append((f'{config}-{profile}-frozen',6))
for config in ['default','span','swift','all']:
    for profile in ['debug','release']:required.append((f'{config}-{profile}-check',None))
required.append(('format',None))
qualifying=[]
for name,count in required:
    r=latest[name];assert r['exitCode']==0,name
    if count is not None:assert (r['passedTests'],r['failedTests'],r['ignoredTests'])==(count,0,0),name
    assert r['sourceTreeSHA256']==(digest(manifest(PROBES)) if name.startswith('probes-') else inputs['candidateClosure'])
    if name.startswith('probes-'):assert r['environment']['CARGO_TARGET_DIR']==str(SCRATCH/'target-probe-vm')
    if name.startswith('isolated-'):assert r['environment']['CARGO_TARGET_DIR']==str(SCRATCH/'target-candidate-vm')
    qualifying.append({k:r[k] for k in ['name','receipt','exitCode','sourceTreeSHA256','passedTests'] if k in r})
layouts=json.loads((HERE/'layouts.json').read_text());assert len(layouts)==8
assert len(json.loads((HERE/'canonical-roles.json').read_text()))==2
assert json.loads((HERE/'hook-role-replay.json').read_text())['positiveFields']==400
assert all(r['identical'] for r in json.loads((HERE/'frozen-identity.json').read_text()).values())
assert len(json.loads((HERE/'clippy-comparison.json').read_text())['candidate'])==26

executables=[];(HERE/'executables').mkdir(exist_ok=True)
for prefix in ['isolated-full-lib-','probes-']:
    for config in ['swift','all']:
        for profile in ['debug','release']:
            name=prefix+config+'-'+profile;r=latest[name];path=HERE/r['receipt'];stderr=gzip.decompress((path.parent/'stderr.gz').read_bytes()).decode()
            matches=re.findall(r'Running unittests src/lib.rs \(([^)]+)\)',stderr);assert len(matches)==1,(name,matches)
            executable=Path(matches[0]);assert executable.is_file() and executable.is_relative_to(SCRATCH)
            target=HERE/'executables'/(name+'.gz');data=executable.read_bytes()
            with gzip.open(target,'wb') as f:f.write(data)
            executables.append(dict(name=name,path=str(target.relative_to(HERE)),uncompressedBytes=len(data),uncompressedSHA256=hashlib.sha256(data).hexdigest(),sourceTreeSHA256=r['sourceTreeSHA256'],commandReceipt=r['receipt'],originalPath=str(executable)))
(HERE/'executable-manifest.json').write_bytes(enc(executables))

excluded=[dict(name=r['name'],receipt=r['receipt'],reason='shared Cargo target allowed a probe binary to be reused under the exact source cwd; superseded by source-isolated full-library commands') for r in commands if r['name'].startswith('full-lib-')]
assert len(excluded)==4
failed=[dict(name=r['name'],receipt=r['receipt'],reason='review oracle compared after_cleanup=None against the original record_cleanup observation; exact first failure and at_failure preserved; corrected oracle source retained separately') for r in commands if r['name'].startswith('probes-') and r['exitCode']!=0]
assert len(failed)==1
(HERE/'attempts.json').write_bytes(enc(dict(authoringFailures=failed,excludedVerificationAttempts=excluded,initialProbeSource='attempts/attempt-1-independent-probes.rs',initialRunnerSource='attempts/attempt-1-runner.py',successfulSixGroupSource='attempts/attempt-2-independent-probes.rs',productCorrections=[])))

bindings=dict(inputs['inputs'])
for name in ['mixer-product-plan.md','THIRD_PARTY.yml','verification/swift-control-accounting-candidate-2/collect.py','verification/swift-control-accounting-candidate-2/build_overlay.py','verification/swift-control-accounting-candidate-2/inventory.py','verification/swift-control-accounting-candidate-2/inventory-schema.json','verification/swift-control-accounting-candidate-2/unit.mir.gz','verification/swift-active-frames-implementation/inventory.py','verification/swift-active-frames-implementation/frozen-inventory-schema.json','verification/swift-active-frames-implementation/implementation-inventory-schema.json']:
    bindings[name]=sha(ROOT/name)
(HERE/'dependency-bindings.json').write_bytes(enc(dict(externalBindings=bindings,cargoLockSHA256=sha(VM/'Cargo.lock'),cargoTomlSHA256=sha(VM/'Cargo.toml'),packages=[dict(name='mixer-vm',version='0.1.0')],newDependencies=[],scope='standard-library-only host review; frozen accepted metadata and inventory helpers are reused as explicitly hashed tooling, with fresh source/compiler observations and new runtime cases')))
(HERE/'findings.json').write_bytes(enc(dict(unresolvedFindings=[],productCorrections=[],recommendation='accept-private-control-behavior-slice-for-root-review',observations=['First failure + at_failure preserved; record_cleanup may add/update after_cleanup as its separate observation.','Original removal underflow keeps Cleanup/None/None/resource None and actual WASI; invocation attribution is not invented.','Canonical logical reservation does not establish RSS, optimized stack or optimizer temporary bounds.','The prior candidate2 acceptance was source/accounting preflight only.','All seven independently authored groups and all required old suites remain separate evidence from future full dispatch.'],reviewOnlyIssues=failed+excluded)))

processes=subprocess.check_output(['ps','-Ao','pid,ppid,command']).decode();active=[line for line in processes.splitlines() if str(SCRATCH) in line]
assert not active,active
du=subprocess.check_output(['du','-sk',str(SCRATCH)]).decode().strip()
shutil.rmtree(SCRATCH);assert not SCRATCH.exists()
if (HERE/'__pycache__').exists():shutil.rmtree(HERE/'__pycache__')
cleanup=dict(ownedPath=str(SCRATCH),removed=True,observedBeforeRemovalKiB=du,activeScratchProcessesBeforeRemoval=active,liveVMUnchanged=digest(manifest(ROOT/'vm'))==inputs['baselineClosure'],nativeInstancesStarted=0,physicalRuns=0,screenCapture=False,otherProjectProcessesModified=False,scope='only this reviewer-owned host scratch; retained packet/executables remain')
(HERE/'cleanup.json').write_bytes(enc(cleanup))
receipt=dict(schema=1,observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='recommend-private-control-behavior-acceptance-pending-root',sourceRevision=inputs['sourceRevision'],baselineVMClosure=inputs['baselineClosure'],implementationVMClosure=inputs['candidateClosure'],reviewProbeVMClosure=digest(json.loads((HERE/'probe-manifest.json').read_text())),commands=len(commands),qualifyingRuntimeAndCheckCommands=qualifying,fullLibraryTestsPerConfiguration=dict(swiftDebug=168,swiftRelease=168,allDebug=197,allRelease=197),independentProbeGroups=7,independentProbeConfigurations=4,metadataConfigurations=8,canonicalFunctionsPerConfiguration=38,canonicalFieldsPerConfiguration=3752,positiveHookFields=400,originalFrameValueControlTestsPerConfiguration=46,originalFrozenParityTestsPerConfiguration=6,production=dict(header=1514504,frame=2211968,controlPermanent=105280,controlActive=1162520),unit=dict(header=2409184,frame=3950128,controlPermanent=122456,controlActive=2325256,hookPermanent=17144,hookActive=224),recommendation=True,rootAccepted=False,implementationAccepted=False,liveIntegrated=False,gaAcceptance=False,nativeRuntime=False,physicalRuntime=False,phonesDisconnected=True,liveVMUnchanged=True,fullDispatcher=False,Ready=False,publicInvocation=False,limits=['Logical authored/canonical ownership reservation only; no physical stack, optimizer temporary or RSS bound.','Actual original underflow is Cleanup with absent function/offset/resource and actual WASI; G08 remains pending.','Broad Clippy has the same 26 baseline diagnostic identities; library Clippy passes.','Root acceptance/live application, full dispatcher/Ready/public invocation, immutable separate-repository FieldLog release, native/final physical, signing/store/customer/operational/GA remain pending.'])
(HERE/'receipt.json').write_bytes(enc(receipt))
(HERE/'commands.json').write_bytes(enc(commands))
files={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='seal.json'}
seal=dict(schema=1,files=files,documentSHA256=sha(ROOT/'docs/swift-control-behavior-review.md'),externalBindings=bindings,implementationAccepted=False,gaAcceptance=False)
(HERE/'seal.json').write_bytes(enc(seal))
print('sealed independent recommendation; all required old and new host cases pass; owned scratch removed')
