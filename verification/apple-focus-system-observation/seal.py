#!/usr/bin/env python3
"""Seal only this lane's two documents and owned source/host artifacts."""
import datetime,gzip,hashlib,io,json,pathlib,shutil,stat,tarfile
H=pathlib.Path(__file__).resolve().parent
ROOT=H.parents[1]
DOCS=[ROOT/'docs/apple-focus-system-observation-contract.md',ROOT/'docs/apple-focus-system-observation.md']
sha=lambda b:hashlib.sha256(b).hexdigest()
def stable(v):return (json.dumps(v,indent=2,sort_keys=True)+'\n').encode()
report=json.loads((H/'host-validation-1/stdout.json').read_bytes());assert report['passed'] and report['hostTests']==26
assert json.loads((H/'host-validation-1/receipt.json').read_bytes())['exitCode']==0
assert not (H/'.owned-typecheck').exists()
removed=[]
for p in H.rglob('__pycache__'):
 removed.append(str(p.relative_to(H)));shutil.rmtree(p)
cleanup={'schema':1,'compilerScratchAbsent':not (H/'.owned-typecheck').exists(),'removedOwnedPythonCaches':removed,'ownedPythonCachesAbsent':not list(H.rglob('__pycache__')),'allRecordedCompilerCommandsExited':True,'nativeAttempts':0,'nativeQueries':0,'ownedNativeInstancesCreated':0,'otherProjectProcessesOrDataTouched':False,'scope':'Owned host/compiler scratch only; no fresh native inventory or cleanup claim'}
(H/'cleanup.json').write_bytes(stable(cleanup))
files=sorted(p for p in (H/'candidate').rglob('*') if p.is_file());assert len(files)==40
members={}
archive=io.BytesIO()
with gzip.GzipFile(fileobj=archive,mode='wb',mtime=0) as gz:
 with tarfile.open(fileobj=gz,mode='w') as t:
  for p in files:
   raw=p.read_bytes();name=str(p.relative_to(H/'candidate'));info=tarfile.TarInfo(name);info.size=len(raw);info.mode=0o444;info.uid=info.gid=0;info.mtime=0
   t.addfile(info,io.BytesIO(raw));members[name]={'bytes':len(raw),'sha256':sha(raw),'mode':0o444}
(H/'review-source-package.tar.gz').write_bytes(archive.getvalue())
(H/'review-source-package-manifest.json').write_bytes(stable({'schema':1,'archiveSHA256':sha(archive.getvalue()),'members':members,'memberTreeSHA256':sha(stable(members)),'membersCount':40,'changedMembers':report['changedMembers']}))
(H/'receipt.json').write_bytes(stable({'schema':1,'status':'source-host-complete-pending-independent-review','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':report['scope'],'sourceRevisionLabelFromAcceptedFrozenReview':'4a28261b333c28b4fce386f370a19b93e735c8d2','originalArchiveSHA256':'96cf2e6d4356035e004564a2a4d4e01122fb570835e4089c6c83788ab53465f8','resultReviewHandoffSHA256':'4c51a382173b38962cf031db0f19c82b076756fc51195092b29674e9f7a5ee48','candidateTreeSHA256':report['candidateTreeSHA256'],'sourceReviewArchiveSHA256':sha(archive.getvalue()),'hostTests':26,'typecheck':'full-accepted-and-modified-Prototype-plus-exact-unchanged4harness','changedSourceMembers':report['changedMembers'],'originalOraclePassed':False,'originalFailingPredicates':['actualNativeFocusTraversal'],'settingsPreviouslyPassed':True,'nativeAttempts':0,'nativeQueries':0,'nativeAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred','next':'Independent source review; native packet/build/runtime not selected'}))
paths=sorted([p for p in H.rglob('*') if p.is_file() and p.name not in ['handoff.json','handoff.sha256']]+DOCS)
rows={}
for p in paths:
 assert not p.is_symlink();p.chmod(0o444);raw=p.read_bytes();rows[str(p.relative_to(ROOT))]={'bytes':len(raw),'sha256':sha(raw),'mode':0o444}
handoff={'schema':1,'scope':'Bounded read-only UIKit focus-system supplemental source and host derivative; pending independent source review','members':rows,'memberTreeSHA256':sha(stable(rows)),'nativeAttempts':0,'nativeQueries':0,'nativeAccepted':False,'gaAccepted':False,'originalOraclePassed':False,'originalOracleUnchanged':True,'physicalPhones':'disconnected-deferred'}
raw=stable(handoff);(H/'handoff.json').write_bytes(raw);(H/'handoff.sha256').write_text(sha(raw)+'\n')
(H/'handoff.json').chmod(0o444);(H/'handoff.sha256').chmod(0o444)
for p in sorted([p for p in H.rglob('*') if p.is_dir()],key=lambda p:len(p.parts),reverse=True):p.chmod(0o555)
H.chmod(0o555)
print(json.dumps({'members':len(rows),'handoffSHA256':sha(raw),'sourceReviewArchiveSHA256':sha(archive.getvalue()),'scope':'Sealed isolated source/host result; no native acceptance'},sort_keys=True))
