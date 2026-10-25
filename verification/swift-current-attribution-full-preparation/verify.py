#!/usr/bin/env python3
"""Read-only prepared-packet verification; no compiler, live VM, guest, Git or network."""
from pathlib import Path
import ast,difflib,gzip,hashlib,json,subprocess,tarfile
H=Path(__file__).resolve().parent;R=H.parent.parent;C=H.parent/'swift-cache-current-attribution-observer';P=H.parent/'swift-exact-reactor-after-plan-reuse'
load=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
seal=load(H/'prepared-seal.json')
files={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name!='prepared-seal.json'}
assert files==set(seal['files'])
for n,d in seal['files'].items():assert sha(H/n)==d,n
for n,d in seal['externalFiles'].items():assert sha(R/n)==d,n
binding=load(H/'binding.json')
for info in binding['inputs']:assert sha(info['path'])==info['sha256'],info['path']
assert binding['baselineClosure']==sha(H/'baseline-manifest.json')=='16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd'
assert binding['sourceRevisionContext']=='6b8aba350224ed19f678669bdbea6b359d8de68b'
assert sha(C/'seal.json')=='e4a520641fbad904381bc7438feb0baee4dfca7d716806262da80ac4b20f0305'
assert sha(H.parent/'swift-cache-attribution-independent-review/seal.json')=='9f7d6c2357f0464d09932c4632cba543ecf8a20073ea6a3d9f07030de4175ce4'
assert sha(P/'result-seal.json')=='8f04098c444d63e9d638c32e22297eccdad346222241529ef710c524473e7526'
base=load(H/'baseline-manifest.json');candidate=load(C/'copied-source-manifest.json');prepared=load(H/'copied-build-manifest.json')
with tarfile.open(C/'isolated-source.tar.gz','r:gz') as archive:
    members=archive.getmembers()
    assert len(members)==132 and len({m.name for m in members})==132
    assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
    source={m.name:archive.extractfile(m).read() for m in members}
assert {n:hashlib.sha256(b).hexdigest() for n,b in source.items()}==candidate
source['src/experimental_swift_reactor/cache_tests.rs']+=b'\n'+(H/'adapter.rs').read_bytes()+b'\n'+(H/'adapter-controls.rs').read_bytes()
append='\n// Isolated diagnostic only; baseline production bytes are unchanged.\ninclude!('+json.dumps(str(H/'harness.rs'))+');\n'
source['src/experimental_swift_reactor/lifecycle_tests.rs']+=append.encode()
assert {n:hashlib.sha256(b).hexdigest() for n,b in source.items()}==prepared
assert len(base)==len(candidate)==len(prepared)==132
assert [n for n in candidate if prepared[n]!=candidate[n]]==['src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/lifecycle_tests.rs']
assert [n for n in base if prepared[n]!=base[n]]==['src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/lifecycle_tests.rs']
for filename,patch in [('harness.rs','harness-changes.patch'),('diagnostic.py','driver-changes.diff')]:
    expected=''.join(difflib.unified_diff((P/filename).read_text().splitlines(True),(H/filename).read_text().splitlines(True),fromfile='historical/'+filename,tofile='prepared/'+filename))
    assert (H/patch).read_text()==expected
old=(P/'harness.rs').read_text();new=(H/'harness.rs').read_text()
assert old.split('    #[test]\n    fn exact_reactor_target_once()',1)[1]==new.split('    #[test]\n    fn exact_reactor_target_once()',1)[1]
old_driver=(P/'diagnostic.py').read_text();new_driver=(H/'diagnostic.py').read_text()
functions=lambda s:{n.name:ast.get_source_segment(s,n) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
a,b=functions(old_driver),functions(new_driver)
for n in ('observe_group','record_command','build','strict_json','events','cleanup','host_controls'):assert a[n]==b[n],n
expected=a['execute'].replace('    save(name + "-result.json", result)\n','    save(name + "-result.json", result)\n    save(name + "-telemetry.json", telemetry.classify(stdout, observed))\n')
expected=expected.replace('        assert selection["maxTargetAttempts"] == 1\n','        assert selection["maxTargetAttempts"] == 1\n        assert selection["sourceManifestSHA256"] == sha(HERE / "copied-build-manifest.json")\n        assert selection["telemetryClassifierSHA256"] == sha(HERE / "telemetry.py")\n        assert selection["outputContractSHA256"] == sha(HERE / "output-contract.json")\n')
assert expected==b['execute']
commands=['build-001','list-001','control-001','control-002','adapter-controls','driver-observation-controls']
owned=set()
for name in commands:
    q=H/'commands'/name;r=load(q/'receipt.json');owned.add(r['processGroup'])
    assert r['passed'] and r['exitCode']==0 and not r['timedOut'] and not r['signalSent'] and r['processGroupEmpty'] and r['rawStreamEOFConfirmed']
    assert r['sourceClosure']==sha(H/'copied-build-manifest.json')
    assert r['stdout']['sha256']==sha(q/'stdout') and r['stderr']['sha256']==sha(q/'stderr')
    assert r['harnessSHA256']==sha(H/'harness.rs')==sha(q/'harness.rs')
    assert r['driverSHA256']==sha(H/'diagnostic.py')==sha(q/'diagnostic.py')
    assert r['toolsBefore']==binding['compilerTools'] and r['toolsUnchanged']
    assert load(q/'source-manifest.json')==prepared
assert '--no-run' in load(H/'commands/build-001/receipt.json')['argv']
assert '3 passed; 0 failed; 0 ignored; 0 measured; 392 filtered out' in (H/'commands/adapter-controls/stdout').read_text()
assert 'Ran 14 tests' in (H/'commands/driver-observation-controls/stderr').read_text() and (H/'commands/driver-observation-controls/stderr').read_text().endswith('OK\n')
for name in ('control-001','control-002'):
    result=load(H/(name+'-result.json'));t=load(H/(name+'-telemetry.json'));ev=load(H/(name+'-events.json'))
    assert result['commandPassed'] and result['diagnosticCompleted'] and result['ownedCleanupEmpty'] and not result['targetAttempted'] and result['firstFailure'] is None
    assert t['status']=='valid' and not t['issues'] and t['outputBytes']==3716 and len(t['snapshots'])==6
    final=next(e['payload'] for e in ev if e['event']=='final_cleanup_usage')
    assert final['instructions']==5 and final['cache_work']==5166 and final['cleanup_invariant'] is None
    assert all(v['current']==0 for k,v in final['reservations'].items() if isinstance(v,dict)) and final['reservations']['live_tickets']==0
    assert all(v['current']==0 for v in final['live'].values())
selected=load(H/'prepared-selection.json');proposal=load(H/'proposed-command.json');template=load(H/'root-selection-template.json')
for name,digest in selected['boundEvidence'].items():assert sha(H/name)==digest,name
assert selected['status']=='prepared-awaiting-root-exact-selection' and not selected['targetAttempted'] and selected['maxTargetAttempts']==1
assert proposal['outerDeadlineSeconds']==170 and proposal['terminationGraceSeconds']==proposal['killWaitSeconds']==5
assert proposal['validationDeadlineMs']==120000 and proposal['cumulativeRuntimeDeadlineMs']==proposal['cumulativeWasiDeadlineMs']==30000
assert selected['argv']==proposal['argv'] and selected['outerCommand']==proposal['outerCommand']
assert template['exactCommandSelected'] is False and template['sourceManifestSHA256']==sha(H/'copied-build-manifest.json') and template['telemetryClassifierSHA256']==sha(H/'telemetry.py') and template['outputContractSHA256']==sha(H/'output-contract.json')
with gzip.open(H/'bin/exact-tests.gz','rb') as stream:binary=stream.read()
info=load(H/'binary.json')['retained'];assert len(binary)==info['bytes'] and hashlib.sha256(binary).hexdigest()==info['sha256']==selected['binarySHA256']
cleanup=load(H/'cleanup.json');assert cleanup['removed'] and cleanup['holderExitCode']==1
assert not (H/'owned-scratch').exists() and not (H/'bin/exact-tests').exists()
assert not (H/'root-selection.json').exists() and not (H/'target-attempt-started.json').exists() and not (H/'commands/target-once').exists()
ps=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,comm='],text=True,timeout=10)
assert not [row for row in ps.splitlines() if len(row.split())>=2 and int(row.split()[1]) in owned]
receipt=load(H/'receipt.json');assert receipt['fullTargetAttempts']==0 and not receipt['productionSourceChanged'] and not receipt['gaAccepted']
assert receipt['finiteRustTestExecutionsPassed']==5 and receipt['hostControlsPassed']==14 and receipt['tinySyntheticGuestInstructions']==10
print(json.dumps({'preparedIntegrityVerified':True,'sealedMembers':len(files),'sourceFiles':132,'deltaFromAcceptedObserverFiles':2,'finiteRustTestExecutionsPassed':5,'hostControlsPassed':14,'tinySyntheticGuestInstructions':10,'fullTargetAttempts':0,'rootSelectionPending':True,'ownedProductsCleaned':True,'gaAccepted':False},sort_keys=True))
