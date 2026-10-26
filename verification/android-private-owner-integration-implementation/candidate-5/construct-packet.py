#!/usr/bin/env python3
"""Seal only candidate5 after the frozen bounded producer commands terminate."""
from pathlib import Path
import datetime,difflib,hashlib,json,subprocess,sys
ROOT=Path.cwd();BASE=ROOT/'verification/android-private-owner-integration-implementation/candidate-5';C4=ROOT/'verification/android-private-owner-integration-implementation/candidate-4'
def ident(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def save(name,value):(BASE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def read(path):return json.loads(path.read_text())
def validate_manifest(relative,expected):
 p=ROOT/relative;assert ident(p.read_bytes())['sha256']==expected
 m=read(p);total=0
 for rel,identity in m['files'].items():
  q=p.parent/rel
  if not q.is_file():q=ROOT/rel
  assert ident(q.read_bytes())==identity,rel
  total+=identity['bytes']
 assert len(m['files'])==m['members'] and total==m['bytes']
 return {'manifest_path':relative,'manifest':ident(p.read_bytes()),'verified_members':len(m['files']),'verified_bytes':total,'use':'immutable historical provenance; no current independent closure claimed'}
assert not (BASE/'manifest.json').exists()
smap=read(BASE/'source-map.json');assert len(smap)==311
for rel,identity in smap.items():
 assert ident((BASE/'source'/rel).read_bytes())==identity,rel
 assert ident((ROOT/rel).read_bytes())==identity,rel
profile=read(BASE/'profile-proposal.json');projection=lambda files:hashlib.sha256(''.join(k+'\0'+v['sha256']+'\n' for k,v in sorted(files.items())).encode()).hexdigest()
assert projection(profile['adapter_files'])==profile['adapter_compatibility_sha256'] and projection(profile['sdk_files'])==profile['sdk_compatibility_sha256']
assert ident((BASE/'descriptor.json').read_bytes())==profile['default_descriptor']
assert profile['adapter_compatibility_sha256']=='c5df444d5be8f7d422dedde7786b0232f24db1b295288da3cc3fce31a27f5b59'
assert smap['native/android/app/src/dev/mixer/android/NativeOwnerV2.java']['sha256']=='056aa51d07e765b59a3859ce76090477a24211c973b63336406ff4b0d4102269'
assert smap['native/android/app/src/dev/mixer/android/OwnerLifecycleV2.java']['sha256']=='4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6'
refs=[validate_manifest('verification/android-private-owner-integration-implementation/candidate-4/manifest.json','69fcd445119c0ea311c11cf97587d591d87ba1c5bd2d5b3c0a722116f66231c5'),validate_manifest('verification/android-private-owner-independent-review/implementation-review-3/manifest.json','f4afff4105d08642e74f1e5a3255015828e57c2a703b023bdd91ce709be18bc2'),validate_manifest('verification/android-private-owner-effect-integration-root-review/candidate5-proposal/manifest.json','22a119f096db3da04efdbde6b2f6d6c1a2402e22bfc4bac9a0a26fa8687ccf89')]
swiftmap=read(C4/'evidence/swift-jni-final-1/source-map.json');swiftinputs={p:i for p,i in swiftmap.items() if p.startswith(('sdk/','native/android/engine/','native/android/bridge/'))}
for rel,identity in swiftinputs.items():assert ident((ROOT/rel).read_bytes())==identity,rel
save('historical-evidence.json',{'schema':1,'immutable_dependencies':refs,'unchanged_Swift_JNI_input_members':len(swiftinputs),'unchanged_Swift_JNI_inputs':swiftinputs,'Swift_JNI_scope':'Historical C4 ordinary engine/SDK/JNI cross-compilation only; not rerun for the Java-only owner repair. Fresh candidate5 unsigned Java/Android SDK/D8 compilation is separately recorded.','independent_review3_status':'Rejected C4 F09. Historical direct callback timing 1316/1323, seven measure-helper direct rows pending; historical actual owner 129 cases/1787 assertions; 35 groups/153 source sites bound but full447 dynamic expansion pending. No current independent review credit.'})
labels=['before-candidate4-A','after-candidate5-A','after-candidate5-B','after-candidate5-crosscompile'];receipts={};commands={}
for label in labels:
 e=BASE/'evidence'/label;receipt=read(e/'receipt.json');cmd=read(e/'commands.json');receipts[label]=receipt;commands[label]=cmd
 assert receipt['cleanup']['scratch_removed'] and receipt['cleanup']['children_reaped']
 assert all(c['child_reaped'] and c['child_pid']>0 and c['timeout_seconds']>0 and not c['timeout'] and not c['output_limit_exceeded'] for c in cmd)
 for c in cmd:
  assert ident((e/(c['label']+'.stdout')).read_bytes())==c['stdout']
  assert ident((e/(c['label']+'.stderr')).read_bytes())==c['stderr']
 if label.startswith('after-'):assert receipt['source_stable'] and receipt['status'] in ['passed-host-only','passed-crosscompile-only'] and all(c['exit']==0 for c in cmd)
 else:
  assert receipt['status']=='failed' and cmd[-1]['label']=='host' and cmd[-1]['exit']==1
  assert 'owner failed to collect retained ordinary before fatal' in (e/'host.stderr').read_text()
  assert read(e/'source-map.json')['native/android/app/src/dev/mixer/android/NativeOwnerV2.java']['sha256']=='f789a835ec4e0649ba5d1eec2ad267fa4cf7301dfa9151771f6bc0e05b2d3895'
for rel in ['native/android/app/src/dev/mixer/android/NativeOwnerV2.java','native/android/tests/NativeOwnerV2HostTests.java']:
 before=(C4/'source'/rel).read_text();after=(BASE/'source'/rel).read_text();(BASE/(Path(rel).stem+'.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='candidate4/'+rel,tofile='candidate5/'+rel)))
save('failure-control.json',{'schema':1,'status':'expected-candidate4-rejection-and-candidate5-pass','before':'Same strengthened producer test and controlled leaves, frozen C4 owner override. Exact expected owner-primary assertion fails. The baseline runner source_stable=false is expected because its explicit historical owner intentionally differs from current canonical candidate5; no canonical file was reverted.','before_owner':read(BASE/'evidence/before-candidate4-A/source-map.json')['native/android/app/src/dev/mixer/android/NativeOwnerV2.java'],'after_owner':smap['native/android/app/src/dev/mixer/android/NativeOwnerV2.java'],'new_priority_controls':['successful disposal','ordinary-only identity','fatal-only identity/escape','ordinary A then fatal E retains outer A/E and escapes E','earlier outer P precedes component A while retaining fatal E','earlier outer P/F precedes component A/E and escapes F'],'repeated_close':'Each of six variants repeats close twice and checks both resource counts, queue empty, retained identity and exact fatal policy. Existing mixed entry/beforeReturn vectors now check outer identities and escaping E.','native_runtime_qualification':False})
barriers=read(BASE/'evidence/after-candidate5-B/barrier-cases.json')
row_count=len(barriers) if isinstance(barriers,list) else len(barriers.get('cases',[]))
save('source-custody.json',{'schema':1,'command':'python3 -B verification/android-private-owner-integration-implementation/candidate-5/construct-packet.py','python':sys.version,'revision_context':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source_members':len(smap),'all_frozen_and_current_inputs_match':True,'source_map':ident((BASE/'source-map.json').read_bytes()),'profile':ident((BASE/'profile-proposal.json').read_bytes()),'descriptor':ident((BASE/'descriptor.json').read_bytes()),'driver_commands':{k:[{'label':c['label'],'child_pid':c['child_pid'],'deadline_monotonic':c['deadline_monotonic'],'timeout_seconds':c['timeout_seconds'],'child_reaped':c['child_reaped']} for c in v] for k,v in commands.items()},'source_and_evidence_read_scope':'Selected owner/Android source and its named immutable C4, review3 and root-proposal packets; no hosted catalog, authority driver, rejectedWorkerV2 or broad hosted harness accessed or executed.'})
summary={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'frozen-producer-candidate5-awaiting-independent-review-and-root-selection','scope':'Narrow F09 private Android owner diagnostic collection repair; host semantics and unsigned Java/SDK/D8 cross-compilation only','revision_context':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'product_source':'Exact root proposal: closePending collects coordinator retained primary and firstFatal before caught failure; cleanup token/failure and fatal escape mechanism unchanged.','source_members':len(smap),'source_map':ident((BASE/'source-map.json').read_bytes()),'profile':ident((BASE/'profile-proposal.json').read_bytes()),'adapter_projection_sha256':profile['adapter_compatibility_sha256'],'sdk_projection_sha256':profile['sdk_compatibility_sha256'],'profile_id':profile['id'],'core_unchanged':True,'producer_host_A':(BASE/'evidence/after-candidate5-A/host.stdout').read_text().strip(),'producer_host_B':(BASE/'evidence/after-candidate5-B/host.stdout').read_text().strip(),'producer_barrier_rows':row_count,'producer_callback_scope':'Original mechanical matrix rerun on exact candidate5 subjects. Does not close the seven independent direct measure-helper timing rows, full historical dynamic vector expansion, full cancellation/decoder/IME roster or independent source review.','crosscompile':'Fresh strict Java --release17/-Xlint:all/-Werror/-proc:none against Android37 plus D8 minAPI28 pass. Historical unchanged Swift/JNI evidence referenced separately.','compiled_profile_literals_or_CLI_changed':False,'commit_or_push_by_lane':False,'cleanup':{'all_command_children_reaped':True,'all_owned_scratch_removed':True,'native_runtime_UI_capture_or_process_discovery':False,'other_projects_processes_touched':False},'pending':['Independent exact candidate5 source/behavior review and seven direct measure-helper callback rows','Root selection of new adapter hash and separately coordinated fresh CLI/source export consumer qualification','Historical full447 dynamic expansion and broader cancellation/decoder/IME coverage','Android runtime/JNI/IME/draw/lifecycle tests paused; no physical phones','External immutable-package FieldLog dogfood, signing/store/customer/operational/GA gates']}
save('receipt.json',summary)
files={p.relative_to(BASE).as_posix():ident(p.read_bytes()) for p in sorted(BASE.rglob('*')) if p.is_file() and p!=BASE/'manifest.json'}
save('manifest.json',{'schema':1,'files':files,'members':len(files),'bytes':sum(i['bytes'] for i in files.values())})
print(json.dumps({'candidate':str(BASE.relative_to(ROOT)),'manifest':ident((BASE/'manifest.json').read_bytes()),'members':len(files),'bytes':sum(i['bytes'] for i in files.values()),'source_map':ident((BASE/'source-map.json').read_bytes()),'profile':ident((BASE/'profile-proposal.json').read_bytes()),'producer_barrier_rows':row_count,'host_A':summary['producer_host_A'],'host_B':summary['producer_host_B']},indent=2))
