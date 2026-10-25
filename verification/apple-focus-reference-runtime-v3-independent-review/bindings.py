#!/usr/bin/env python3
"""Independent data-only verification. No producer imports or native execution."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PRODUCER = ROOT/'verification/apple-focus-reference-runtime-v3'
EXPECTED_HANDOFF = 'f50006ea6fbe274eac4a78c214a33da4b77c4249b0ef2e8a19f1e0c4200e18f1'
EXPECTED_PACKET = '89e4b9b819bacc7ba69aee1fa2344245bf2eb26a3b8ed72a33a169f574f3fd60'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
stable = lambda value: (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()

def row(path, official_alias=False):
    resolved=path.resolve()
    assert resolved==path or official_alias, 'Redirected input: '+str(path)
    info=resolved.lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_nlink==1, str(path)
    data=resolved.read_bytes()
    return {'kind':'file','mode':stat.S_IMODE(info.st_mode),'bytes':len(data),'sha256':sha(data)}

def archive(path, rows, expected_hash, prefix='', snapshot=None, expected_dirs=None):
    assert row(path)['sha256']==expected_hash
    files={}; directories=[]
    with tarfile.open(path,'r:gz') as tf:
        seen=set()
        for member in tf:
            name=member.name
            assert name not in seen and not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
            seen.add(name)
            assert member.isdir() or member.isfile(), 'Archive link/special rejected'
            if member.isdir():
                assert member.mode==0o755
                directories.append(name)
                continue
            assert name.startswith(prefix)
            relative=name[len(prefix):]
            assert relative in rows
            raw=tf.extractfile(member).read()
            observed={'kind':'file','mode':member.mode,'bytes':len(raw),'sha256':sha(raw)}
            assert observed==rows[relative], relative
            files[relative]=observed
            if snapshot is not None:
                target=snapshot/relative
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(raw)
        assert files==rows, 'Archive member inventory differs'
        if expected_dirs is not None: assert sorted(directories)==sorted(expected_dirs)
    return {'archiveSHA256':expected_hash,'fileCount':len(files),'fileTreeSHA256':sha(stable(files)),'directoryCount':len(directories)}

def verify(snapshot=None):
    handoff=json.loads((PRODUCER/'handoff.json').read_bytes())
    assert row(PRODUCER/'handoff.json')['sha256']==EXPECTED_HANDOFF
    assert row(PRODUCER/'packet.json')['sha256']==EXPECTED_PACKET
    assert sha(stable(handoff['members']))==handoff['memberTreeSHA256']
    bindings={}
    for name,expected in handoff['members'].items():
        assert name.startswith(('verification/apple-focus-reference-runtime-v3/','docs/apple-focus-reference-runtime-v3.md'))
        observed=row(ROOT/name);assert observed==expected,name;bindings[name]=observed
    bindings['verification/apple-focus-reference-runtime-v3/handoff.json']=row(PRODUCER/'handoff.json')
    lock=json.loads((PRODUCER/'input-lock.json').read_bytes())
    official='/Applications/Xcode_26.6.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator26.5.sdk/SDKSettings.json'
    aliases={}
    for name,expected in lock.items():
        assert 'hosted' not in name and 'catalog' not in name and 'authority-driver' not in name
        path=Path(name) if name.startswith('/') else ROOT/name
        observed=row(path,name==official);assert observed==expected,name;bindings[name]=observed
        if path.resolve()!=path: aliases[name]=str(path.resolve())
    for name in lock:
        if name.endswith('/handoff.json'):
            historical=json.loads((ROOT/name).read_bytes())
            assert sha(stable(historical['members']))==historical['memberTreeSHA256'],name
            for member,expected in historical['members'].items(): assert bindings[member]==expected,member
    packet=json.loads((PRODUCER/'packet.json').read_bytes())
    assert packet['schema']=='mixer.apple-focus-reference-runtime-packet.3'
    assert sha(stable(packet['ownedSources']))==packet['ownedSourceTreeSHA256']
    for name,expected in {**packet['ownedSources'],**packet['files']}.items(): assert row(PRODUCER/name)==expected,name
    assert row(ROOT/'docs/apple-focus-reference-runtime-v3.md')==packet['documentation']
    manifest=json.loads((PRODUCER/'runtime-source-manifest.json').read_bytes())
    assert sha(stable(manifest['files']))==manifest['treeSHA256']
    source=archive(PRODUCER/'runtime-sources.tar.gz',manifest['files'],manifest['archive']['sha256'],'selected/',snapshot,manifest['directories'])
    old=ROOT/'verification/apple-focus-diagnostic-runtime-v1'
    oldmanifest=json.loads((old/'selected-runtime-source-manifest.json').read_bytes())
    older=archive(old/'selected-runtime-sources.tar.gz',oldmanifest['files'],oldmanifest['archive']['sha256'],'selected/',expected_dirs=oldmanifest['directories'])
    v1=ROOT/'verification/apple-focus-reference-diagnostic-v1'
    prepared=json.loads((v1/'prepared.json').read_bytes())
    assert sha(stable(prepared['derivativeSources']))==packet['sourceTreeSHA256']
    accepted=archive(v1/'accepted-sources.tar.gz',prepared['derivativeSources'],prepared['archive']['sha256'],'accepted/')
    products=json.loads((v1/'compile-attempt-1/product-manifest.json').read_bytes())
    assert sha(stable(products['products']))==packet['productTreeSHA256']
    product=archive(v1/'compile-attempt-1/products.tar.gz',products['products'],packet['productArchiveSHA256'])
    return {'handoffSHA256':EXPECTED_HANDOFF,'packetSHA256':EXPECTED_PACKET,'bindings':bindings,'bindingTreeSHA256':sha(stable(bindings)),'sourceArchive':source,'historicalSourceArchive':older,'acceptedSourceArchive':accepted,'productArchive':product,'officialAliases':aliases,'nativeExecuted':False,'producerCodeImported':False}

if __name__=='__main__':
    attempt=BASE/'attempt-1';attempt.mkdir()
    result=verify(attempt/'source-inspection')
    (attempt/'frozen-inputs-before.json').write_bytes(stable(result))
    copies=attempt/'producer-copy';copies.mkdir()
    handoff=json.loads((PRODUCER/'handoff.json').read_bytes())
    for name in handoff['members']:
        path=Path(name)
        if path.parent==Path('verification/apple-focus-reference-runtime-v3'):
            (copies/path.name).write_bytes((ROOT/name).read_bytes())
    (attempt/'source-inspection-manifest.json').write_bytes(stable(json.loads((PRODUCER/'runtime-source-manifest.json').read_bytes())['files']))
    print(json.dumps({k:v for k,v in result.items() if k!='bindings'},sort_keys=True))
