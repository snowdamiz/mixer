#!/usr/bin/env python3
"""Read-only source/hash/archive/receipt verification; no build or guest execution."""
from pathlib import Path
import gzip, hashlib, json, re, subprocess, tarfile
H=Path(__file__).resolve().parent;R=H.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):return json.loads((H/n).read_text())
seal=read('seal.json')
actual={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file()}
assert actual==set(seal['files'])|{'seal.json'}
for n,v in seal['files'].items():
    p=H/n;assert sha(p)==v,(n,'content mismatch');assert p.stat().st_mode&0o222==0,(n,'writable')
assert (H/'seal.json').stat().st_mode&0o222==0
for n,v in seal['externalFiles'].items():assert sha(R/n)==v,(n,'external binding drift')
assert not (H/'owned-scratch').exists()
r=read('receipt.json');a=read('command-audit.json');m=read('matrix.json');s=read('source-selection.json')
assert not r['liveIntegrationSelected'] and not r['full53MBReactorSelected'] and not r['gaAccepted']
assert r['finalMatrixPassingNamedExecutions']==2314 and not r['fullFormattingPass']
assert r['swiftOnlyLibraryClippyWarningsDeniedPass'] and r['exactPhaseHelperReallyInvoked']
final=read('final-source-manifest.json');candidate=read('candidate-input-manifest.json');live=read('live-input-manifest.json')
assert len(final)==len(candidate)==len(live)==132
assert sha(H/'final-source-manifest.json')==s['final132FileClosure']=='524a006715a63b14087398161e1d1d9551fea2faf177e5e5c1a1d10f14c5ed4c'
assert sha(H/'candidate-input-manifest.json')=='cc52d92302ed81a71eeb8856644686b94657c1a505cf67b3f26c3bd91ad073c3'
assert sha(H/'live-input-manifest.json')=='3ffa1055e462be74c10ee9830bf891bbd196a896dfc7a66dc6befe2a6d9bb70f'
assert [n for n in final if final[n]!=candidate[n]]==s['changedFromCandidate']==['src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/execution_tests.rs','src/experimental_swift_reactor/lifecycle_tests.rs']
for n,v in final.items():assert sha(H/'source'/n)==v
for n,v in live.items():assert sha(R/'vm'/n)==v,(n,'live source changed after isolated slice')
for n,v in read('input-bindings.json').items():assert sha(H/'input-documents'/n)==v,(n,'original input bytes not preserved')
assert read('plan-provenance-recovery.json')['originalBytesRecoveredExactly']
for p in (H/'commands').glob('*/receipt.json'):
    c=json.loads(p.read_text());label=p.parent.name
    assert c['sourceUnchanged'] and c['ownedGroupAbsent'] and all(c['streamsClosed'].values()) and not c['signals']
    assert sha(p.parent/'source-manifest.json')==c['sourceManifestSHA256']
    for n in ('stdout','stderr'):assert sha(p.parent/n)==c[n+'SHA256']
    for n,v in json.loads((p.parent/'source-manifest.json').read_text()).items():assert sha(H/'source-objects'/v)==v
    tests=[];stdout=(p.parent/'stdout').read_text()
    if c['action'] in ('suite','named','observe'):
        for match in re.finditer(r'^test ([^\n]+?) \.\.\. ([\s\S]*?)(?=^test [^\n]+? \.\.\. |^failures:|^test result:|\Z)',stdout,re.M):
            name,body=match.groups();status=re.search(r'^(ok|FAILED|ignored[^\n]*)\s*$',body,re.M);assert status
            tests.append({'name':name,'result':status.group(1)})
    assert tests==a[label]['namedTests']
for context,row in m.items():
    assert row['failed']==0 and row['ignored']==9 and row['passed']==(519 if context.startswith('swift') else 638)
    assert row['sourceManifestSHA256']==s['final132FileClosure'] and row['exactPhaseHelperThroughRealEnclosingTest']
    assert a[row['command']]['qualifyingPass']
    assert any(t['name']=='experimental_swift_reactor::cache_tests::construction_and_operation_phase_boundaries' and t['result']=='ok' for t in row['namedTests'])
assert sum(x['passed'] for x in a.values())==4095 and sum(x['failed'] for x in a.values())==15
assert all(not x['zeroTestCommandNonqualifying'] for x in a.values())
cleanup=read('cleanup.json');assert cleanup['scratchAbsent'] and cleanup['ownedGroupsAbsent'] and cleanup['holdersEmpty'] and cleanup['inodeStableImmediatelyBeforeRemoval']
for arc in cleanup['binaryArchives']:
    p=H/arc['archive'];assert sha(p)==arc['archiveSHA256'];raw=gzip.decompress(p.read_bytes())
    assert len(raw)==arc['uncompressedBytes'] and hashlib.sha256(raw).hexdigest()==arc['uncompressedSHA256']
assert len(cleanup['binaryArchives'])==148
with tarfile.open(H/'final-source.tar.gz','r:gz') as archive:
    assert len(archive.getmembers())==132
    for member in archive.getmembers():assert hashlib.sha256(archive.extractfile(member).read()).hexdigest()==final[member.name.removeprefix('source/')]
ps=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,comm='],text=True,timeout=30)
assert not [x for x in ps.splitlines() if len(x.split())>=2 and int(x.split()[1]) in cleanup['processGroupsChecked']]
print(json.dumps({'verifiedFiles':len(seal['files']),'externalBindings':len(seal['externalFiles']),'sealSHA256':sha(H/'seal.json'),'finalSourceClosure':s['final132FileClosure'],'finalNamedPasses':2314,'contexts':{k:{n:v[n] for n in ['passed','failed','ignored']} for k,v in m.items()},'liveUnchanged':True,'scratchAbsent':True,'fullFormattingPass':False,'ClippyPass':True,'liveIntegrationSelected':False,'GA':False},sort_keys=True))
