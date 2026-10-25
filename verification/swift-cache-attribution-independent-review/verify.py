#!/usr/bin/env python3
"""Read-only review audit; no compilation, guest, native, network or live source."""
from pathlib import Path
import hashlib,json,subprocess,tarfile
H=Path(__file__).resolve().parent
R=H.parent.parent
C=H.parent/'swift-cache-current-attribution-observer'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
seal=load(H/'seal.json')
files={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name!='seal.json'}
assert files==set(seal['files'])
for n,d in seal['files'].items():assert sha(H/n)==d,n
for n,d in seal['externalFiles'].items():assert sha(R/n)==d,n
assert sha(C/'seal.json')=='e4a520641fbad904381bc7438feb0baee4dfca7d716806262da80ac4b20f0305'
candidate=load(C/'seal.json')
assert len(candidate['files'])==43
for n,d in candidate['files'].items():assert sha(C/n)==d,n
audit=load(H/'source-audit.json')
assert audit['sourceFiles']==132 and audit['unchangedBaselineFiles']==129 and audit['originalTestsPrefixByteIdentical']
assert audit['baselineClosure']=='16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd'
assert audit['candidateSourceManifestSHA256']==sha(C/'copied-source-manifest.json')
assert audit['candidateArchiveSHA256']==sha(C/'isolated-source.tar.gz')
assert not audit['liveSourceRead'] and not audit['gitQueried']
parent=H.parent/'swift-plan-cache-remaining-work-diagnosis'
assert sha(parent/'seal.json')=='3a52d3f20cf852da7521fc3345a177ef6f8a7f157ebf2da7e3e63d01bc725b3d'
parent_seal=load(parent/'seal.json')
assert len(parent_seal['files'])==46
for n,d in parent_seal['files'].items():assert sha(parent/n)==d,n
base=load(C/'baseline-manifest.json');modified=load(C/'copied-source-manifest.json')
assert set(base)==set(modified) and len(base)==132
assert sha(C/'baseline-manifest.json')==audit['baselineClosure']
with tarfile.open(C/'isolated-source.tar.gz','r:gz') as t:
    members=t.getmembers()
    assert len(members)==132 and len(set(m.name for m in members))==132
    assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
    source={m.name:t.extractfile(m).read() for m in members}
assert {n:hashlib.sha256(b).hexdigest() for n,b in source.items()}==modified
changed=sorted(n for n in base if base[n]!=modified[n])
assert changed==audit['changedFiles']
with tarfile.open(parent/'isolated-source.tar.gz','r:gz') as t:
    baseline={m.name:t.extractfile(m).read() for m in t.getmembers()}
for n in changed:baseline[n]=(parent/'originals'/n).read_bytes()
assert {n:hashlib.sha256(b).hexdigest() for n,b in baseline.items()}==base
assert all(source[n]==baseline[n] for n in source if n not in changed)
testpath='src/experimental_swift_reactor/cache_tests.rs'
assert source[testpath]==baseline[testpath]+b'\n'+(C/'observer-and-controls.rs').read_bytes()
source[testpath]+=b'\n'+(H/'independent-controls.rs').read_bytes()
review=load(H/'review-source-manifest.json')
assert len(review)==132 and {n:hashlib.sha256(b).hexdigest() for n,b in source.items()}==review
delta=load(H/'review-source-delta.json')
assert delta['changedFiles']==[testpath]
assert delta['appendedControlSHA256']==sha(H/'independent-controls.rs')
assert delta['reviewManifestSHA256']==sha(H/'review-source-manifest.json')
for n,d in audit['contextArchives'].items():assert sha(H/'context'/n)==d
command=load(H/'command.json')
assert command['exitCode']==0 and not command['timedOut'] and not command['signalsSent']
assert command['sourceManifestSHA256']==sha(H/'review-source-manifest.json')
assert command['stdoutSHA256']==sha(H/'finite.stdout') and command['stderrSHA256']==sha(H/'finite.stderr')
assert command['argv'][1:]==['test','--lib','--locked','--offline','--no-default-features','--features','experimental-swift-reactor','--release','experimental_swift_reactor::cache_tests::independent_attribution_','--','--nocapture','--test-threads=1']
assert command['environment']['CARGO_NET_OFFLINE']=='true' and command['environment']['CARGO_BUILD_JOBS']=='2'
stdout=(H/'finite.stdout').read_text()
assert '3 passed; 0 failed; 0 ignored; 0 measured; 390 filtered out' in stdout
assert stdout.count('REVIEW_POLICY ')==2 and stdout.count('REVIEW_BITMAP ')==1 and stdout.count('REVIEW_INVALID ')==4
assert 'rejected_site=4 published_plan=0 bitmap=0' in stdout and 'rejected_site=12 published_plan=1 bitmap=0' in stdout
assert 'mode=3 invalid=8 partial_discarded_bytes=64' in stdout
cleanup=load(H/'cleanup.json');pre=load(H/'cleanup-preflight.json')
assert cleanup['ownedPathsAbsent'] and cleanup['allOwnedProcessGroupsAbsent'] and cleanup['holderChecksEmpty'] and cleanup['deviceInodeChecksPassed']
assert not cleanup['signalsSent'] and not cleanup['liveVmQueried'] and not cleanup['nativeInstancesUsed'] and not cleanup['otherProjectsTouched']
assert not pre['matchingOwnedProcesses']
assert all(r['exitCode']==1 and not r['stdout'] and not r['stderr'] for r in pre['holders'].values())
assert all(not (H/n).exists() for n in ['owned-source','owned-target','owned-tmp'])
ps=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,comm='],text=True,timeout=10)
assert not [r for r in ps.splitlines() if len(r.split())>=2 and int(r.split()[1])==command['processGroup']]
receipt=load(H/'receipt.json');findings=load(H/'findings.json')
assert receipt['verdict']=='accepted-for-diagnostic-preparation-only' and not findings['blockingFindings']
assert receipt['finiteTestsPassed']==3 and receipt['fullTargetAttempts']==receipt['completeVmRegressionRuns']==0
assert not receipt['productionSourceChanged'] and not receipt['gaAccepted']
print(json.dumps({'integrityVerified':True,'sealedMembers':len(files),'sourceFiles':132,'unchangedBaselineFiles':129,
    'independentFinitePasses':3,'independentCases':7,'blockingFindings':0,'fullTargetAttempts':0,
    'cleanupComplete':True,'verdict':receipt['verdict'],'gaAccepted':False},sort_keys=True))
