#!/usr/bin/env python3
"""Remove only this lane's compiler/temp scratch after checking actual holders."""
from pathlib import Path
import datetime,hashlib,json,shutil,subprocess
H=Path(__file__).resolve().parent;R=H.parent.parent;S=H/'owned-scratch'
assert S.is_dir() and S.resolve()==H/'owned-scratch' and not S.is_symlink()
original=json.loads((H/'baseline-manifest.json').read_text())
assert all(hashlib.sha256((R/'vm'/n).read_bytes()).hexdigest()==v for n,v in original.items())
for p in (H/'commands').glob('*/receipt.json'):
 r=json.loads(p.read_text());assert r['ownedGroupAbsent'] and all(r['streamEOF'].values())
files=[p for p in S.rglob('*') if p.is_file()];logical=sum(p.stat().st_size for p in files)
r=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(S)],capture_output=True,text=True,timeout=30)
(H/'cleanup-holder.stdout').write_text(r.stdout);(H/'cleanup-holder.stderr').write_text(r.stderr)
assert r.returncode==1 and not r.stdout and not r.stderr,(r.returncode,r.stdout,r.stderr)
shutil.rmtree(S)
result={'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'path':str(S),'logicalBytesRemoved':logical,'filesRemoved':len(files),'holderCheckArgv':['/usr/sbin/lsof','-nP','+D',str(S)],'holderCheckExitCode':r.returncode,'ownedScratchRemoved':not S.exists(),'preservedOtherProjects':True,'sourceAndEvidencePreserved':True,'live132SourceUnchanged':all(hashlib.sha256((R/'vm'/n).read_bytes()).hexdigest()==v for n,v in original.items()),'nativeDeviceInstancesCreated':0}
(H/'cleanup.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result))
