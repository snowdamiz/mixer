"""Summarize exact compiler evidence and freeze only this source-preparation lane."""
from pathlib import Path
import json,hashlib,datetime,shutil,sys
ROOT=Path(__file__).resolve().parent
assert not (ROOT/'seal.json').exists(),'never mutate a frozen packet'
def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads(path.read_text())
def write(name,data):(ROOT/name).write_text(json.dumps(data,indent=2)+'\n')
profiles=['gated-production-debug','gated-production-optimized','gated-unit-debug','gated-unit-optimized']
commands={p:read(ROOT/'commands'/p/'receipt.json') for p in profiles}
assert all(c['exit_code']==0 and c['child_reaped'] and not c['timed_out'] for c in commands.values())
default_metadata=read(ROOT/'commands/default-typecheck-production/receipt.json')
default_symbols=read(ROOT/'commands/default-production-debug/receipt.json')
absence=read(ROOT/'commands/default-production-debug/measurement-absence.json')
assert default_metadata['exit_code']==0 and not default_metadata['measurement_cfg_enabled']
assert default_symbols['exit_code']==0 and not default_symbols['measurement_cfg_enabled'] and absence['passed']
digests={c['source_tree_sha256'] for c in commands.values()};assert len(digests)==1
manifest=read(ROOT/'source-manifest.json');assert len(manifest['members'])==144
for member in manifest['members']:
    data=(ROOT/'source/vm'/member['path']).read_bytes()
    assert len(data)==member['bytes'] and sha(data)==member['sha256']
digest=sha(json.dumps(manifest['members'],sort_keys=True,separators=(',',':')).encode())
assert digests=={digest}
assert default_metadata['source_tree_sha256']==digest and default_symbols['source_tree_sha256']==digest
ledger=read(ROOT/'encoder-helper-ledger.json')
measurements={}
for profile in profiles:
    layouts=read(ROOT/'commands'/profile/'layouts.json')
    helper_rows=[]
    for group in ['encoder','loader']:
        flat=layouts['MIXER_COMPOSITION_'+group.upper()+'_HELPER_LAYOUTS_V1']
        expected=ledger['groups'][group]
        assert len(flat)==len(expected)*2
        for i,row in enumerate(expected):
            assert flat[i*2:i*2+2]==[row['bytes'],row['alignment']],(profile,row,flat[i*2:i*2+2])
            helper_rows.append({'name':row['name'],'bytes':flat[i*2],'alignment':flat[i*2+1]})
    static_names=ledger['static_capture_names'];flat=layouts['MIXER_COMPOSITION_ENCODER_CAPTURE_LAYOUTS_V1']
    assert len(flat)==len(static_names)*2
    captures=[{'name':name,'bytes':flat[i*2],'alignment':flat[i*2+1]} for i,name in enumerate(static_names)]
    extra=layouts['EXACT_PARAMETER_CAPTURE_V1'];assert extra==[8,8]
    captures.append({'name':'parameter-range','bytes':extra[0],'alignment':extra[1]})
    assert len(captures)==26
    partial=layouts['MIXER_COMPOSITION_CAPTURE_PARTIAL_SUM_V1'];assert partial==[1,152]
    total=partial[1]+extra[0];assert total<=2**64-1
    measurements[profile]={'source_tree_sha256':digest,'helper_shapes':helper_rows,'exact_captures':captures,
        'statically_checked_capture_occurrence_bytes':152,'separate_parameter_capture_bytes':8,'all_capture_occurrence_bytes':total,
        'composition_control_layouts':layouts['MIXER_COMPOSITION_CONTROL_LAYOUTS_V1'],
        'composition_initial_layouts':layouts['MIXER_COMPOSITION_INITIAL_LAYOUTS_V1'],
        'scope':'compiler layout/occurrence evidence; no source/phase/foundation floor or runtime result'}
write('layout-results.json',{'schema':1,'profiles':measurements,'helper_shapes_per_profile':58,'exact_capture_occurrences_per_profile':26,'complete_storage_floor':False})

frozen={
 'selection':('swift-semantic-adapter-root-review/guarded-snapshot-composition-source-preparation-selection.json','9aefd86c679ee13a232315bb3a3a15e59fd3bba8e358139e7bbdffbd24e1573c'),
 'encoder_seal':('swift-guarded-snapshot-encoder-implementation/seal.json','eadbe533d23459573ead21c7a9bac54ae929b98cdbc76dd47aebe34b5ceb2b1f'),
 'correction_seal':('swift-guarded-snapshot-export-admission-correction/seal.json','3812896d87c86c9fe70446494ca48d57d4a848ea4da885e41b877b47388049f5'),
 'original_admission_seal':('swift-guarded-snapshot-export-admission-design/seal.json','b60d1ba0790076b35b6df30dd8df407486f89144e6914f40d2d0d55e4e20e1f5'),
 'correction_acceptance':('swift-semantic-adapter-root-review/guarded-snapshot-admission-correction-host-acceptance.json','a64934fac867f371c670b81b6a49fde0cc0d20691951f5fa723eca5f74ee8d7b'),
 'encoder_acceptance':('swift-semantic-adapter-root-review/guarded-snapshot-encoder-host-acceptance.json','4d0eb23c7306e4d63d039f989391e59e45a928be98ece531f69f543952eb15cb'),
 'measurement_release':('swift-semantic-adapter-root-review/guarded-snapshot-encoder-layout-composition-release.json','6f241f56431eec5f1d192fc97df51adcaea960c9feea211c214b053a202f7ebb'),
 'independent_addendum':('swift-guarded-snapshot-encoder-independent/candidate-review/source-place-addendum.json','c63de76852dc11819935856021ad325208946dd8008e0910dd508a70b9460ce8'),
 'encoder_work_acceptance':('swift-semantic-adapter-root-review/guarded-snapshot-encoder-work-host-acceptance.json','757345abe9013a4d5d880738c794e8a9783061fb733f4de24f432698861e9351'),
}
inputs={}
for name,(relative,expected) in frozen.items():
    path=ROOT.parent/relative;data=path.read_bytes();assert sha(data)==expected
    inputs[name]={'path':'verification/'+relative,'bytes':len(data),'sha256':expected}
write('released-input-custody.json',{'schema':1,'inputs':inputs,'accepted_scope':'root released finite encoder/correction and additive layout inputs only; source floor/work/writer authority unselected'})

negative=read(ROOT/'negative-results-candidate.json');assert negative['all_passed'] and len(negative['results'])==12
truth=read(ROOT/'source-truth.json');assert all(x['passed'] for x in truth['checks'])
all_commands=[]
for path in sorted((ROOT/'commands').glob('*/receipt.json')):
    data=read(path)
    if 'child_reaped' in data:assert data['child_reaped']
    all_commands.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path.read_bytes()),'exit_code':data.get('exit_code'),'source_tree_sha256':data.get('source_tree_sha256')})

# Archive only known owned residual text/probe artifacts; never inventory or
# signal system-wide processes or touch another project's simulator/data.
removed=[]
work=ROOT/'owned-work'
if work.exists():
    residual=[p for p in sorted(work.rglob('*')) if p.is_file()]
    if residual:
        archive=ROOT/'commands/retained-owned-compiler-scratch';archive.mkdir(parents=True,exist_ok=False)
        for p in residual:
            relative=p.relative_to(work);destination=archive/relative
            destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,destination)
            removed.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes()),'retained':destination.relative_to(ROOT).as_posix()})
    shutil.rmtree(work)
write('cleanup.json',{'schema':1,'owned_work_removed':not work.exists(),'archived_residuals':removed,
    'all_recorded_compiler_children_reaped':True,'final_four_compilers_created_owned_process_groups':True,
    'final_four_timeout_actions':{k:v['cleanup_actions'] for k,v in commands.items()},
    'no_retroactive_unknown_group_actions':True,'process_inventory_performed':False,
    'native_ui_capture_device_simulator_emulator_runs':False,'other_projects_processes_or_data_changed':False,
    'limit':'Earlier direct short compiler/type feasibility subprocesses had tool/Python child completion but no separate owned-group proof. No later unknown-group cleanup or inventory was attempted.'})
write('receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status':'isolated-real-source-composition-and-exact-layout-preparation-frozen-awaiting-storage-work-independent-review',
    'source_revision':read(ROOT/'input-custody.json')['source_revision'],'source_members':144,'source_tree_sha256':digest,
    'compiler_profiles':profiles,'compiler_profiles_passed':4,'helper_shapes_each':58,'exact_closure_occurrences_each':26,
    'measurement_cfg':'mixer_snapshot_composition_layout; enabled only in layout probes; no authority or product limit',
    'default_production_metadata_passed':True,'default_production_measurement_symbol_absence_passed':True,
    'ownership_privacy_negative_controls':12,'negative_scope':'same behavioral source before additive measurement seam; both Debug/optimized exact diagnostics retained; no authority body changed afterward',
    'static_custody_controls':len(truth['checks']),'runtime_executions':0,'genuine_admitted_writer_executions':0,
    'future_genuine_fixture_entry':'compiled unit-only source with no dispatch; not executed',
    'planning_contract':'16384 original UNSELECTED planning constant; full source audit pending',
    'emission_contract':'WorkAuditPending; no coefficients/grant selected',
    'accepted_encoder_only_work':'F14224; block26+68I+39D+139W+Q; opaque getter3; no retries after error; caller/control formula pending',
    'complete_storage_floor':False,'healthy_selected_cleanup':False,
    'F1':'actual original post-Construction primary plus independent retirement; enlarged charge/invariant retained',
    'finalizer':'actual scope/cache/adopted/WASI owners consumed; retained outer/error/return uncertainty keeps enlarged Construction charge/invariant',
    'limitations':['full helper/argument/return/move source-place sum and overlap reconciliation pending','pre-Construction funding/lifetime closure pending','single authoritative common Original source floor unselected','work formula and bounded-call amendment require root selection','genuine all-eight/File/alias/fault/work/stop/cleanup behavior and independent review pending','native/UI/capture/device/simulator/emulator/process inventory paused','FieldLog separate-repository immutable publication, OTA/signing/store/customer/operational/GA pending'],
    'retained_failures':['typecheck-production-1: two E0369 generic bracket typos; repaired before successful profiles','measured-typecheck-production-1: E0308 lifetime function-pointer mismatch plus unused probe locals; corrected before fresh four-profile measurement'],
    'unit_diagnostics':'two inherited dropping_copy_types warnings; production has no diagnostics',
    'commands':all_commands,'python_version':sys.version,'canonical_product_changed':False,'git_actions':False,'GA_gates_verified':0})

members=[]
for path in sorted(ROOT.rglob('*')):
    if path.is_file() and path.name!='seal.json':
        data=path.read_bytes();members.append({'path':path.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':sha(data)})
write('seal.json',{'schema':1,'members':members,'member_count':len(members),'total_bytes':sum(m['bytes'] for m in members),
    'scope':'source/compile/layout preparation only; no accepted operational storage/work floor, writer run or healthy selected cleanup'})
print(json.dumps({'members':len(members),'source_tree_sha256':digest,'seal_sha256':sha((ROOT/'seal.json').read_bytes())}))
