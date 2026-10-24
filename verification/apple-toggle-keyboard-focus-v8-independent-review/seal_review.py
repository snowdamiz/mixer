"""Seal or read-only verify this failing independent review; no native operations."""
import datetime
import hashlib
import io
import json
import pathlib
import shutil
import sys
import tarfile

HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];DOC=ROOT/'docs/apple-toggle-keyboard-focus-v8-independent-review.md';SEAL=HERE/'review-seal.json'
OPERATIONAL={'seal-command.stdout','seal-command.stderr','seal-command.json','check-command.stdout','check-command.stderr','check-command.json'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
write=lambda p,v:p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')


def verify_inputs():
    inputs=read(HERE/'review-inputs.json');links={x['path']:x for x in read(HERE/'tool-link-bindings.json')}
    for name,expected in inputs.items():
        path=pathlib.Path(name) if name.startswith('/') else ROOT/name
        assert path.is_file() and sha(path)==expected,name
        if path.is_symlink():
            link=links[str(path)];assert str(path.readlink())==link['linkText'] and str(path.resolve())==link['resolved'] and sha(path)==link['sha256']
    return len(inputs)


def verify_archive():
    manifest=read(HERE/'host-evidence-manifest.json');seen=set()
    with tarfile.open(HERE/'host-evidence.tar.gz','r:gz') as archive:
        for member in archive.getmembers():
            assert member.name in manifest and member.name not in seen,member.name
            expected=manifest[member.name]
            if expected['kind']=='symlink':assert member.issym() and member.linkname==expected['target']
            else:
                assert member.isfile();data=archive.extractfile(member).read()
                assert len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256'],member.name
            seen.add(member.name)
    assert seen==set(manifest)
    return len(manifest)


def sealed_paths():
    return [DOC,*[p for p in sorted(HERE.rglob('*')) if p.is_file() and p!=SEAL and p.name not in OPERATIONAL]]


def seal():
    assert not SEAL.exists(),'Sealed review must not be overwritten'
    count=verify_inputs();scratch=HERE/'host-scratch';assert scratch.resolve()==scratch and scratch.is_dir()
    manifest={}
    with tarfile.open(HERE/'host-evidence.tar.gz','w:gz') as archive:
        for path in sorted(scratch.rglob('*')):
            name=str(path.relative_to(HERE));member=archive.gettarinfo(str(path),arcname=name)
            if path.is_symlink():
                manifest[name]=dict(kind='symlink',target=str(path.readlink()));archive.addfile(member)
            elif path.is_file():
                data=path.read_bytes();manifest[name]=dict(kind='file',bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
                member.type=tarfile.REGTYPE;member.linkname='';member.size=len(data);archive.addfile(member,io.BytesIO(data))
            else:assert path.is_dir(),str(path)
    write(HERE/'host-evidence-manifest.json',manifest);assert verify_archive()==len(manifest)
    shutil.rmtree(scratch)
    write(HERE/'review-cleanup.json',dict(syntheticWorkingTreeArchived=True,archive='host-evidence.tar.gz',manifest='host-evidence-manifest.json',archivedEntries=len(manifest),archivedRegularFileBytes=sum(x.get('bytes',0) for x in manifest.values()),workingTreeAbsent=not scratch.exists(),loopbackClientsServersAndThreadsClosed=True,loopbackCleanupMethod='Every request finally closes client, joins handle_request thread with a three-second bound, closes server, and fails if thread remains alive',nativeInstanceCreated=False,nativeInstanceQueried=False,otherProjectProcessesOrDataTouched=False,scope='Only this exact owned synthetic host-scratch tree removed after independent archive byte and link verification'))
    paths=sealed_paths();assert all(not p.is_symlink() for p in paths)
    files={str(p.relative_to(ROOT)):sha(p) for p in paths}
    decision=read(HERE/'review-decision.json')
    result=dict(**decision,observedUTC=datetime.datetime.now(datetime.UTC).isoformat(),command=[sys.executable,'-B',str(HERE/'seal_review.py'),'seal'],pythonVersion=sys.version,fileCount=len(files),files=files,inputFileCount=count,syntheticEvidenceEntriesArchived=len(manifest),unsealedOperationalOutputs=sorted(OPERATIONAL),unsealedOperationalOutputsAuthorizeNoQualification=True)
    write(SEAL,result);return check()


def check():
    seal=read(SEAL);assert seal['fileCount']==len(seal['files'])
    for name,expected in seal['files'].items():
        path=ROOT/name;assert path.is_file() and not path.is_symlink() and sha(path)==expected,name
    assert {str(p.relative_to(ROOT)) for p in sealed_paths()}==set(seal['files']),'Unsealed extra/missing artifact'
    assert verify_inputs()==seal['inputFileCount'];assert verify_archive()==seal['syntheticEvidenceEntriesArchived']
    assert not (HERE/'host-scratch').exists()
    return dict(status=seal['status'],sealSHA256=sha(SEAL),filesVerified=seal['fileCount'],inputsVerified=seal['inputFileCount'],archivedEvidenceEntriesVerified=seal['syntheticEvidenceEntriesArchived'],strictPersistenceContractSatisfied=False,nativeSelectionAccepted=False,nativeExecuted=False,gaAccepted=False)

if __name__=='__main__':
    action=sys.argv[1] if len(sys.argv)>1 else 'check';assert action in ['seal','check']
    print(json.dumps(seal() if action=='seal' else check(),sort_keys=True))
