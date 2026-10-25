#!/usr/bin/env python3
"""Archive final binaries; remove only owned scratch after group/holder/inode checks."""
from pathlib import Path
import datetime,gzip,hashlib,json,os,shutil,stat,subprocess
H=Path(__file__).resolve().parent;S=H/'owned-scratch'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
receipts=[json.loads(p.read_text()) for p in (H/'commands').glob('*/receipt.json')]
groups=sorted({r['pgid'] for r in receipts})
pscmd=['/bin/ps','-axo','pid=,pgid=,comm='];ps=subprocess.run(pscmd,capture_output=True,text=True,check=True)
(H/'cleanup-ps.stdout').write_text(ps.stdout);(H/'cleanup-ps.stderr').write_text(ps.stderr)
members=[x for x in ps.stdout.splitlines() if len(x.split())>=2 and int(x.split()[1]) in groups];assert not members
assert S.is_dir() and not S.is_symlink();before=S.stat();assert stat.S_ISDIR(before.st_mode)
archives=[]
for lane,profile in [('baseline','debug'),('candidate','debug'),('candidate','release')]:
    candidates=[p for p in (S/lane/profile/'deps').iterdir() if p.is_file() and p.name.startswith('mixer_vm-') and '.' not in p.name and os.access(p,os.X_OK)]
    assert len(candidates)==1,candidates;b=candidates[0]
    identified=[v for r in receipts for v in r['binaries'] if v['path']==str(b) and v['sha256']==sha(b)];assert identified
    out=H/'executables'/(lane+'-'+profile+'.gz');out.parent.mkdir(exist_ok=True)
    raw=b.read_bytes();out.write_bytes(gzip.compress(raw,compresslevel=9,mtime=0))
    assert gzip.decompress(out.read_bytes())==raw
    archives.append({'archive':str(out.relative_to(H)),'archiveSHA256':sha(out),'original':identified[0],'mode':oct(stat.S_IMODE(b.stat().st_mode))})
lsofcmd=['/usr/sbin/lsof','-nP','+D',str(S)];lsof=subprocess.run(lsofcmd,capture_output=True,text=True)
(H/'cleanup-lsof.stdout').write_text(lsof.stdout);(H/'cleanup-lsof.stderr').write_text(lsof.stderr)
assert lsof.returncode in [0,1] and not lsof.stdout.strip() and not lsof.stderr.strip(),(lsof.returncode,lsof.stdout,lsof.stderr)
ps2=subprocess.run(pscmd,capture_output=True,text=True,check=True)
(H/'cleanup-final-ps.stdout').write_text(ps2.stdout)
assert not [x for x in ps2.stdout.splitlines() if len(x.split())>=2 and int(x.split()[1]) in groups]
after=S.stat();assert (before.st_dev,before.st_ino)==(after.st_dev,after.st_ino)
shutil.rmtree(S)
save(H/'cleanup.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ownedScratch':str(S),'scratchDevice':before.st_dev,'scratchInode':before.st_ino,'inodeStableImmediatelyBeforeRemoval':True,'processGroupsChecked':groups,'ownedGroupsAbsent':True,'psArgv':pscmd,'lsofArgv':lsofcmd,'lsofExitCode':lsof.returncode,'holdersEmpty':True,'holderStdoutSHA256':sha(H/'cleanup-lsof.stdout'),'holderStderrSHA256':sha(H/'cleanup-lsof.stderr'),'scratchAbsent':not S.exists(),'binaryArchives':archives,'onlyOwnedScratchRemoved':True,'sourceCopiesAndAllFailedEvidenceRetained':True})
print(json.dumps({'scratchAbsent':not S.exists(),'groups':len(groups),'archives':len(archives),'holdersEmpty':True},sort_keys=True))
