#!/usr/bin/env python3
from pathlib import Path
import datetime,gzip,hashlib,json,os,shutil,subprocess,sys
H=Path(__file__).resolve().parent;S=H/'owned-scratch'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
assert S.is_dir() and not S.is_symlink() and S.resolve()==S
inode=S.stat().st_ino
receipts=[json.loads(p.read_text()) for p in sorted((H/'commands').glob('*/receipt.json'))]
assert len(receipts)==len(list((H/'commands').glob('*/started.json')))
assert all(r['ownedGroupAbsent'] and all(r['streamEOF'].values()) for r in receipts)
groups={r['processGroup'] for r in receipts}
ps=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,comm='],text=True)
active=[line for line in ps.splitlines() if len(line.split())>=2 and int(line.split()[1]) in groups]
assert not active,active
lsof=Path('/usr/sbin/lsof')
def holders():
 p=subprocess.run([str(lsof),'-nP','+D',str(S)],capture_output=True,text=True)
 assert p.returncode in (0,1)
 assert p.returncode==1 and not p.stdout.strip(),p.stdout
 return {'argv':[str(lsof),'-nP','+D',str(S)],'exitCode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
before=holders()
archives=[];(H/'bin').mkdir(exist_ok=True)
for label in ('qualified-finite-debug','qualified-finite-release','qualified-baseline-frozen'):
 r=json.loads((H/'commands'/label/'receipt.json').read_text())
 binaries=r['executedBinaryIdentities'];assert len(binaries)==1
 b=binaries[0];p=Path(b['path']);assert sha(p)==b['sha256']
 target=H/'bin'/(label+'.gz')
 with p.open('rb') as src,target.open('wb') as dst:
  with gzip.GzipFile(filename='',mode='wb',fileobj=dst,mtime=0) as out:shutil.copyfileobj(src,out)
 assert hashlib.sha256(gzip.decompress(target.read_bytes())).hexdigest()==b['sha256']
 archives.append({'archive':str(target.relative_to(H)),'archiveBytes':target.stat().st_size,'archiveSHA256':sha(target),'original':b})
after=holders();assert S.stat().st_ino==inode
files=[p for p in S.rglob('*') if p.is_file() and not p.is_symlink()]
bytes_=sum(p.stat().st_size for p in files)
shutil.rmtree(S)
save(H/'cleanup.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'owned-scratch only','path':str(S),'inode':inode,'processGroupsChecked':sorted(groups),'ownedGroupsAbsent':True,'holdersBeforeArchive':before,'holdersImmediatelyBeforeRemoval':after,'logicalFileBytesRemoved':bytes_,'filesRemoved':len(files),'scratchAbsent':not S.exists(),'binaryArchives':archives,'otherProjectsTouched':False,'lsofSHA256':sha(lsof),'pythonExecutable':sys.executable,'pythonSHA256':sha(Path(sys.executable))})
print(json.dumps({'scratchAbsent':not S.exists(),'bytesRemoved':bytes_,'archives':len(archives),'groups':len(groups)}))
