#!/usr/bin/env python3
"""Offline exact-source custody and executed-host evidence checks; never release admission."""
from pathlib import Path
import hashlib,json,datetime
D=Path(__file__).resolve().parent;R=D.parents[1];C=D/'candidate'
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def fail(message):raise AssertionError(message)
def check(value,message):
 if not value:fail(message)
def save(p,value):p.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
profile=json.loads((C/'profile5.json').read_text());reb=R/'verification/android-editor-source-pair5-rebinding';accepted=R/'verification/android-editor-preservation-membership-correction';bindings={}
check(ident(reb/'seal.json')['sha256']=='088b6dd59bbfd91cd93e7c4cbb16ca1285018b0f6eb6045932b348f7beaf8864','exact accepted rebinding seal')
for group,base in [('sdk_files',C/'sdk'),('adapter_files',C/'native/android')]:
 result={}
 for name,expected in profile[group].items():
  target=base/name
  if group=='adapter_files' and name.startswith('Sources/'):target=base/'engine'/name
  check(ident(target)==expected,'profile member differs: '+str(target))
  original=reb/'sources'/('sdk' if group=='sdk_files' else 'adapter')/name
  check(target.read_bytes()==original.read_bytes(),'rebinding member bytes differ '+name)
  result[name]={'candidate':str(target.relative_to(C)),'accepted_rebinding_member':str(original.relative_to(reb)),**ident(target)}
 bindings[group]=result
projection=lambda rows:hashlib.sha256(''.join(name+'\0'+rows[name]['sha256']+'\n' for name in sorted(rows)).encode()).hexdigest()
check(projection(profile['sdk_files'])==profile['sdk_compatibility_sha256'],'SDK projection')
check(projection(profile['adapter_files'])==profile['adapter_compatibility_sha256'],'adapter projection')
check(ident(C/'descriptor.json')==profile['default_descriptor'],'default descriptor')
product={}
for path in sorted((accepted/'source').glob('*.java')):
 target=C/'native/android/app/src/dev/mixer/android'/path.name
 check(path.read_bytes()==target.read_bytes(),'accepted product changed '+path.name);product[path.name]=ident(path)
check(len(product)==16,'exact sixteen product source members')
roster=json.loads((C/'native/android/tests/private-owner-source-pair5-roster.json').read_text())
for name,expected in roster['selected_source_identities'].items():check(ident(C/name)==expected,'frozen roster identity differs '+name)
for key,v in roster['closures'].items():
 check(len(v['actual_production_sources'])==(11 if key.startswith('A') else 16),'expanded product closure '+key)
 check(len(v['actual_production_sources'])==len(set(v['actual_production_sources'])),'no duplicate product '+key)
check(len(roster['crosscompile']['proposed_java'])==24 and len(roster['crosscompile']['current_swift_c_h'])==76,'exact cross24/76 closure')
for name in ('jni.c','mixer_android.h','mixer_android_v2.h'):check((C/'native/android/bridge'/name).read_bytes()==(R/'native/android/bridge'/name).read_bytes(),'bridge/header unchanged '+name)
# Five V1 positives remain byte-identical at the method source level; execution is separately retained.
def method(text,name,next_name):return text.split('    private static void '+name+'(){',1)[1].split('    private static void '+next_name+'(){',1)[0]
history=(D/'historical/native/android/tests/NativeOwnerV2ConcreteHostTests.java').read_text();current=(C/'native/android/tests/NativeOwnerV2ConcreteHostTests.java').read_text()
check(method(history,'v1Baselines','smoke')==method(current,'v1Baselines','smoke'),'unchanged complete V1 positive control method')
# Exact selected B leaves, except the independently derived probe allowlist delta.
leaf_results={}
for old in sorted((accepted/'host-leaves').rglob('*.java')):
 relative=old.relative_to(accepted/'host-leaves');new=C/'native/android/tests/NativeOwnerV2ConcreteHostLeaves'/relative
 expected=old.read_bytes()
 if old.name=='ConcreteHostProbe.java':expected=expected.replace(b'"NativeOwnerV2","OwnerLifecycleV2"',b'"NativeOwnerV2","NativeEditorConnectionV2","OwnerLifecycleV2"')
 check(new.read_bytes()==expected,'B leaf differs from exact selected mechanical delta '+str(relative));leaf_results[str(relative)]={'origin':ident(old),'candidate':ident(new),'delta':'direct-editor-frame-allowlist-only' if old.name=='ConcreteHostProbe.java' else None}
check(len(leaf_results)==86,'explicit complete accepted B leaf set')
report={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'passed-offline-custody-only','product16':product,'profile_bindings':bindings,'sdk_projection':projection(profile['sdk_files']),'adapter_projection':projection(profile['adapter_files']),'B_leaves':leaf_results,'scope':'Exact source custody and preserved test methods only; executable receipts and combined/native qualification remain separate','new_runtime_or_release_authority':False}
save(D/'source-check-receipt.json',report);print('PASS exact product16, SDK22, adapter24, cross24/76, accepted B86 leaves and unchanged V1 method; offline source custody only')
