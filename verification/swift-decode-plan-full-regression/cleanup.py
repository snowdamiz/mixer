#!/usr/bin/env python3
"""Retain reproducible source and final executables; remove owned targets only."""
from pathlib import Path
import datetime, gzip, hashlib, io, json, os, shutil, stat, subprocess, tarfile
H=Path(__file__).resolve().parent;S=H/'owned-scratch'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
receipts=[json.loads(p.read_text()) for p in (H/'commands').glob('*/receipt.json')]
groups=sorted({r['pgid'] for r in receipts})
pscmd=['/bin/ps','-axo','pid=,pgid=,comm=']
ps=subprocess.run(pscmd,capture_output=True,text=True,check=True,timeout=30)
(H/'cleanup-ps.stdout').write_text(ps.stdout);(H/'cleanup-ps.stderr').write_text(ps.stderr)
assert not [x for x in ps.stdout.splitlines() if len(x.split())>=2 and int(x.split()[1]) in groups]
assert S.is_dir() and not S.is_symlink();before=S.stat();assert stat.S_ISDIR(before.st_mode)
F=H/'executables';F.mkdir(exist_ok=True);archives=[];byhash={}
labels=['final-swift-debug','final-swift-release','corrected-full-debug','corrected-full-release']
for label in labels:
    r=json.loads((H/'commands'/label/'receipt.json').read_text());assert r['qualifyingPass']
    bins=r['binaries'][:]
    context=r['context'];profile='release' if context.endswith('release') else 'debug'
    cli=S/context/profile/'mixer-vm'
    if cli.is_file():bins.append({'path':str(cli),'sha256':sha(cli),'bytes':cli.stat().st_size,'role':'regular CLI used by integration tests'})
    for b in bins:
        p=Path(b['path']);assert p.is_relative_to(S) and not p.is_symlink() and sha(p)==b['sha256']
        digest=b['sha256'];out=F/(digest+'.gz')
        if digest not in byhash:
            raw=p.read_bytes();out.write_bytes(gzip.compress(raw,compresslevel=9,mtime=0))
            assert gzip.decompress(out.read_bytes())==raw
            byhash[digest]={'archive':str(out.relative_to(H)),'archiveSHA256':sha(out),'uncompressedSHA256':digest,'uncompressedBytes':len(raw),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
        archives.append({'command':label,'original':b,'archive':byhash[digest]['archive']})
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w',format=tarfile.PAX_FORMAT) as archive:
    for p in sorted((H/'source').rglob('*')):
        if not p.is_file():continue
        data=p.read_bytes();member=tarfile.TarInfo('source/'+str(p.relative_to(H/'source')))
        member.size=len(data);member.mode=0o644;member.mtime=0;member.uid=member.gid=0;member.uname=member.gname=''
        archive.addfile(member,io.BytesIO(data))
sourcearc=H/'final-source.tar.gz';sourcearc.write_bytes(gzip.compress(buffer.getvalue(),compresslevel=9,mtime=0))
with tarfile.open(sourcearc,'r:gz') as archive:
    m=json.loads((H/'final-source-manifest.json').read_text())
    assert len(archive.getmembers())==len(m)==132
    for member in archive.getmembers():
        assert hashlib.sha256(archive.extractfile(member).read()).hexdigest()==m[member.name.removeprefix('source/')]
lsofcmd=['/usr/sbin/lsof','-nP','+D',str(S)]
lsof=subprocess.run(lsofcmd,capture_output=True,text=True,timeout=60)
(H/'cleanup-lsof.stdout').write_text(lsof.stdout);(H/'cleanup-lsof.stderr').write_text(lsof.stderr)
assert lsof.returncode in (0,1) and not lsof.stdout.strip() and not lsof.stderr.strip(),(lsof.returncode,lsof.stdout,lsof.stderr)
ps2=subprocess.run(pscmd,capture_output=True,text=True,check=True,timeout=30)
(H/'cleanup-final-ps.stdout').write_text(ps2.stdout)
assert not [x for x in ps2.stdout.splitlines() if len(x.split())>=2 and int(x.split()[1]) in groups]
after=S.stat();assert (before.st_dev,before.st_ino)==(after.st_dev,after.st_ino)
shutil.rmtree(S)
save(H/'cleanup.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ownedScratch':str(S),'scratchDevice':before.st_dev,'scratchInode':before.st_ino,'inodeStableImmediatelyBeforeRemoval':True,'processGroupsChecked':groups,'ownedGroupsAbsent':True,'psArgv':pscmd,'lsofArgv':lsofcmd,'lsofExitCode':lsof.returncode,'holdersEmpty':True,'scratchAbsent':not S.exists(),'binaryArchives':list(byhash.values()),'commandBinaryBindings':archives,'sourceArchive':{'path':'final-source.tar.gz','sha256':sha(sourcearc),'members':132},'onlyOwnedScratchRemoved':True,'otherProjectsProcessesAndDataPreserved':True,'sourceObjectsAndAllFailuresRetained':True})
print(json.dumps({'scratchAbsent':not S.exists(),'groups':len(groups),'binaryBindings':len(archives),'uniqueBinaryArchives':len(byhash),'sourceMembers':132,'holdersEmpty':True},sort_keys=True))
