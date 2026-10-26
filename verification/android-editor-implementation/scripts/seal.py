#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys,datetime
D=Path(__file__).resolve().parents[1]
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
if '--check' in sys.argv:
 seal=json.loads((D/'seal.json').read_text())
 for row in seal['members']:assert ident(D/row['path'])=={'bytes':row['bytes'],'sha256':row['sha256']},row['path']
 print('PASS frozen candidate seal',len(seal['members']),'members',ident(D/'seal.json')['sha256']);raise SystemExit
host=D/'runs/host-13';cross=D/'runs/cross-2';check=json.loads((D/'source-check.json').read_text())
assert json.loads((host/'receipt.json').read_text())['status']=='passed-host-only'
assert json.loads((cross/'receipt.json').read_text())['status']=='passed-cross-only'
assert 'PASS 38 actual-complete-source groups / 505 assertions' in (host/'host.stdout').read_text()
for folder in ('source','host-leaves','tests','cross-source'):
 for p in sorted((D/folder).rglob('*')):
  if p.is_file():assert ident(p)==ident(host/'inputs'/p.relative_to(D)),('host stale',str(p))
for p in sorted((D/'source').glob('*.java')):assert ident(p)==ident(cross/'inputs/source'/p.name),('cross stale',p.name)
for receipt in (D/'runs').glob('*/receipt.json'):
 row=json.loads(receipt.read_text());assert row['cleanup']['scratch_removed'] and row['cleanup']['children_reaped']
subject_rows={str(p.relative_to(D)):ident(p) for folder in ('source','host-leaves','tests','cross-source') for p in sorted((D/folder).rglob('*')) if p.is_file()}
subject_tree=hashlib.sha256(''.join(p+'\0'+row['sha256']+'\n' for p,row in sorted(subject_rows.items())).encode()).hexdigest()
known=[]
for active,message,close in [(False,'editor native frame active',0),(True,'Editable replacement inside native editor call refused',1)]:
 known.append({'route':'valid native accessibility ACTION_SET_TEXT','active_connection':active,'returned':'IllegalStateException','message':message,'value':'hello','Editable_replaced':False,'native_target_close_calls':close,'terminal':True,'classification':'observed implementation compatibility failure, not selected refusal or pending native-only check'})
save(D/'receipt.json',{
 'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'frozen isolated implementation for independent audit; known compatibility failures; no integration acceptance',
 'context_revision_supplied_by_root':'8ac624160a2cfff10d201d8063f69cf05f005edb','context_tree_supplied_by_root':'604a1360677391356ce401d17f966dfd5f1393e8','context_only_not_source_authority':True,
 'binding_selection_sha256':'89fa92964745eaa306e3e2578aeae822a0cd0224c987f06c7b62edecdf8a292e','producer_seal_sha256':'060347101b96ecb7a5ee180828cf3437d47179fbb82e8c8ba8457a96859023b7','mandatory_addendum_seal_sha256':'ecdc6bd94e2c49b501c2d1dbf69323b8abb3d830c78c689acc39435a31d273c0',
 'product_source_tree_digest':check['source_tree_digest'],'complete_host_closure_tree_digest':subject_tree,'complete_host_closure_subjects':subject_rows,
 'final_host_run':'runs/host-13','bounded_control_groups':38,'assertions_including_expected_failure_witness_assertions':505,'official_InputConnection_descriptors':38,
 'final_cross_run':'runs/cross-2','cross_scope':'unsigned complete-source javac --release17 pinned android-37.0 / D8 min-api28 only; SDK36 product admission guards unchanged',
 'product_source_matches_final_host_and_cross':True,'known_compatibility_failures':known,'ordinary_editor_widget_compatibility_accepted':False,
 'source_check':'source-check.json','source_check_scope':'custody and compiled symbol inventory only; not native/release authorization',
 'first_failed_outputs':['runs/host-1/compile.stderr','runs/host-4/host.stderr','runs/host-11/host.stderr'],
 'failure_history':['Authored host interface initially made later default methods abstract; corrected to exact pinned signatures with hostile default tripwires.','Healthy Binding echo exposed boxed Boolean selecting generic Mutation.result; fixed by explicit boolean overload.','First ACTION_SET_TEXT witness wrongly expected a fresh-field buffer replacement; actual frame guard refuses before replacement; corrected witness with original output preserved.'],
 'cleanup':{'all_owned_compiler_JVM_children_reaped':True,'all_owned_scratch_directories_removed':True,'native_or_capture_processes_started_or_queried':False,'other_projects_touched':False},
 'python':sys.version,'tools':json.loads((cross/'receipt.json').read_text())['tools'],
 'pending':['Independent actual-source audit of this frozen candidate','Selected design and implementation for observed valid ACTION_SET_TEXT replacement gaps','Root canonical integration/source profile selection','Native IME/EditorInfo/selection/composition/batch/lifecycle/visibility/accessibility/TalkBack qualification after user resumes','Physical phones/API28-35/immutable separate-repository FieldLog/store/signing/OTA/operations/GA'],
 'limits':['Controlled authored host leaves are not Android TextView/IME behavior.','Exact native close RETURNED does not prove native batch/service reclamation.','Public lifecycle leases do not cover hidden TextView suffixes or outer platform dispatch quiescence.','Rejected/throwing Handler posts retain pending resource/token without guaranteed autonomous resumption.'],
 'canonical_changes':False,'owner_core_changes':False,'source_profile_promotion':False,'root_metadata_changes':False,'Git_actions':False,'native_or_GA_accepted':False
})
rows=[{'path':str(p.relative_to(D)),**ident(p)} for p in sorted(D.rglob('*')) if p.is_file() and p!=D/'seal.json']
save(D/'seal.json',{'schema':1,'scope':'Complete-source isolated editor implementation and bounded host/cross evidence for independent audit only; known ACTION_SET_TEXT failures; no canonical/native/GA acceptance','product_source_tree_digest':check['source_tree_digest'],'complete_host_closure_tree_digest':subject_tree,'members':rows,'exclusions':['seal.json self digest']})
print('FROZEN',len(rows),'members',sum(r['bytes'] for r in rows),'bytes','seal SHA256',ident(D/'seal.json')['sha256'])
