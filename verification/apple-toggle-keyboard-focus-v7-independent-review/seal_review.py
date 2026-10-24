#!/usr/bin/env python3
"""Seal this independent review or verify it without writing any artifact."""
import datetime
import hashlib
import json
import pathlib
import shutil
import sys
import tarfile

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
DOC=ROOT/'docs/apple-toggle-keyboard-focus-v7-independent-review.md'
SEAL=HERE/'review-seal.json'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
read=lambda path:json.loads(path.read_bytes())
write=lambda path,value:path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')


def verify_inputs():
    inputs=read(HERE/'review-inputs.json')
    for name,digest in inputs.items():
        path=pathlib.Path(name) if name.startswith('/') else ROOT/name
        assert path.is_file() and not path.is_symlink() and sha(path)==digest,name
    for binding in read(HERE/'tool-link-bindings.json'):
        path=pathlib.Path(binding['path'])
        assert path.is_symlink() and path.readlink().as_posix()==binding['linkText'] and str(path.resolve())==binding['resolved'] and sha(path)==binding['sha256']
    return len(inputs)


def verify_archive():
    manifest=read(HERE/'host-evidence-manifest.json')
    with tarfile.open(HERE/'host-evidence.tar.gz','r:gz') as archive:
        names=[]
        for member in archive.getmembers():
            assert member.isfile() and member.name in manifest and member.name not in names
            data=archive.extractfile(member).read()
            assert len(data)==manifest[member.name]['bytes'] and hashlib.sha256(data).hexdigest()==manifest[member.name]['sha256']
            names.append(member.name)
        assert set(names)==set(manifest)
    return len(manifest)


def seal():
    assert not SEAL.exists(),'Never overwrite sealed independent review'
    input_count=verify_inputs()
    work=HERE/'host-evidence';manifest={}
    for path in sorted(work.rglob('*')):
        assert not path.is_symlink()
        if path.is_file():manifest[str(path.relative_to(HERE))]=dict(bytes=path.stat().st_size,sha256=sha(path))
    assert manifest
    with tarfile.open(HERE/'host-evidence.tar.gz','w:gz') as archive:
        for name in manifest:archive.add(HERE/name,arcname=name,recursive=False)
    write(HERE/'host-evidence-manifest.json',manifest)
    assert verify_archive()==len(manifest)
    assert work.resolve()==work and work.parent==HERE
    size=sum(value['bytes'] for value in manifest.values())
    shutil.rmtree(work)
    write(HERE/'review-cleanup.json',dict(syntheticWorkingTreeArchived=True,archive='host-evidence.tar.gz',manifest='host-evidence-manifest.json',archivedFiles=len(manifest),bytesArchivedBeforeRemoval=size,workingTreeAbsent=not work.exists(),compilerScratchAbsent=not (HERE/'host-build-scratch').exists(),nativeInstanceCreated=False,nativeInstanceQueried=False,otherProjectProcessesOrDataTouched=False,scope='Only exact owned generated host evidence working tree removed after per-file archive verification; all attempt bytes retained'))
    paths=[DOC,*[path for path in sorted(HERE.rglob('*')) if path.is_file()]]
    assert all(not path.is_symlink() for path in paths)
    files={str(path.relative_to(ROOT)):sha(path) for path in paths}
    result=dict(schema='mixer.apple-toggle.keyboard-v7-independent-review.1',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),accountableReviewer='/root/apple_keyboard_v7_independent_review',
                producerSealSHA256='1332308b51182f2ead68a774f135bc3121e00b7385cbd0337395a90d53175579',rootSelectionSHA256='a56b15d641c3dd71fcb7e3472b19c5b8156736091c9fea905c07f6ba1ea8b6da',inputFileCount=input_count,
                status='changes-required-persistence-acknowledgement-blockers',nativeSelectionAccepted=False,findings=['PERSIST-POSTWRITE-JOURNAL','PERSIST-PAYLOAD-ORPHAN','PERSIST-ACK-SUMMARY'],independentActualHostMethodsPassed=13,independentActualResolverControlsPassed=61,unchangedTransportControlsPassed=[16,35],frozenV6RecordsReplayed=275,syntheticEvidenceFilesArchived=len(manifest),
                fileCount=len(files),files=files,nativeExecuted=False,nativeInstancesQueried=False,applicationCasesExecuted=0,applicationCasesUnrun=['keyboard-disabled-off','keyboard-disabled-on','keyboard-enabled-off','keyboard-enabled-on','keyboard-stale-off','keyboard-stale-on'],nativeKeyboardQualification=False,carrierAccepted=False,gaAccepted=False,physicalPhones='disconnected-deferred')
    write(SEAL,result)
    return check()


def check():
    seal=read(SEAL)
    assert seal['fileCount']==len(seal['files'])
    for name,digest in seal['files'].items():
        path=ROOT/name
        assert path.is_file() and not path.is_symlink() and sha(path)==digest,name
    actual={str(path.relative_to(ROOT)) for path in HERE.rglob('*') if path.is_file() and path!=SEAL}|{str(DOC.relative_to(ROOT))}
    assert actual==set(seal['files']),'Unsealed extra/missing review artifact'
    assert verify_inputs()==seal['inputFileCount']
    assert verify_archive()==seal['syntheticEvidenceFilesArchived']
    return dict(status=seal['status'],sealSHA256=sha(SEAL),filesVerified=seal['fileCount'],inputsVerified=seal['inputFileCount'],archivedEvidenceFilesVerified=seal['syntheticEvidenceFilesArchived'],nativeSelectionAccepted=False,nativeExecuted=False,gaAccepted=False)


if __name__=='__main__':
    action=sys.argv[1] if len(sys.argv)>1 else 'check'
    assert action in ['seal','check']
    print(json.dumps(seal() if action=='seal' else check(),sort_keys=True))
