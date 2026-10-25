#!/usr/bin/env python3
"""Read-only finite packet integrity and recorded-result verification."""
from pathlib import Path,PurePosixPath
import hashlib,json,re,tarfile
H=Path(__file__).resolve().parent
ROOT=H.parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
seal=json.loads((H/'seal.json').read_text())
assert sha(H/'seal.json')==(H/'seal.sha256').read_text().strip()
for n,digest in seal['members'].items():
    p=PurePosixPath(n)
    assert not p.is_absolute() and '..' not in p.parts
    assert sha(H/n)==digest,n
for n,digest in seal['externalMembers'].items():assert sha(ROOT/n)==digest,n
manifests={}
for label,name in [('baseline','baseline-test-manifest.json'),('candidate','candidate-manifest.json')]:
    expected=json.loads((H/name).read_text());manifests[label]=expected
    assert len(expected)==132
    with tarfile.open(H/f'{label}-source.tar.gz','r:gz') as archive:
        members=archive.getmembers()
        assert len(members)==132 and all(m.isfile() for m in members)
        assert {m.name for m in members}==set(expected)
        actual={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in members}
    assert actual==expected,label
original=json.loads((H/'baseline-manifest.json').read_text())
assert sha(H/'baseline-manifest.json')=='16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd'
assert [n for n in original if original[n]!=manifests['baseline'][n]]==['src/experimental_swift_reactor/cache_tests.rs']
assert [n for n in original if original[n]!=manifests['candidate'][n]]==['src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs']
for receipt in (H/'commands').glob('*/receipt.json'):
    r=json.loads(receipt.read_text());folder=receipt.parent
    for field,name in [('stdoutSHA256','stdout'),('stderrSHA256','stderr'),('sourceManifestSHA256','source-manifest.json')]:
        assert r[field]==sha(folder/name),(folder.name,name)
unlaunched=json.loads((H/'invocation-repair.json').read_text())['attempts']
assert sorted(p.name for p in (H/'commands').iterdir() if p.is_dir() and not (p/'receipt.json').exists())==sorted(unlaunched)
summary=json.loads((H/'result-summary.json').read_text())
for name in summary['selectedFinalCommands']:
    r=json.loads((H/'commands'/name/'receipt.json').read_text())
    assert r['exitCode']==0
    label='baseline' if name.startswith('baseline') else 'candidate'
    assert json.loads((H/'commands'/name/'source-manifest.json').read_text())==manifests[label],name
for pair in summary['genericOutputComparisons']:
    normalized=[]
    for label in ['baseline','candidate']:
        s=(H/'commands'/pair[label]/'stdout').read_text()
        normalized.append(re.sub(r'finished in [0-9.]+s','finished in <elapsed>s',s))
    assert normalized[0]==normalized[1]
    assert hashlib.sha256(normalized[0].encode()).hexdigest()==pair['normalizedStdoutSHA256']
assert summary['fullSwiftReactorAttempts']==summary['nativeAttempts']==0
assert not summary['actualWorkloadBenefitProven'] and not summary['liveIntegrationSelected'] and not summary['gaAccepted']
cleanup=json.loads((H/'cleanup.json').read_text())
assert cleanup['ownedProcessesAbsent'] and cleanup['holdersAbsent'] and cleanup['deviceInodeChecksPassed']
# Restoring these paths for a later bounded review is permitted, so verify the
# recorded retirement rather than asserting their perpetual absence.
live={n:sha(ROOT/'vm'/n) for n in original}
print(json.dumps({'verified':True,'sealedMembers':len(seal['members']),'archives':2,'sourceFilesPerArchive':132,'genericOutputsEqual':True,'liveVMStillMatchesOriginal':live==original,'fullReactorAttempts':0,'nativeAttempts':0,'scope':'finite candidate only; independent acceptance and target comparison remain pending'}))
