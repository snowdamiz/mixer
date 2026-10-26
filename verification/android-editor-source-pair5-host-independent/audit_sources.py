#!/usr/bin/env python3
from pathlib import Path
import datetime,difflib,hashlib,json,re
O=Path(__file__).resolve().parent;R=O.parents[1];P=R/'verification/android-editor-source-pair5-host-integration';C=P/'candidate';B=R/'verification/android-editor-source-pair5-rebinding';A=R/'verification/android-editor-preservation-membership-correction'
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def projection(rows):return hashlib.sha256(''.join(n+'\0'+rows[n]['sha256']+'\n' for n in sorted(rows)).encode()).hexdigest()
def save(n,v):(O/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
profile=json.loads((C/'profile5.json').read_text());assert (C/'profile5.json').read_bytes()==(B/'profile5.json').read_bytes();maps={}
for group,base,origin in [('sdk_files',C/'sdk',B/'sources/sdk'),('adapter_files',C/'native/android',B/'sources/adapter')]:
 maps[group]={}
 for n,x in profile[group].items():
  p=base/n if group=='sdk_files' or not n.startswith('Sources/') else base/'engine'/n
  assert ident(p)==x and p.read_bytes()==(origin/n).read_bytes();maps[group][n]={'path':str(p.relative_to(C)),**ident(p)}
 assert projection(profile[group])==profile['sdk_compatibility_sha256' if group=='sdk_files' else 'adapter_compatibility_sha256']
assert len(maps['sdk_files'])==22 and len(maps['adapter_files'])==24
assert ident(C/'descriptor.json')==profile['default_descriptor'] and (C/'descriptor.json').read_bytes()==(B/'descriptor.json').read_bytes()
old=json.loads((B/'profile4.json').read_text());oldmap=old['adapter_files'];newmap=profile['adapter_files'];changed=[n for n in oldmap if oldmap[n]!=newmap[n]];added=sorted(set(newmap)-set(oldmap));assert set(changed)=={'app/src/dev/mixer/android/'+n for n in ['NativeAppearanceViewsV2.java','NativeRenderer.java','NativeCoordinatorV2.java']};assert added==['app/src/dev/mixer/android/NativeEditorConnectionV2.java'];assert old['sdk_files']==profile['sdk_files'] and old['wire']==profile['wire'] and old['default_descriptor']==profile['default_descriptor']
roster=json.loads((C/'native/android/tests/private-owner-source-pair5-roster.json').read_text())
for n,x in roster['selected_source_identities'].items():assert ident(C/n)==x
for n,v in roster['closures'].items():
 paths=v['actual_production_sources']+[x['source'] for x in v['substitutes']]+v['test_support_sources']+[v['test_source']];assert len(paths)==len(set(paths));assert set(v['actual_production_sources']).isdisjoint({x['source'] for x in v['substitutes']})
 assert len(v['actual_production_sources'])==(11 if n.startswith('A') else 16)
 assert ('native/android/app/src/dev/mixer/android/NativeEditorConnectionV2.java' in paths)==n.startswith('B')
product={}
for p in (A/'source').glob('*.java'):
 q=C/'native/android/app/src/dev/mixer/android'/p.name;assert p.read_bytes()==q.read_bytes();product[p.name]=ident(q)
assert len(product)==16
leaves=[]
for p in sorted((A/'host-leaves').rglob('*.java')):
 n=p.relative_to(A/'host-leaves');q=C/'native/android/tests/NativeOwnerV2ConcreteHostLeaves'/n;b=p.read_bytes()
 if p.name=='ConcreteHostProbe.java':b=b.replace(b'"NativeOwnerV2","OwnerLifecycleV2"',b'"NativeOwnerV2","NativeEditorConnectionV2","OwnerLifecycleV2"')
 assert q.read_bytes()==b;leaves.append({'path':str(n),'origin':ident(p),'candidate':ident(q),'delta':'direct-editor-frame-allowlist' if p.name=='ConcreteHostProbe.java' else None})
assert len(leaves)==86
stub=C/'native/android/tests/NativeOwnerV2HostLeaves/dev/mixer/android/NativeRenderer.java';stubold=R/'native/android/tests/NativeOwnerV2HostLeaves/dev/mixer/android/NativeRenderer.java';delta=b' // Mechanical orchestration-only stub; does not model editor busy behavior.\n boolean editorDisposalBusyV2(){return false;}\n // Root-selected mechanical signature only: no completion/preservation behavior.\n void completeFailedV2(Candidate candidate, Throwable primary, Error firstFatal) {}\n';assert stub.read_bytes().replace(delta,b'')==stubold.read_bytes()
old_suite=P/'historical/native/android/tests/NativeOwnerV2ConcreteHostTests.java';new_suite=C/'native/android/tests/NativeOwnerV2ConcreteHostTests.java'
def method(p,name,next_name):return p.read_text().split('    private static void '+name+'(){',1)[1].split('    private static void '+next_name+'(){',1)[0]
assert method(old_suite,'v1Baselines','smoke')==method(new_suite,'v1Baselines','smoke')
assert (P/'historical/native/android/tests/NativeOwnerV2HostTests.java').read_bytes()==(C/'native/android/tests/NativeOwnerV2HostTests.java').read_bytes()
controls=C/'native/android/tests/NativeEditorPreservationHostControls';original=controls/'IndependentPreservationCompletionControls.java';selected=controls/'SelectedIdentityMembershipReviewControls.java';expected=original.read_text().replace('IndependentPreservationCompletionControls','SelectedIdentityMembershipReviewControls').replace('"token", "membership", "forward"','"token", "membership"');assert expected==selected.read_text()
control_provenance={}
for p in controls.glob('*.java'):
 if p.name=='SelectedIdentityMembershipReviewControls.java':continue
 if p.name=='IndependentOwnForwardControls.java':q=R/'verification/android-editor-preservation-membership-independent/actual-review/selected-controls'/p.name
 else:q=A/'tests'/p.name
 if not q.exists():
  seal=json.loads((P/'input-seals/independent-review-seal.json').read_text());rows=[x for x in seal['members'] if x['sha256']==ident(p)['sha256']];assert rows,p.name
  row=min(rows,key=lambda x:len(x['path']));q=R/'verification/android-editor-preservation-membership-independent/actual-review'/row['path']
 assert q.read_bytes()==p.read_bytes();control_provenance[p.name]={'original':str(q.relative_to(R)),**ident(p)}
# Every promoted target is an exact candidate test member; independently recompute its diff from current untouched canonical originals.
targets=json.loads((P/'test-targets.json').read_text());assert targets['product_sdk_bridge_engine_targets']==[]
assert {x['candidate_path'] for x in targets['targets']}=={str(p.relative_to(P)) for p in (C/'native/android/tests').rglob('*') if p.is_file()}
recomputed=[];changes=[]
for row in targets['targets']:
 q=P/row['candidate_path'];assert ident(q)=={k:row[k] for k in ('bytes','sha256')};n=row['canonical_path'];assert n.startswith('native/android/tests/');p=R/n;a=p.read_text() if p.exists() else '';b=q.read_text()
 if a!=b:changes.append({'path':n,'kind':'changed' if p.exists() else 'added'});recomputed.extend(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+n,tofile='b/'+n))
diff=''.join(recomputed);(O/'independent-test-and-runner-changes.diff').write_text(diff);assert diff.encode()==(P/'test-and-runner-changes.diff').read_bytes()
# Formatting of concatenated diffs is source-bound by independently retained exact target maps; do not use source inspection as release admission.
java=roster['crosscompile']['proposed_java'];swift=roster['crosscompile']['current_swift_c_h'];assert len(java)==len(set(java))==24 and len(swift)==len(set(swift))==76
save('source-audit.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'offline exact source and regression-preservation review only','product16':product,'profile_maps':maps,'profile4_delta':{'changed':changed,'added':added,'unchanged':len(oldmap)-len(changed),'wire_descriptor_sdk_unchanged':True},'selected_B86_leaves':leaves,'A_stub_exact_only_two_selected_methods':True,'A_test_source_unchanged':ident(C/'native/android/tests/NativeOwnerV2HostTests.java'),'V1_method_exact_bytes_preserved':True,'V1_separate_compiled_calls_required':5,'controls_unchanged_provenance':control_provenance,'selected_identity_derivative_only_class_name_and_forward_row_omission':True,'test_targets':len(targets['targets']),'target_delta':changes,'cross_java_count':24,'cross_swift_c_header_count':76,'reviewed_helpers':{n:ident(C/'native/android/tests'/n) for n in ['run-private-owner-host.py','run-private-owner-crosscompile.py']},'new_runtime_release_authority':False})
print('PASS independent source audit; product16 SDK22 adapter24 B86; original A/V1/control assertions retained; exact selected own-forward derivative; targets',len(targets['targets']),'delta',len(changes))
