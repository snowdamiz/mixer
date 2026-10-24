"""Seal/verify the bounded host-only V9 independent review; never native operations."""
import datetime
import hashlib
import io
import json
import pathlib
import shutil
import sys
import tarfile

HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
DOC=ROOT/'docs/apple-toggle-keyboard-focus-v9-independent-review.md';SEAL=HERE/'review-seal.json'
OPERATIONAL={'seal-command.stdout','seal-command.stderr','seal-command.json',
             'check-command.stdout','check-command.stderr','check-command.json'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
write=lambda p,v:p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')


def verify_inputs():
    inputs=read(HERE/'review-inputs.json')
    links={item['path']:item for item in read(HERE/'tool-link-bindings.json')}
    for name,expected in inputs.items():
        path=pathlib.Path(name) if name.startswith('/') else ROOT/name
        assert path.is_file() and sha(path)==expected,name
        if path.is_symlink():
            link=links[str(path)]
            assert str(path.readlink())==link['target'] and str(path.resolve())==link['resolved'],name
    inventory=read(HERE/'inventory.json')
    for name,expected in inventory['loadedSourceFiles'].items():
        assert sha(ROOT/name)==expected,name
    return len(inputs)


def verify_execution():
    attempts={name:read(HERE/'commands'/name/'commands.json') for name in ['attempt-1','attempt-2','attempt-3','attempt-4']}
    assert not attempts['attempt-1']['passed']
    assert all(attempts[name]['passed'] for name in ['attempt-2','attempt-3','attempt-4'])
    for name,result in attempts.items():
        for rel,expected in result['sourceFiles'].items():
            assert sha(HERE/'commands'/name/pathlib.Path(rel).name)==expected,(name,rel)
        for command in result['commands']:
            for channel in ['stdout','stderr']:
                assert sha(HERE/'commands'/name/(command['name']+'.'+channel))==command[channel+'SHA256']
    for attempt in ['attempt-2','attempt-3']:
        sources=attempts[attempt]['sourceFiles']
        for name in ['independent_flow.py','host_checks.py']+(['supplemental_checks.py'] if attempt=='attempt-3' else []):
            assert sha(HERE/name)==sources[str((HERE/name).relative_to(ROOT))],name
    base=read(HERE/'independent-controls.json');extra=read(HERE/'supplemental-controls.json')
    assert base['passed'] and extra['passed'] and base['controlCount']==60 and extra['controlCount']==12
    assert sum(x['requestCount'] for x in base['controls']+extra['controls'])==1546
    return attempts


def verify_archive():
    manifest=read(HERE/'host-evidence-manifest.json');seen=set()
    with tarfile.open(HERE/'host-evidence.tar.gz','r:gz') as archive:
        for member in archive.getmembers():
            assert member.name in manifest and member.name not in seen,member.name
            expected=manifest[member.name]
            assert member.mode==expected['mode'],member.name
            if expected['kind']=='symlink':
                assert member.issym() and member.linkname==expected['target'],member.name
            else:
                assert member.isfile(),member.name
                data=archive.extractfile(member).read()
                assert len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256'],member.name
            seen.add(member.name)
    assert seen==set(manifest)
    controls=read(HERE/'independent-controls.json')['controls']+read(HERE/'supplemental-controls.json')['controls']
    for result in controls:
        assert manifest[result['path']]['sha256']==result['sha256'],result['name']
    return len(manifest)


def sealed_paths():
    return [DOC,*[p for p in sorted(HERE.rglob('*')) if p.is_file() and p!=SEAL and p.name not in OPERATIONAL]]


def seal():
    assert not SEAL.exists(),'Never overwrite a sealed review'
    count=verify_inputs();verify_execution()
    scratch=HERE/'host-scratch'
    assert scratch==ROOT/'verification/apple-toggle-keyboard-focus-v9-independent-review/host-scratch'
    assert scratch.resolve()==scratch and scratch.is_dir() and not scratch.is_symlink()
    manifest={}
    with tarfile.open(HERE/'host-evidence.tar.gz','w:gz') as archive:
        for path in sorted(scratch.rglob('*')):
            name=str(path.relative_to(HERE));member=archive.gettarinfo(str(path),arcname=name)
            if path.is_symlink():
                manifest[name]=dict(kind='symlink',mode=member.mode,target=str(path.readlink()))
                archive.addfile(member)
            elif path.is_file():
                data=path.read_bytes()
                manifest[name]=dict(kind='file',mode=member.mode,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
                member.type=tarfile.REGTYPE;member.linkname='';member.size=len(data)
                archive.addfile(member,io.BytesIO(data))
            else:
                assert path.is_dir(),str(path)
    write(HERE/'host-evidence-manifest.json',manifest)
    assert verify_archive()==len(manifest)
    shutil.rmtree(scratch)
    write(HERE/'review-cleanup.json',dict(syntheticWorkingTreeArchived=True,archive='host-evidence.tar.gz',
        manifest='host-evidence-manifest.json',archivedEntries=len(manifest),
        archivedRegularFileBytes=sum(x.get('bytes',0) for x in manifest.values()),
        archiveByteLinkAndModeVerifiedBeforeRemoval=True,workingTreeAbsent=not scratch.exists(),
        loopbackClientsServersAndThreadsClosed=True,actualHTTPRequests=1546,
        loopbackCleanupMethod='Per-request finally: close client, join handle_request thread <=3 seconds, close server; fail if thread remains alive.',
        nativeInstanceCreated=False,nativeInstanceQueried=False,
        otherProjectProcessesOrDataTouched=False,
        scope='Only this exact owned synthetic host-scratch tree removed after verification.'))
    paths=sealed_paths();assert all(not p.is_symlink() for p in paths)
    files={str(p.relative_to(ROOT)):sha(p) for p in paths}
    decision=read(HERE/'review-decision.json')
    result=dict(**decision,observedUTC=datetime.datetime.now(datetime.UTC).isoformat(),
        command=[sys.executable,'-B',str(HERE/'seal_review.py'),'seal'],pythonVersion=sys.version,
        pythonExecutableSHA256=sha(pathlib.Path(sys.executable)),fileCount=len(files),files=files,
        inputFileCount=count,syntheticEvidenceEntriesArchived=len(manifest),
        unsealedOperationalOutputs=sorted(OPERATIONAL),unsealedOperationalOutputsAuthorizeNoQualification=True)
    write(SEAL,result)
    return check()


def check():
    seal=read(SEAL)
    assert seal['fileCount']==len(seal['files'])
    for name,expected in seal['files'].items():
        path=ROOT/name
        assert path.is_file() and not path.is_symlink() and sha(path)==expected,name
    assert {str(p.relative_to(ROOT)) for p in sealed_paths()}==set(seal['files']),'Unsealed extra/missing artifact'
    assert verify_inputs()==seal['inputFileCount']
    verify_execution()
    assert verify_archive()==seal['syntheticEvidenceEntriesArchived']
    assert not (HERE/'host-scratch').exists()
    return dict(status=seal['status'],sealSHA256=sha(SEAL),filesVerified=seal['fileCount'],
        inputsVerified=seal['inputFileCount'],archivedEvidenceEntriesVerified=seal['syntheticEvidenceEntriesArchived'],
        independentControls=72,actualHTTPRequests=1546,strictPersistenceContractSatisfied=True,
        nativeSelectionAccepted=False,nativeExecuted=False,gaAccepted=False)


if __name__=='__main__':
    action=sys.argv[1] if len(sys.argv)>1 else 'check'
    assert action in ['seal','check']
    print(json.dumps(seal() if action=='seal' else check(),sort_keys=True))
