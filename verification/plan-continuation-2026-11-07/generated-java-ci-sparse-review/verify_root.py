#!/usr/bin/env python3
"""Read-only prepared workflow review; writes only this review namespace."""
from pathlib import Path
import hashlib,json,subprocess
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
STAGED=HERE.parent/'generated-java-ci-root-integration'
OLD=ROOT/'.github/workflows/verify.yml'
NEW=STAGED/'verify.proposed.yml'
FRAGMENT=HERE.parent/'generated-java-ci-integration/workflow-proposal.yml'
def require(ok,msg):
 if not ok: raise RuntimeError(msg)
def identity(p):
 b=p.read_bytes(); return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
expected={OLD:'5cc067d90adaadbb4741e8e0e25bf1ecace4fa2d5ce87cbe13cfddb92fc67325',NEW:'38292821070d24d4c8c13ad28c6abc08e532eaa65a56c020a18b0f1b04131a64',FRAGMENT:'6b3d18ff334833a807de7af3a4f468caa1a751b349cd82a53414b10ab134a364'}
pins={str(p.relative_to(ROOT)):identity(p) for p in expected}
for p,sha in expected.items(): require(identity(p)['sha256']==sha,'Workflow hash changed '+str(p))
fragment=b''.join(FRAGMENT.read_bytes().splitlines(keepends=True)[2:])
require(NEW.read_bytes()==OLD.read_bytes()+fragment,'Prepared workflow is not exact old bytes plus reviewed job')
prep=json.loads((STAGED/'preparation.json').read_text())
require(prep['state']=='PREPARED_NOT_INSTALLED' and prep['status']=='PASS' and prep['terminalCustody'] is True,'Preparation record differs')
for command in prep['commands']:
 require(command['exit_code']==0 and command['terminal_custody'] is True,'Preparation command unsuccessful')
 for data in command['logs'].values():
  p=Path(data['path']); require(p.is_relative_to(STAGED),'Preparation log outside namespace')
  require(identity(p)=={k:data[k] for k in ('bytes','sha256')},'Preparation log hash drift')
commands=[]
for label,argv in [('ruby-version',['/usr/bin/ruby','--version']),('full-workflow-equality',['/usr/bin/ruby',str(HERE/'verify_workflow.rb'),str(OLD),str(NEW),str(FRAGMENT)])]:
 r=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=15)
 for stream,data in [('stdout',r.stdout),('stderr',r.stderr)]: (HERE/(label+'.'+stream)).write_bytes(data)
 commands.append({'argv':argv,'cwd':str(ROOT),'timeout_seconds':15,'exit_code':r.returncode,'stdout':identity(HERE/(label+'.stdout')),'stderr':identity(HERE/(label+'.stderr'))})
 require(r.returncode==0,'Parser failed '+label)
parsed=json.loads((HERE/'full-workflow-equality.stdout').read_text())
for p,sha in expected.items(): require(identity(p)['sha256']==sha,'Workflow drift during review')
receipt={'observed_utc':datetime.now(timezone.utc).isoformat(),'status':'ACCEPT_PREPARED_WORKFLOW','source_revision':prep['sourceRevision'],'pins':pins,'preparation_receipt':identity(STAGED/'preparation.json'),'preparation_logs_match_receipt':True,'producer_custody':'Positive terminal custody recorded in preparation; no processes probed by reviewer','exact_original_bytes_plus_reviewed_job':True,'yaml_equality':parsed,'commands':commands,'scope':'Read-only proposal inspection and YAML parsing; canonical workflow untouched; no dispatch or compiler execution'}
(HERE/'root-integration-review.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'exact_original_bytes_plus_reviewed_job':True,'yaml_equality':parsed}))
