#!/usr/bin/env python3
"""Freeze the bounded Caller/Closure mapping; read-only checks plus owned seal."""
import datetime,hashlib,json,pathlib,signal,sys,time
signal.alarm(55)
start=time.monotonic()
out=pathlib.Path(__file__).resolve().parent
root=out.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def load(name): return json.loads((out/name).read_text())
assert load('mapping-report.json')['status']=='incomplete-required-Caller-and-Closure-definitions-not-identified'
assert load('input-pins-before.json')['raw_artifacts']==load('input-pins-after-index.json')['raw_artifacts']
before=load('finalization-input-pins-before.json')
after=load('finalization-input-pins-after.json')
assert before['raw_artifacts']==after['raw_artifacts']
for record in before['raw_artifacts']+after['anchor_inputs']+[before[k] for k in ['selection','frontier','capture_acceptance','independent_terminal_seal']]:
    path=root/record['path']; data=path.read_bytes()
    assert len(data)==record['bytes'] and sha(data)==record['sha256'],record['path']
for name in ['index-method.json','finalization-index-method.json']:
    script=load(name)['script']; data=(root/script['path']).read_bytes()
    assert len(data)==script['bytes'] and sha(data)==script['sha256']
commands={
 'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'inspection_tool':{'python_version':sys.version,'version_provenance':'running stdlib process, no external version command'},
 'commands':[
  {'command':'python3 verification/swift-physical-map-caller-closure/inspect_saved.py','exit_code':0,
   'recorded_elapsed_seconds':load('input-pins-after-index.json')['elapsed_seconds'],
   'stdout_summary':{'selected_definitions':[],'llvm_mentions':0,'asm_mentions':0}},
  {'command':'python3 verification/swift-physical-map-caller-closure/finalize_mapping.py','exit_code':0,
   'recorded_elapsed_seconds':after['elapsed_seconds'],
   'stdout_summary':{'status':load('mapping-report.json')['status'],'indexed':load('mapping-report.json')['indexed'],
                     'expected_source_file_debug_records':1,'expected_file_subprograms':50,'source_line_853_861_subprograms':0}},
  {'command':'git diff --check -- verification/swift-physical-map-caller-closure','exit_code':0,'output':''},
  {'command':'python3 verification/swift-physical-map-caller-closure/seal_mapping.py','execution_scope':'current sealing process'}],
 'scope':'offline saved-artifact and pinned source/MIR text inspection only',
 'no_native_tests_or_compiler_or_capture_processes':True,
 'owned_files_only':True,'raw_inputs_preserved':True,
 'note':'Exit-zero inspection is command completion, not semantic or physical acceptance.'}
(out/'inspection-commands.json').write_text(json.dumps(commands,indent=2,sort_keys=True)+'\n')
excluded={'final-seal.json'}
files=[]
for path in sorted(out.rglob('*')):
    if not path.is_file() or path.name in excluded:continue
    data=path.read_bytes()
    files.append({'path':str(path.relative_to(root)),'bytes':len(data),'sha256':sha(data)})
total=sum(x['bytes'] for x in files)
seal={
 'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'frozen-incomplete-Caller-Closure-mapping-requires-root-independent-review',
 'source_revision':'9e860ea12074ca31bef4087ce34177a03f295dd8',
 'source146_tree_sha256':'91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f',
 'command':'python3 verification/swift-physical-map-caller-closure/seal_mapping.py',
 'command_alarm_seconds':55,'elapsed_seconds_before_seal_write':time.monotonic()-start,
 'raw_pair_total_distinct_bytes':sum(x['bytes'] for x in before['raw_artifacts']),
 'raw_input_pins_rechecked_at_seal':True,'source_MIR_and_control_pins_rechecked_at_seal':True,
 'derived_file_count_excluding_seal':len(files),'derived_bytes_excluding_seal':total,
 'files':files,
 'seal_self_hash_excluded':True,
 'complete_frontier':False,'native_edges_mapped':False,'root_semantic_approval':False,
 'actual_geometry_verifier_run':False,'physical_capacity_peak_certificate_or_GA_accepted':False,
 'all_existing_holds_preserved':True,
 'memory_scope':'Prior memory used only to retain the component-versus-product acceptance boundary; all task-specific facts revalidated from current pinned artifacts.'}
data=(json.dumps(seal,indent=2,sort_keys=True)+'\n').encode()
assert total+len(data)<=8388608
(out/'final-seal.json').write_bytes(data)
print(json.dumps({'status':seal['status'],'files':len(files),'derived_total_bytes':total+len(data),
                  'seal_sha256':sha(data),'elapsed_seconds':time.monotonic()-start},indent=2))
