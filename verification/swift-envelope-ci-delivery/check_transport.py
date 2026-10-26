import datetime, hashlib, json, subprocess, sys, tempfile
from pathlib import Path
from evidence_transport import canonical, verify, digest
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
result={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python_version':sys.version,'scope':'Root evidence transport only; no archive member executed','commands':[]}
with tempfile.TemporaryDirectory(prefix='mixer-envelope-evidence-recovery-',dir='/private/tmp') as temporary:
 base=Path(temporary); result['owned_scratch']=str(base); result['owned_identity']=[base.stat().st_dev,base.stat().st_ino,base.stat().st_uid]
 argv=[sys.executable,'-B',str(OUT/'evidence_transport.py'),'--archive',str(OUT/'producer-evidence.tar.gz'),'--manifest',str(OUT/'producer-evidence-manifest.json'),'--out',str(base/'recovered')]
 completed=subprocess.run(argv,capture_output=True,timeout=60)
 (OUT/'recovery.stdout').write_bytes(completed.stdout); (OUT/'recovery.stderr').write_bytes(completed.stderr)
 result['commands'].append({'argv':argv,'exit':completed.returncode,'child_returned':True,'stdout_sha256':hashlib.sha256(completed.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(completed.stderr).hexdigest()}); completed.check_returncode()
 result['recovery']=json.loads(completed.stdout)
 bad=['.','../foo','/foo','a//b','a/./b','a\\b','a/../b','.git/config']
 for name in bad:
  try: canonical(name)
  except ValueError: pass
  else: raise RuntimeError('Accepted badpath '+name)
 canonical('verification/example/receipt.json')
 result['canonical_rejections']=len(bad)
 try: verify(OUT/'producer-evidence.tar.gz',OUT/'producer-evidence-manifest.json',base/'recovered')
 except ValueError as error:
  if str(error)!='Recovery requires a new destination outside Git metadata': raise
 else: raise RuntimeError('Existing recovery accepted')
 value=json.loads((OUT/'producer-evidence-manifest.json').read_bytes());value['archive_sha256']='0'*64;(base/'changed-manifest.json').write_text(json.dumps(value))
 try: verify(OUT/'producer-evidence.tar.gz',base/'changed-manifest.json')
 except ValueError as error:
  if str(error)!='Archive identity differs': raise
 else: raise RuntimeError('Changed archive identity accepted')
 result['existing_destination_refused']=result['archive_identity_mismatch_refused']=True
result['owned_scratch_removed']=not Path(result['owned_scratch']).exists();result['members_executed']=False
result['tools']={p.name:digest(p) for p in [Path(__file__),OUT/'build_transport.py',OUT/'evidence_transport.py']}
(OUT/'transport-checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['commands','tools','owned_scratch','owned_identity']},indent=2))
