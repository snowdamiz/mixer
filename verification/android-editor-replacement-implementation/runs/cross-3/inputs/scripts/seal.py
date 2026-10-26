#!/usr/bin/env python3
"""Freeze a completed isolated packet once; --check is strictly read-only."""
from pathlib import Path
import datetime,hashlib,json,re,sys
D=Path(__file__).resolve().parents[1]
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
if '--check' in sys.argv:
 seal=json.loads((D/'seal.json').read_text())
 expected={r['path'] for r in seal['members']};actual={str(p.relative_to(D)) for p in D.rglob('*') if p.is_file() and p!=D/'seal.json'}
 assert actual==expected,('packet member set changed',actual^expected)
 for row in seal['members']:assert ident(D/row['path'])=={'bytes':row['bytes'],'sha256':row['sha256']},row['path']
 print('PASS frozen derivative',len(expected),'members',sum(r['bytes'] for r in seal['members']),'bytes; seal SHA256',ident(D/'seal.json')['sha256']);raise SystemExit
assert not (D/'seal.json').exists(),'Refusing to overwrite an immutable seal'
host=D/'runs/host-9';cross=D/'runs/cross-3';check=json.loads((D/'source-check.json').read_text())
assert json.loads((host/'receipt.json').read_text())['status']=='passed-host-only'
assert json.loads((cross/'receipt.json').read_text())['status']=='passed-cross-only'
m=re.search(r'PASS (\d+) actual-complete-source groups / (\d+) assertions;', (host/'host.stdout').read_text());assert m and int(m[1])==52
for folder in ('source','host-leaves','tests','cross-source'):
 for p in sorted((D/folder).rglob('*')):
  if p.is_file():assert ident(p)==ident(host/'inputs'/p.relative_to(D)),('host input stale',str(p))
for p in sorted((D/'source').glob('*.java')):assert ident(p)==ident(cross/'inputs/source'/p.name),('cross input stale',p.name)
assert ident(D/'cross-source/NativeBridge.java')==ident(cross/'inputs/cross-source/NativeBridge.java')
runs=[]
for p in sorted((D/'runs').glob('*/receipt.json')):
 r=json.loads(p.read_text());assert r['cleanup']['scratch_removed'] and r['cleanup']['children_reaped'] and not r['cleanup']['native_or_capture_processes_started_or_queried']
 runs.append({'run':str(p.parent.relative_to(D)),'status':r['status'],'receipt':ident(p),'cleanup':r['cleanup']})
subjects={str(p.relative_to(D)):ident(p) for folder in ('source','host-leaves','tests','cross-source') for p in sorted((D/folder).rglob('*')) if p.is_file()}
closure=hashlib.sha256(''.join(p+'\0'+r['sha256']+'\n' for p,r in sorted(subjects.items())).encode()).hexdigest()
inputs={str(p.relative_to(D)):ident(p) for folder in ('inputs','official','historical') for p in sorted((D/folder).rglob('*')) if p.is_file()}
input_tree=hashlib.sha256(''.join(p+'\0'+r['sha256']+'\n' for p,r in sorted(inputs.items())).encode()).hexdigest()
old=json.loads((D/'historical/base/receipt.json').read_text())
save(D/'receipt.json',{
 'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'frozen isolated complete-source derivative for independent review; no integration/native/GA acceptance',
 'context_revision_supplied_by_root':'db6332d4c27efec4f9e22b9adc43000d48c591a1','context_tree_supplied_by_root':'dc76d1caa4ad6db89b51f82172314dd6d4b89995','context_only_not_source_authority':True,'historical_original_context_revision':old['context_revision_supplied_by_root'],
 'original_frozen_seal_sha256':'99ee53d6cf73cc062d5f39f7caa743dfed68f0f22522788adabe83159cacc9cd','binding_selections':check['selected_inputs'],'verified_seals':check['seals'],
 'product_source_tree_digest':check['product_source_tree_digest'],'complete_host_closure_tree_digest':closure,'complete_host_closure_subjects':subjects,'reference_and_historical_input_tree_digest':input_tree,'reference_and_historical_inputs':inputs,
 'final_host_run':str(host.relative_to(D)),'control_groups':int(m[1]),'assertions':int(m[2]),'prior_38_groups_preserved':True,'official_InputConnection_descriptors':38,'final_cross_run':str(cross.relative_to(D)),
 'cross_scope':'unsigned complete-source javac --release17 pinned android-37.0 / D8 min-api28 only; API36 product admission guards unchanged','product_source_matches_final_host_and_cross':True,
 'observed_host_replacement_positives':['fresh without connection','active predecessor closed before accessibility super','closed predecessor','same value','empty string','Annotation spans','Unicode','unfocused accessible A with focused healthy B','compatible synchronous Binding echo','later fresh connection and ordinary foreign entry'],
 'EditorInfo_supported_input_contract':'main-first nonnull exact EditorInfo runtime class only, before live/native getters, revoke/attempt/output effects; subclass clean no-call refusal preserves output and healthy adapter; platform qualification pending',
 'historical_original_ACTION_SET_TEXT_failures_unmodified':old['known_compatibility_failures'],'historical_independent_five_findings_unmodified':'historical/findings-1/seal.json','ordinary_editor_widget_compatibility_accepted':False,
 'derivative_failed_outputs':['runs/host-1/compile.stderr','runs/host-3/host.stderr','runs/host-5/host.stderr'],
 'failure_history':['host-1: authored Editable subclass introduced JDK25 this-escape Werror; leaf span methods made final.','host-3: test counted native shadow setters globally; corrected to exact actual field receiver.','host-5: test expected ISE but exact foreign drain rejects using selected Json.bad IAE; expectation corrected to runtime refusal.'],
 'all_runs':runs,'tools':json.loads((cross/'receipt.json').read_text())['tools'],'python':sys.version,
 'cleanup':{'all_owned_compiler_JVM_children_reaped':True,'all_owned_scratch_directories_removed':True,'native_or_capture_processes_started_or_queried':False,'other_projects_touched':False},
 'pending':['Independent actual-source derivative audit','Root canonical integration/source profile selection','Native IME/EditorInfo/selection/composition/batch/lifecycle/visibility/accessibility/TalkBack/OEM qualification after resumption','Physical phones/API28-35/immutable separate-repository FieldLog/store/signing/OTA/operations/GA'],
 'limitations':['Authored Android/JNI leaves are a controlled JVM model, not Android behavior.','Default factory/movement/delegate/transformation/filter premises are checked private admission assumptions; native compatibility remains pending.','EditorInfo subclass support is explicitly refused by selected private supported-input contract.','Returning native close does not prove native batch/service reclamation.','Public lifecycle suffixes do not establish hidden TextView detach suffix or outer dispatch quiescence.','Rejected/throwing Handler posts retain pending custody without guaranteed autonomous retry.','Reflective roster/target/counter injections are host invariant controls, not product exploit claims.','Unbalanced final replacement suffix retains busy terminal custody; no fabricated finish or autonomous repair.'],
 'canonical_changes':False,'owner_core_changes':False,'extra_coordinator_changes':False,'source_profile_promotion':False,'root_metadata_changes':False,'Git_actions':False,'native_or_GA_accepted':False
})
rows=[{'path':str(p.relative_to(D)),**ident(p)} for p in sorted(D.rglob('*')) if p.is_file() and p!=D/'seal.json']
save(D/'seal.json',{'schema':1,'scope':'Frozen complete-source corrected editor replacement candidate and controlled host/unsigned SDK evidence for independent review only; no native/canonical/GA acceptance','product_source_tree_digest':check['product_source_tree_digest'],'complete_host_closure_tree_digest':closure,'reference_and_historical_input_tree_digest':input_tree,'members':rows,'exclusions':['seal.json self digest']})
print('FROZEN',len(rows),'members',sum(r['bytes'] for r in rows),'bytes; seal SHA256',ident(D/'seal.json')['sha256'])
