#!/usr/bin/env python3
"""Custody, actual-bytecode and scoped source proof. Never an OTA/native release gate."""
from pathlib import Path
import hashlib,json,re,difflib,datetime,sys,subprocess
D=Path(__file__).resolve().parent
assert not (D/'seal.json').exists(),'frozen packet'
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def mapping(folder):return {str(p.relative_to(folder)):ident(p) for p in sorted(folder.rglob('*')) if p.is_file()}
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(name,value):(D/name).write_text(json.dumps(value,indent=2)+'\n')
def method(source,signature):
 start=source.index(signature);opening=source.index('{',start);depth=0
 for i in range(opening,len(source)):
  if source[i]=='{':depth+=1
  elif source[i]=='}':
   depth-=1
   if depth==0:return source[start:i+1]
 raise AssertionError(signature)
def sealed(root,sha):
 assert ident(root/'seal.json')['sha256']==sha
 seal=json.loads((root/'seal.json').read_text());total=0
 for row in seal['members']:
  actual=ident(root/row['path']);assert actual=={k:row[k] for k in ('bytes','sha256')},row['path'];total+=row['bytes']
 assert total==seal['member_bytes'] and len(seal['members'])==seal['member_count']
 return {'seal_sha256':sha,'members':seal['member_count'],'bytes':total}
base=D/'base-candidate';witness=D/'witness-PC-C16'
inputs={'base':sealed(base,'8f355ae83ec4d734e8d28451fc64a45200967a718eecb7c1987fa0fcc69d9920'),'PC_C16':sealed(witness,'736df698b56281a71fe3621326107da463aeb4bf8237712c18d188513d96cc44')}
before=mapping(base/'source');after=mapping(D/'source');assert len(before)==len(after)==16
assert digest(before)=='cb5c2b813b9cb375f2907bafcb066ba9c556a2713ffd04c9d74777d9595d01e4'
changed=[name for name in before if before[name]!=after[name]];assert changed==['NativeRenderer.java']
s=(D/'source/NativeRenderer.java').read_text();old=(base/'source/NativeRenderer.java').read_text()
(D/'NativeRenderer.java.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='sealed-preservation-completion/NativeRenderer.java',tofile='membership-correction/NativeRenderer.java')))
assert mapping(D/'host-leaves')==mapping(base/'host-leaves')
assert mapping(D/'cross-source')==mapping(base/'cross-source')
for name,row in mapping(base/'tests').items():assert ident(D/'tests'/name)==row,name
assert ident(D/'tests/IndependentPreservationCompletionControls.java')==ident(witness/'controls-5/control-source/IndependentPreservationCompletionControls.java')
assert ident(D/'descriptor.json')==ident(base/'descriptor.json')
assert len(mapping(D/'tests'))==len(mapping(base/'tests'))+2
unchanged={}
for signature in ['private void requireV2Live()','private void requireEditorsAvailableV2()','boolean editorDisposalBusyV2()','void publishScalarV2(','void sealScalarV2()','private void requireTransactionV2(','private void validateV2(','public void fieldPreservationBegin(','public void fieldPreservationEnd(']:
 a=method(old,signature);b=method(s,signature);assert a==b,signature;unchanged[signature]=hashlib.sha256(b.encode()).hexdigest()
marker='        // No call, allocation, throwing guard, reporter, getter or callback below this boundary.'
old_finish=method(old,'void finishV2(');new_finish=method(s,'void finishV2(')
assert old_finish[old_finish.index(marker):]==new_finish[new_finish.index(marker):]
base_identity=method(old,'boolean fieldPreservationIdentityV2(');captured=method(s,'private boolean fieldPreservationCapturedV2(')
assert base_identity.split('if(',1)[1].split(')return false;',1)[0]==captured.split('return !(',1)[1].rsplit(');',1)[0].strip()
assert s.count('new NativeState(this,previous.size(),record)')==1
assert s.count('new PreservationMembership(state,scope)')==1 and s.count('state.membership=membership;')==1
begin=method(s,'private void beginFieldPreservationsV2(')
assert begin.index('state.membership!=null')<begin.index('new PreservationMembership')<begin.index('state.membership=membership')<begin.index('record.input.fieldPreservationBegin')
for run in ['host-2','cross-2']:
 r=D/'runs'/run;receipt=json.loads((r/'receipt.json').read_text());assert receipt['status']=='passed-'+run.split('-')[0]+'-only'
 assert mapping(r/'inputs/source')==after
 for folder in ['tests','host-leaves','cross-source']:assert mapping(r/'inputs'/folder)==mapping(D/folder)
 assert json.loads((r/'source-map.json').read_text())==mapping(r/'inputs')
 assert json.loads((r/'source-freeze.json').read_text())['complete_source_map']==ident(r/'source-map.json')
 for name,row in json.loads((r/'class-map.json').read_text()).items():assert ident(r/'classes'/name)==row
 commands=json.loads((r/'commands.json').read_text());assert len(commands)==receipt['commands']
 for row in commands:
  assert row['exit']==0 and row['elapsed_seconds']<60 and row['reaped']
  assert ident(r/(row['name']+'.stdout'))==row['stdout'] and ident(r/(row['name']+'.stderr'))==row['stderr']
for name,row in json.loads((D/'runs/cross-2/dex-map.json').read_text()).items():assert ident(D/'runs/cross-2/dex'/name)==row
baseline=(D/'runs/baseline-1/independent-journal-membership.stdout').read_text()
assert 'returned=true' in baseline and 'Ccounted=true' in baseline and 'busy=false' in baseline
assert ident(D/'runs/baseline-1/independent-journal-membership.stdout')==ident(witness/'controls-5/independent-journal-membership.stdout')
assert ident(D/'runs/baseline-1/independent-journal-membership.stderr')==ident(witness/'controls-5/independent-journal-membership.stderr')
fixed=(D/'runs/host-2/independent-journal-membership.stdout').read_text()
assert all(word in fixed for word in ['returned=false','terminal=true','completion=4','shared=2','preservation=2','held=2','Acounted=true','Ccounted=true','Cregistered=true','busy=true','/ 335 assertions'])
assert 'failed completion wrong journal refuses before endpoint effects on both owners' in (D/'runs/host-1/completion-foreign-endpoints.stderr').read_text()
# Inspect actual bytecode generated from both final complete source closures.
proof={}
helpers=[('  private boolean preservationMembershipV2(', '  private boolean fieldPreservationCapturedV2(',[]),('  private boolean fieldPreservationCapturedV2(', '  private boolean preservationProvenanceV2(',[]),('  private boolean preservationProvenanceV2(', '  boolean fieldPreservationIdentityV2(',['fieldPreservationCapturedV2']),('  boolean fieldPreservationIdentityV2(', '  private boolean preservationCohortV2(',['fieldPreservationCapturedV2','preservationMembershipV2']),('  private boolean preservationCohortV2(', '  private boolean preservationFailureFundedV2(',['preservationMembershipV2']),('  private boolean preservationFailureFundedV2(', '  private boolean preservationEndReadyV2(',['preservationMembershipV2'])]
for run in ['host-2','cross-2']:
 text=(D/'runs'/run/'completion-bytecode.stdout').read_text()
 def code(signature,end):
  start=text.index(signature);return text[start:text.index(end,start)]
 row={'bytecode':ident(D/'runs'/run/'completion-bytecode.stdout'),'success_tail':{},'scalar_helpers':{}}
 for name,start,end in [('finishV2','  void finishV2(','  void validateAttachedV2('),('fieldPreservationBegin','  public void fieldPreservationBegin(','  public void fieldPreservationEnd(')]:
  body=code(start,end);instructions=[line for line in body.splitlines() if re.match(r'\s+\d+:',line)]
  last=max(i for i,line in enumerate(instructions) if re.search(r': athrow\b',line));tail=instructions[last+1:];assert tail
  assert all(not re.search(r': (?:invoke\w*|new\w*|anewarray|multianewarray|athrow|monitor\w*)\b',line) for line in tail),(run,name)
  offsets={int(line.split(':',1)[0]) for line in tail};boundary=min(offsets)
  for line in tail:
   match=re.search(r': (?:if\w*|goto)\s+(\d+)',line)
   if match:assert int(match.group(1)) in offsets
  p=D/(run+'-'+name+'-scalar-tail.bytecode');p.write_text('\n'.join(tail)+'\n')
  row['success_tail'][name]={'first_offset':boundary,'instructions':len(tail),'tail':ident(p),'no_invocation_allocation_explicit_throw_monitor_or_external_branch':True}
 for start,end,allowed in helpers:
  body=code(start,end);assert not re.search(r': (?:new\w*|anewarray|multianewarray|athrow|monitor\w*)\b',body),start
  calls=re.findall(r': invoke\w*\s+[^\n]+',body)
  assert all(any('Method '+name+':' in call for name in allowed) for call in calls),(start,calls)
  row['scalar_helpers'][start.strip()]={'instructions':sum(bool(re.match(r'\s+\d+:',line)) for line in body.splitlines()),'calls_only':allowed,'observed_calls':calls}
 # The sole new membership object's constructor has only Object initialization and final reference writes.
 ctor=code('  dev.mixer.android.NativeRenderer$PreservationMembership(', '\n}')
 assert len(re.findall(r': invoke',ctor))==1 and 'java/lang/Object."<init>"' in ctor
 assert not re.search(r': (?:new\w*|anewarray|multianewarray|athrow|monitor\w*)\b',ctor)
 (D/(run+'-PreservationMembership-constructor.bytecode')).write_text(ctor+'\n')
 row['new_member_constructor']={'only_Object_init_and_direct_final_reference_writes':True,'bytecode':ident(D/(run+'-PreservationMembership-constructor.bytecode'))}
 proof[run]=row
save('scalar-completion-proof.json',{'scope':'Actual final complete-source JVM/SDK37 bytecode and source invariants; no native/OTA qualification','runs':proof,'whole_success_tail_source_byte_identical_to_base':True,'begin_entire_method_source_byte_identical_to_base':True,'callgraph':'Success preflight: preservationProvenanceV2 -> fieldPreservationCapturedV2; membership is direct fields/array bounds/positions; identity -> captured+membership; cohort -> membership. Other existing non-error preflight call is ArrayDeque.isEmpty. No main/current/native/Input/snapshot/JNI/event/reporter/owner or allocation.', 'bound_and_failure_proof':['UiPacket retains existing unique-id/node cap4096; Candidate baseRecords are its already-installed records; no cap changed','Journal creates exactly one NativeState(this,previous.size(),record) per record before copying ordered previous into final states/stateCount; private source has no other constructor call','NativeState final journal+position gives one source-constructed state at each exact position; duplicate/swap/null/foreign/array-size/count mismatch cannot satisfy ordered admission','Exactly one PreservationMembership per actual preserved state is allocated before any member/Record registration or Begin acquisition; final state/scope references bind scope identity; duplicate capture guard precedes its creation','New membership constructor performs only Object initialization plus final reference assignments; allocation/constructor failure precedes publication and acquisition, so no own registration/count needs cleanup; earlier actual entered scopes remain discoverable through unchanged candidate journal. Allocation-failure-at-new is source proof, not a fault-injected JVM/Android receipt','PC-P02 existing constructor-before-registration, CAPTURED refusal and partial-entry controls replay unchanged; no scope/count fabricated','No product callback or mutation can alter the fixed prevalidated roster during the direct success tail; no asynchronous VM interruption or arbitrary reflection/Unsafe recovery claim'],'failure_release':'Membership checked at entry, before each post-report scope effect, and after final reporters before either release loop; known-own malformed roster retains every unproven hold and consumes failed endpoint once; foreign captured authority refuses before endpoint effects'})
# Context revision is intentionally distinct from the frozen isolated product tree.
revision=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,check=True,timeout=60)
(D/'source-revision-context.stdout').write_bytes(revision.stdout);(D/'source-revision-context.stderr').write_bytes(revision.stderr)
save('source-verification.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision_context_only':revision.stdout.decode().strip(),'revision_command':['git','rev-parse','HEAD'],'revision_stdout':ident(D/'source-revision-context.stdout'),'revision_stderr':ident(D/'source-revision-context.stderr'),'python':{'version':sys.version,'executable':str(Path(sys.executable).resolve()),'file':ident(Path(sys.executable).resolve())},'immutable_input_reverification':inputs,'base_product_tree':digest(before),'product_tree':digest(after),'complete_host_tree':digest({name:mapping(D/name) for name in ['source','host-leaves','tests']}),'changed_product_files':changed,'unchanged_product_files':[name for name in after if name not in changed],'unchanged_sensitive_methods':unchanged,'NativeAppearanceViews_Coordinator_other13_byte_identical_to_base':True,'bothSDK36guards_unchanged':True,'original8_test_files_and_selected_adaptations_unchanged':True,'witness_full_source_and_assertions_unchanged':True,'host_leaves_and_JNI_signature_leaf_unchanged':True,'selected_final_runs':['host-2','cross-2'],'source_map':after})
receipts=[]
for p in sorted((D/'runs').glob('*/receipt.json')):
 row=json.loads(p.read_text());assert row['cleanup']['scratch_removed'] and row['cleanup']['children_reaped'] and not row['cleanup']['native_or_capture_processes_started_or_queried']
 receipts.append({'path':str(p.relative_to(D)),'status':row['status'],'receipt':ident(p)})
assert not [p for p in D.rglob('owned-*') if p.is_dir()] and not list(D.rglob('__pycache__'))
save('cleanup.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owned_children_bound_seconds':60,'all_owned_children_reaped':True,'all_owned_scratch_removed_including_failed_runs':True,'native_UI_capture_or_process_inventory_started_or_queried':False,'other_projects_touched':False,'run_receipts':receipts,'note':'Deliberate malformed host custody remains held until bounded JVM exits; this is not native reclamation evidence. Base-candidate historical outputs are frozen custody, not rerun/cleanup claims.'})
print('PASS Renderer-only exact source custody; all unchanged suites/witnesses; final host/SDK bytecode scalar tails; captured construction bound; raw baseline/regression retained; scratch cleanup')
