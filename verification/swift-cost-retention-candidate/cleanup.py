#!/usr/bin/env python3
"""Retire only this packet's scratch, after source archives and holder checks."""
import hashlib,json,os,pathlib,shutil,stat,subprocess,time
OUT=pathlib.Path(__file__).resolve().parent
SCRATCH=OUT/'.scratch'
def sha(data):return hashlib.sha256(data).hexdigest()
def write(path,obj):path.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
assert SCRATCH.parent==OUT and SCRATCH.name=='.scratch' and SCRATCH.is_dir() and not SCRATCH.is_symlink()
seal=json.loads((OUT/'source-seals.json').read_text())
for label in ['live-baseline','baseline','candidate']:
 assert sha((OUT/f'{label}-source.tar.gz').read_bytes())==seal[label]['archiveSHA256']
 assert sha((OUT/f'{label}-source-manifest.json').read_bytes())==seal[label]['manifestSHA256']
def check_live():
 ps=subprocess.run(['/bin/ps','-axo','pid=,ppid=,pgid=,command='],capture_output=True,text=True,check=True)
 matches=[line for line in ps.stdout.splitlines() if str(SCRATCH) in line]
 holders=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(SCRATCH)],capture_output=True,text=True)
 assert not matches,matches
 assert holders.returncode in [0,1] and not holders.stdout and not holders.stderr,(holders.returncode,holders.stdout,holders.stderr)
 return {'processMatches':matches,'holderArgv':['/usr/sbin/lsof','-nP','+D',str(SCRATCH)],'holderExit':holders.returncode,'holderStdout':holders.stdout,'holderStderr':holders.stderr}
def inventory():
 rows=[]
 for path in sorted(SCRATCH.rglob('*')):
  st=path.lstat(); assert not stat.S_ISLNK(st.st_mode),str(path)
  assert stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode),str(path)
  rows.append({'path':str(path.relative_to(SCRATCH)),'device':st.st_dev,'inode':st.st_ino,'mode':st.st_mode,'bytes':st.st_size,'mtimeNs':st.st_mtime_ns,'directory':stat.S_ISDIR(st.st_mode)})
 root=SCRATCH.stat()
 return {'root':{'device':root.st_dev,'inode':root.st_ino,'mtimeNs':root.st_mtime_ns},'entries':rows}
first=check_live();before=inventory();second=check_live();assert before==inventory(),'scratch mutation or identity change before retirement'
write(OUT/'cleanup-preflight.json',{'sourceArchivesVerified':True,'first':first,'second':second,'inventory':before})
rows=before['entries'];regular=[r for r in rows if not r['directory']]
shutil.rmtree(SCRATCH)
write(OUT/'cleanup.json',{'scope':str(SCRATCH),'removed':not SCRATCH.exists(),'regularFiles':len(regular),'logicalBytes':sum(r['bytes'] for r in regular),'directories':len(rows)-len(regular)+1,'signalsSent':[],'holderChecks':2,'identityAndMutationCheck':True,'preserved':'all source archives, manifests, scripts, command outputs and nonowned paths'})
print(json.dumps({'removed':True,'regularFiles':len(regular),'logicalBytes':sum(r['bytes'] for r in regular)}))
