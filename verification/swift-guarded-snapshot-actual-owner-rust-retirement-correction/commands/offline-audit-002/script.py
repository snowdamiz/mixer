#!/usr/bin/env python3
"""Offline compiler-output custody, narrow diagnostic mapping and owned cleanup."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def row(path):
    data=path.read_bytes();return {'path':str(path.relative_to(HERE)),'bytes':len(data),'sha256':sha(data)}
def write(name,value):(HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
roster=json.loads((HERE/'proposed-command-roster.json').read_text())
for command in roster['commands']:
    receipt=json.loads((HERE/'commands'/command['id']/'receipt.json').read_text())
    assert receipt['child_reaped'] and receipt['exact_owned_group_absent'] and receipt['reason'] is None
    assert receipt['exit']!=0 if receipt['kind']=='compiler-negative' else receipt['exit']==0
build=HERE/'build';products=[row(path) for path in sorted(build.iterdir()) if path.is_file()]
mir_dir=HERE/'mir'
if (mir_dir/'actual.mir').exists():
    # Resume only the exact observed first audit's completed relocation. Its
    # failure/script/output remain retained under commands/offline-audit-001.
    assert not (build/'actual.mir').exists()
    moved=row(mir_dir/'actual.mir');moved['path']='build/actual.mir';products.append(moved)
assert set(p['path'] for p in products)=={'build/actual.mir','build/actual.rmeta','build/tests-debug','build/tests-opt2'}
if not mir_dir.exists():
    mir_dir.mkdir(exist_ok=False)
    shutil.move(build/'actual.mir',mir_dir/'actual.mir')
full=(mir_dir/'actual.mir').read_text();lines=full.splitlines(keepends=True)
starts=[i for i,line in enumerate(lines) if line.startswith('fn ')]
inventory=[];selected={}
for start in starts:
    # A function's outer closing brace is the only zero-indented brace.
    end=start+1
    while end<len(lines) and lines[end]!='}\n':end+=1
    assert end<len(lines)
    raw=''.join(lines[start:end+1]).encode();header=lines[start].rstrip()
    inventory.append({'header':header,'first_line':start+1,'last_line':end+1,'bytes':len(raw),'sha256':sha(raw)})
    names={'correlation-scope':'::correlation_scope_core_v1(',
        'retire-acquired':'fn retire_acquired_owner_core_v1(',
        'correlate-core':'fn correlate_core_v1(',
        'correlate-facade':'fn correlate_admitted_loader_v1(',
        'retire-facade':'fn retire_admitted_owner_v1(',
        'release-token':'::release_v1(_1: CompleteAcquisitionRetirementV1'}
    for name,needle in names.items():
        if needle in header:
            assert name not in selected
            path=mir_dir/(name+'.mir');path.write_bytes(raw);selected[name]=raw.decode()
assert len(selected)==6
scope=selected['correlation-scope'];retire=selected['retire-acquired']
assert scope.index('Cell::<bool>::set(move _3, const true)')<scope.index('Cell::<bool>::replace')<scope.index('_10 = AdmittedLoaderCorrespondenceV1')
assert 'Cell::<bool>::get' in retire and 'AcquisitionRetirementOutcomeV1' in retire and '::Retained(' in retire
def compact_blocks(text,limit=4):
    output=[];count=0;inside=False
    for line in text.splitlines():
        if line.startswith('    bb'):
            count+=1
            if count>limit:break
            inside=True
        if inside:output.append(line.split('//')[0].rstrip())
    return '\n'.join(output)+'\n'
for name in ['correlation-scope','retire-acquired']:(mir_dir/(name+'-first-blocks.txt')).write_text(compact_blocks(selected[name]))
write('mir-function-inventory.json',{'schema':1,'scope':'Complete top-level fn item inventory; full compiler MIR retained separately including non-fn items.','full_MIR':row(mir_dir/'actual.mir'),'function_items':len(inventory),'functions':inventory})
write('mir-review.json',{'schema':1,'source146_tree':roster['source146_tree'],'compiler_command':'commands/production-MIR/plan.json','full_MIR':row(mir_dir/'actual.mir'),'complete_selected_function_items':[row(mir_dir/(name+'.mir')) for name in selected],'scope_set_before_attempt_check_and_input_publication':True,'retirement_barrier_get_in_new_source_MIR':True,'semantic_basis':'Inspect exact selected MIR blocks with source protocol and Debug/opt2 tests; this narrow output mapping alone is not native/release authorization.','added_owner_capture_layouts_prices':'Pending; no old-price/MIR/layout carryover.','layout_query':False,'native_fixture_UI_capture':False})
diagnostics=[]
for command in roster['commands']:
    if command['kind']!='compiler-negative':continue
    path=HERE/'commands'/command['id']/'stderr';text=path.read_text();assert all(d in text for d in command['intended_diagnostics'])
    errors=[line for line in text.splitlines() if line.startswith('error') and not line.startswith('error: aborting')]
    if command['id']=='C01-clone':assert len(errors)==2 and all('E0277' in error for error in errors) and 'missing_clone_requirement_v1(reservation)' in text and 'missing_clone_requirement_v1(attempt)' in text
    else:assert len(errors)==1
    diagnostics.append({'id':command['id'],'errors':errors,'stderr':row(path),'source_manifest':'probes/'+command['id']+'/probe.json','all_errors_at_intended_operation':True,'fresh_Copy_claim':False,'external_metadata_consumer_claim':False})
write('compiler-diagnostic-review.json',{'schema':1,'commands':diagnostics,'positive_controls':'Debug and opt2 h22; exact production caller compiles.','result_retirement_is_compiler_enforced':False,'result_retirement_protocol':'Runtime permanent private barrier; tested success/refusal/extraction/forget, no result-lifetime claim.','old_Copy_replay_dictionary_cfg_test_evidence':'Historical only; not rerun.','external_metadata_consumer':'Unrun and unselected.'})
removed=[]
for name in ['actual.rmeta','tests-debug','tests-opt2']:
    path=build/name;removed.append(row(path));path.unlink()
assert not list(build.iterdir());build.rmdir()
write('artifact-cleanup.json',{'schema':1,'before_generated':products,'removed_generated':removed,'retained_full_MIR':row(mir_dir/'actual.mir'),'all_removed_and_build_directory_absent':not build.exists(),'source_and_commands_retained':True,'scope':'Only exact owned terminal-command outputs. No unrelated process, file or OS inventory.','new_compiler_or_test_execution':False})
print(json.dumps({'MIR_function_items':len(inventory),'selected_exact_MIR_items':len(selected),'compiler_negative_commands_reviewed':len(diagnostics),'removed_generated_bytes':sum(r['bytes'] for r in removed),'build_absent':not build.exists()}))
