#!/usr/bin/env python3
"""Bind the integrated UI checkpoint to final independent and owner evidence."""
import hashlib, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
specs=[
 ('verification/guest-ui-sdk/2026-10-23-candidate-4/receipt.json','f336e0a822579af8b8e24a08a62323583d4d633051321107430a177adbb60f5b','source_files'),
 ('verification/guest-ui-native-package/2026-10-23-native-2/receipt.json','6e6c64ce24406fccc6842b3a9437557d4f045bbeaab3cb6e2f63dd18cd0a6eaa','source_files'),
 ('verification/guest-ui-native-package/2026-10-23-binding-audit-1/receipt.json','f20392c3f75c28e7961740713227d7efd4d5b7011fef41c9b73c525e0255621f',None),
 ('verification/guest-ui-bridge/2026-10-23-sdk4-native2/receipt.json','06c043e133310c938c0097ab077a92c8c7342166c54c223b1bc1de06519316a8','source'),
 ('verification/guest-ui-exchange-review/receipt.json','1ba35f401f11bab297a448f58bae720320675868cdeda74ec2118d7c67044ed9',None),
 ('verification/guest-ui-presentation/2026-10-23-candidate-6/receipt.json','279d851489001aa060e06ee2b8da38962b78537d676f7d2b4ebe97cc6fcf605d','source_files'),
 ('verification/guest-ui-activation/candidate-4/receipt.json','14531af2ee4d0b9b9d47f129d963e6df797be772da5b735122c36db4666c0970','source_files'),
 ('verification/guest-ui-activation/supplemental-1/receipt.json','f8493375e64118f25bee898e195ae75b59ab22f54fcb9e80cdc8854bec360e42','source_files'),
 ('verification/guest-ui-activation-review/final-receipt.json','5d0c0a0d2e4e457184daab3ed5ac551410f319e85408c16807ef238b4b040c98','source_files')]
checks=[];evidence={};production={}
def verify(path,digest,kind):
 assert path.is_file(),str(path)
 actual=sha(path);assert actual==digest,(str(path),actual,digest)
 checks.append({'path':str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),'sha256':actual,'kind':kind})
for name,digest,key in specs:
 path=ROOT/name;verify(path,digest,'sealed receipt');r=json.loads(path.read_text());evidence[name]={'sha256':digest,'status':r.get('status')}
 if key:
  for source,expected in r[key].items():
   verify(ROOT/source,expected,'current tested source');production[source]=expected
 for command in r.get('commands',[]):
  name=command.get('log');expected=command.get('log_sha256') or command.get('logSHA256') or command.get('sha256')
  if name and expected:
   p=Path(name)
   if not p.is_absolute():p=(ROOT/p) if (ROOT/p).is_file() else path.parent/p
   verify(p,expected,'command output')
 for field in ['nativeArtifacts','borrowed_files','inputs']:
  for name,expected in r.get(field,{}).items():
   if isinstance(expected,str):verify(ROOT/name,expected,'qualified dependency')
 for record in r.get('evidence',{}).values():
  if isinstance(record,dict) and 'path' in record and 'sha256' in record:verify(ROOT/record['path'],record['sha256'],'independent evidence binding')
activation=json.loads((ROOT/'verification/guest-ui-activation/candidate-4/receipt.json').read_text())
assert not activation['working_tree_changes_after_snapshot']
for mode,artifacts in activation['artifacts'].items():
 assert artifacts['tests']==113
 for name in ['dylib','bundle_binary']:verify(Path(artifacts[name]['path']),artifacts[name]['sha256'],mode+' integrated artifact')
record={'status':'final source and evidence bindings passed','head_before_checkpoint':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'driver_sha256':sha(Path(__file__)),'evidence':evidence,'current_source_files':production,'verified_bindings':len(checks),'checks':checks,'findings_resolved':['Unicode canonical-equivalence substitution rejected before presentation authority','Unseen or changed terminal event result preserved for final matching presentation claim','Model retires visual/input authority immediately but preserves final terminal result through actual consumer return','Post-intent UI failure publishes requiresReopen after durable reconciliation'],'scope':'Bounded UI SDK, fixed native bridge, explicit signed Apple UI facade, exact native package, 113 integration tests per host mode, 48 bridge tests per mode, independent exchange/bridge/activation probes, public API privacy and full official iOS/Android module compilation. Existing capability-only facade remains separate.','pending':['Visible native screen/display-cycle and actual native user click qualification','iOS simulator and physical lifecycle/accessibility/performance','Android bound signed guest UI facade and native presentation','Full Swift guest execution and artifact budget','Immutable published consumer/FieldLog, operational and GA gates']}
out=ROOT/'verification/guest-ui-integration-root-review.json';out.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'receipt':str(out),'sha256':sha(out),'bindings':len(checks)}))
