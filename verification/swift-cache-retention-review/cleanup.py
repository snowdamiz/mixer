#!/usr/bin/env python3
"""Retire only this review's checked owned scratch, without signals."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,stat,subprocess,sys
H=Path(__file__).resolve().parent
name=sys.argv[1] if len(sys.argv)>1 else 'cleanup'
assert name.replace('-','_').isidentifier()
write=lambda p,d:p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
paths=[H/n for n in ['owned-source','owned-target','owned-tmp']]
assert all(p.parent==H and p.is_dir() and not p.is_symlink() for p in paths)
rows=[]
for root in paths:
    for p in [root,*sorted(root.rglob('*'))]:
        s=p.lstat();assert s.st_dev==root.stat().st_dev and not stat.S_ISLNK(s.st_mode)
        assert stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode)
        rows.append({'path':str(p.relative_to(H)),'dev':s.st_dev,'ino':s.st_ino,'mode':s.st_mode,'bytes':s.st_size,'mtimeNS':s.st_mtime_ns})
processes=subprocess.check_output(['ps','-axo','pid=,command='],text=True)
owned=[line for line in processes.splitlines() if any(str(p) in line for p in paths)]
assert not owned,owned
holders=[]
for p in paths:
    r=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(p)],capture_output=True,text=True)
    holders.append({'argv':['/usr/sbin/lsof','-nP','+D',str(p)],'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
    assert r.returncode==1 and not r.stdout and not r.stderr,holders[-1]
write(H/(name+'-preflight.json'),{'schema':1,'inventory':rows,'ownedProcessMatches':owned,'holders':holders})
for row in rows:
    s=(H/row['path']).lstat()
    assert (s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns)==(row['dev'],row['ino'],row['mode'],row['bytes'],row['mtimeNS'])
for p in paths:shutil.rmtree(p)
assert all(not p.exists() for p in paths)
regular=[r for r in rows if stat.S_ISREG(r['mode'])]
write(H/(name+'.json'),{'schema':1,'completedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ownedProcessesAbsent':True,'holdersAbsent':True,'deviceInodeAndMutationChecksPassed':True,'removed':[str(p) for p in paths],'removedLogicalBytes':sum(r['bytes']for r in regular),'removedRegularFiles':len(regular),'signalsSent':0,'producerArchivesPreserved':True,'scope':'Only review-owned extracted source, Cargo target and temporary directories; no producer mutation, live VM, native, UI, device or network use.'})
print((H/(name+'.json')).read_text())
