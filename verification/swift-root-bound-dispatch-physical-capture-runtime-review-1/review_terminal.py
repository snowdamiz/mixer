#!/usr/bin/env python3
"""Offline terminal custody review. Generated IR/assembly are hashed only."""
import time
START=time.monotonic()
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ROOT=Path('/Users/andreyyurlov/Documents/dev/mixer')
D=Path(__file__).resolve().parent
LANE=ROOT/'verification/swift-root-bound-dispatch-physical-capture-v1'
RUNTIME=LANE/'runtime'
REVIEW=ROOT/'verification/swift-root-bound-dispatch-physical-capture-independent'
RR=ROOT/'verification/swift-semantic-adapter-root-review'
PINS={}
MEMORY={}
EXPECTED={}

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def identity(info):return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)

def pin(path,expected=None):
    assert time.monotonic()-START<53.5
    path=Path(path)
    if path not in PINS:
        info=path.lstat()
        assert stat.S_ISREG(info.st_mode) and path.resolve(strict=True)==path
        assert info.st_size<=1073741824
        h=hashlib.sha256();size=0
        with path.open('rb') as stream:
            opened=os.fstat(stream.fileno())
            while block:=stream.read(262144):
                assert time.monotonic()-START<53.5
                size+=len(block);assert size<=info.st_size;h.update(block)
            after=os.fstat(stream.fileno())
        assert size==info.st_size and identity(info)==identity(opened)==identity(after)
        PINS[path]={'path':str(path),'bytes':size,'sha256':h.hexdigest()}
    value=PINS[path]
    if expected:assert value['bytes']==expected['bytes'] and value['sha256']==expected['sha256'],str(path)
    return value

def raw(path,expected_sha=None):
    path=Path(path)
    # The artifact data is intentionally never returned as text or parsed.
    assert path.suffix not in ('.ll','.s')
    value=pin(path);assert value['bytes']<=2097152
    if path not in MEMORY:
        data=path.read_bytes();assert len(data)==value['bytes'] and sha(data)==value['sha256'];MEMORY[path]=data
    if expected_sha:assert value['sha256']==expected_sha
    return MEMORY[path]

def loads(data):
    def pairs(items):
        result={}
        for key,value in items:assert key not in result;result[key]=value
        return result
    return json.loads(data,object_pairs_hook=pairs,parse_constant=lambda value:(_ for _ in ()).throw(ValueError(value)))
def load(path,expected_sha=None):return loads(raw(path,expected_sha))
def save(name,value):
    with (D/name).open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')
def relative(folder,name):
    assert type(name) is str and not Path(name).is_absolute() and all(x not in ('','.','..') for x in name.split('/'))
    return folder/name
def expect(path,expected=None):
    value=pin(path,expected);assert value['path'] not in EXPECTED or EXPECTED[value['path']]==value;EXPECTED[value['path']]=value
def members(folder,sealed):
    assert len(sealed['members'])==sealed['member_count'] and len({x['path'] for x in sealed['members']})==sealed['member_count']
    assert sha(canonical(sealed['members']))==sealed['tree_sha256']
    if 'member_bytes' in sealed:assert sum(x['bytes'] for x in sealed['members'])==sealed['member_bytes']
    for item in sealed['members']:expect(relative(folder,item['path']),item)

release_path=RR/'dispatch-physical-capture-release.json'
release=load(release_path,'9c88df2b8f75d8c64d5277bbc4217419d5f6a17ff662744062ed0138314bb836')
plan=load(LANE/'plan.json','3534a9d4bc5428335b3dec4cc295f0b55b1a8ea1c778e265fabdcb9fefb6743e')
base_path=ROOT/plan['base_capture_plan']['path'];pin(base_path,plan['base_capture_plan'])
base=load(base_path,'bed9476b169810452ac0932605784125365f57c897d1e3bf74cd9eaa6ebb8184')
packet=load(LANE/'seal.json','550f6e81fd3abcd5ad74999d953638d99f426f710d48369792922801f753430d')
assert packet['member_count']==12 and packet['controller_sha256']=='1c8036e0dcd5e173c2e379ee6e711c06644638f6fb2caad312c4d41f29ddd98f'
for path in [release_path,LANE/'plan.json',base_path,LANE/'seal.json']:expect(path)
members(LANE,packet)
manifest=load(LANE/'input-manifest.json')
for entry in manifest['inputs']:
    path=Path(entry['path']);expect(path if path.is_absolute() else relative(ROOT,entry['path']),entry)
review_path=ROOT/release['independent_source_review']['path']
assert review_path==REVIEW/'seal.json'
expect(review_path,release['independent_source_review'])
review=load(review_path,'c4ef8437b0fb209ec70c113ff85c607add99ce045ec935da1e518deafd6142da')
members(REVIEW,review)
subject={'base_capture_plan_sha256':pin(base_path)['sha256'],'controller_plan_sha256':pin(LANE/'plan.json')['sha256'],'controller_sha256':pin(LANE/'run-capture.py')['sha256'],'capture_packet_seal_sha256':pin(LANE/'seal.json')['sha256']}
assert release['independent_source_review_subject']==review['independent_source_review_subject']==subject
assert review['findings']==[] and review['compiler_release_recommended'] is True
for key,value in subject.items():assert release[key]==value
assert release['compiler_invocations']==1 and release['automatic_retries']==0 and release['compiler_lane_released'] is True
assert release['reserved_output_authorized'] is True and release['semantic_map_approved'] is False and release['actual_verifier_input_run_released'] is False
assert release['argv_sha256']==sha(canonical(base['argv']))==plan['argv_sha256_canonical_JSON']=='4022ae1057439fe5ae31d18675a884b2dc3e56f317a8ddced08bfb163a410aaa'
for key in ('argv','environment','cwd','bounds','source_directory','source_tree_sha256','source_manifest','compiler','toolchain_manifest','SDK_manifest'):assert canonical(plan[key])==canonical(base[key]),key
expect(Path(plan['python_tool']['path']),plan['python_tool'])
source_path=ROOT/plan['source_manifest']['path'];expect(source_path,plan['source_manifest']);source=load(source_path)
assert len(source['members'])==source['member_count']==146 and sha(canonical(source['members']))==source['tree_sha256']==plan['source_tree_sha256']=='91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f'
for entry in source['members']:expect(relative(Path(plan['source_directory']),entry['path']),entry)
tool_path=ROOT/plan['toolchain_manifest']['path'];expect(tool_path,plan['toolchain_manifest']);tools=load(tool_path)
assert len(tools['members'])==67 and sha(canonical(tools['members']))==tools['tree_sha256']
for entry in tools['members']:expect(relative(Path(tools['root']),entry['path']),entry)
sdk_path=ROOT/plan['SDK_manifest']['path'];expect(sdk_path,plan['SDK_manifest']);sdk=load(sdk_path)
assert str(Path(sdk['requested']).resolve(strict=True))==sdk['resolved']
for entry in sdk['settings']:expect(Path(entry['path']),entry)
policy=load(LANE/'diagnostic-policy.json','707991556c4b7f023010a87ec47d85724daca83a1a891833d03b11fb40e8d879')
frontier_path=ROOT/plan['frontier']['path'];expect(frontier_path,plan['frontier']);frontier=load(frontier_path)
receipt=load(RUNTIME/'receipt.json')
observation=load(RUNTIME/'observations.json','89c7b5a7dd73626f1e10c05075cc8c213704a351934218d3ce3ba358558075cf')
capture=load(RUNTIME/'capture-observation.json','59a878cb673251a32a9ed4603ce69d3ef4dd8df6366ad3a8242dcce3ae4a23a9')
assert receipt['observations_sha256']==pin(RUNTIME/'observations.json')['sha256'] and receipt['capture_observation_sha256']==pin(RUNTIME/'capture-observation.json')['sha256']
assert receipt['status']==capture['status']=='captured-artifacts-only'
for key,expected in [('plan_sha256',subject['controller_plan_sha256']),('base_plan_sha256',subject['base_capture_plan_sha256']),('packet_seal_sha256',subject['capture_packet_seal_sha256']),('controller_sha256',subject['controller_sha256'])]:assert observation[key]==receipt[key]==expected
assert observation['packet_tree_sha256']==packet['tree_sha256']
assert observation['independent_source_review']==release['independent_source_review']
assert observation['source_tree_sha256']==source['tree_sha256']
assert observation['pins_before']==observation['pins_after']==sorted(EXPECTED.values(),key=lambda item:item['path'])
assert observation['all_pins_rechecked'] is True and observation['errors']==receipt['observed_signals']==receipt['finalization_errors']==[]
assert observation['automatic_retries']==0 and observation['owned_groups_closed'] is True
assert observation['signal_record_overflow'] is receipt['signal_record_overflow'] is False
assert observation['python_tool']==plan['python_tool'] and observation['python_version']==plan['python_version_from_this_preparation']
assert observation['compiler_version_from_prior_pinned_receipt']==base['version_from_prior_pinned_receipt']
assert observation['controller_environment']==plan['controller_environment']
assert len(observation['commands'])==1
command=observation['commands'][0]
assert command['kind']=='compiler-capture' and command['argv']==plan['argv'] and command['environment']==plan['environment'] and command['cwd']==plan['cwd']
assert command['custody'] is True and command['pid']==command['pgid']==command['sid']==65417
completion=command['completion_observation']
assert completion['pid']==command['pid'] and completion['code']==1 and completion['status']==0
assert command['cleanup_path']=='completed-child-no-signals' and command['reaped'] is True and command['returncode']==0 and command['group_absent'] is True
assert not command.get('permission_refusal') and not command.get('custody_uncertain') and not command.get('syscall_errors') and command.get('signals',[])==[]
assert command['full_streams_captured'] is True and not command.get('output_truncated')
bounds=plan['bounds']
assert 0<command['start_seconds']<completion['seconds']<=command['reap_seconds']<=command['group_absent_seconds']<=command['end_seconds']<bounds['work_deadline_seconds']==44
assert command['end_seconds']<observation['elapsed_before_observation_seconds']<receipt['signal_cutoff_seconds']<bounds['posthash_deadline_seconds']==53.5
assert bounds['owned_cleanup_deadline_seconds']==49 and bounds['wall_seconds']==55
assert 'later signals outside this receipt' in receipt['signal_scope']
for name in ('stdout','stderr'):
    entry=command[name];assert entry['file']=='compile.'+name
    pin(RUNTIME/entry['file'],entry);assert entry['bytes']<=bounds['maximum_'+name+'_bytes']
assert raw(RUNTIME/'compile.stdout')==b''
stderr=raw(RUNTIME/'compile.stderr');assert stderr.endswith(b'\n') and len(stderr)==8104
lines=stderr.splitlines();assert len(lines)==4 and all(lines)
records=[loads(line.decode('utf-8')) for line in lines]
assert canonical(records)==canonical(policy['records'])
assert [item['level'] for item in records]==['warning']*4 and [item['code']['code'] for item in records[:3]]==['unused_imports','unused_imports','deprecated']
assert records[-1]=={'$message_type':'diagnostic','children':[],'code':None,'level':'warning','message':'3 warnings emitted','rendered':'warning: 3 warnings emitted\n\n','spans':[]}
assert observation['diagnostics']=={'actual_memory_bytes':len(stderr),'actual_memory_sha256':sha(stderr),'policy_sha256':pin(LANE/'diagnostic-policy.json')['sha256'],'success_summary_objects':1,'warning_objects':3}
generated=observation['generated'];assert len(generated['members'])==generated['member_count']<=bounds['maximum_generated_members']==64
assert len({x['path'] for x in generated['members']})==generated['member_count']
retained=observation['retained_generated_files'];assert len({x['path'] for x in retained})==len(retained)
expected_retained=[];generated_bytes=0;expected_runtime={}
for entry in generated['members']:
    relative(RUNTIME,entry['path'])
    name='generated/'+entry['path']
    if entry['type']=='file':
        generated_bytes+=entry['bytes'];expected_retained.append({'path':name,'bytes':entry['bytes'],'sha256':entry['sha256']})
        pin(relative(RUNTIME,name),entry)
        expected_runtime[name]={'type':'file','bytes':entry['bytes'],'sha256':entry['sha256']}
    else:
        assert entry['type']=='directory' and entry['bytes']==0
        expected_runtime[name]={'type':'directory','bytes':0}
assert generated_bytes==generated['file_bytes']<=bounds['maximum_generated_total_bytes']==268435456
assert sorted(retained,key=lambda item:item['path'])==sorted(expected_retained,key=lambda item:item['path'])
assert observation['observed_live_max_members']<=64 and observation['observed_live_max_bytes']<=268435456
assert observation['generated_directory_removed'] is True and not os.path.lexists(plan['owned_output_directory'])
retained_map={x['path']:x for x in retained}
assert retained_map['generated/dispatch.ll']['bytes']==35647549 and retained_map['generated/dispatch.s']['bytes']==23157878
outputs=[{'name':name,'bytes':entry['bytes'],'sha256':entry['sha256']} for name,entry in [('ir',retained_map['generated/dispatch.ll']),('asm',retained_map['generated/dispatch.s']),('stdout',command['stdout']),('stderr',command['stderr'])]]
assert capture['outputs']==outputs and capture['binding']==plan['verifier_binding'] and capture['source_manifest_sha256']==plan['source_manifest']['sha256']
assert capture['compiler_exit']==0 and capture['bounds_met'] is capture['capture_complete'] is capture['cleanup_complete'] is capture['owned_groups_closed'] is True and capture['truncated'] is False
assert observation['frontier_targets']==[{'id':entry['id'],'source':entry['source'],'mapping':'unresolved'} for entry in frontier['targets']]
assert [entry['id'] for entry in observation['frontier_targets']]==['Caller','Closure','Dispatch','Body']
assert observation['missing_private_DCE_or_ambiguous_targets_cannot_complete_frontier'] is True
for data in [receipt,observation,plan,packet,review]:
    assert data.get('frontier_complete',False) is False and data.get('complete_capacity_accepted',False) is False
    assert data.get('physical_capacity_prices_backings_root_funding_product_GA_accepted',False) is False
assert receipt['all_results_local_geometry_only'] is observation['all_results_local_geometry_only'] is True
# Inventory only the root-owned retained directory. This is not a process probe.
expected_runtime['generated']={'type':'directory','bytes':0}
for name in ('receipt.json','observations.json','capture-observation.json','compile.stdout','compile.stderr'):
    entry=pin(RUNTIME/name);expected_runtime[name]={'type':'file','bytes':entry['bytes'],'sha256':entry['sha256']}
inventory={};pending=[RUNTIME];total=0;count=0
while pending:
    assert time.monotonic()-START<53.5
    folder=pending.pop();assert folder.resolve()==folder and stat.S_ISDIR(folder.lstat().st_mode)
    with os.scandir(folder) as entries:
        for entry in entries:
            count+=1;assert count<=plan['retained_evidence_bounds']['maximum_retained_members']==80
            path=Path(entry.path);info=entry.stat(follow_symlinks=False);name=str(path.relative_to(RUNTIME))
            if stat.S_ISDIR(info.st_mode):inventory[name]={'type':'directory','bytes':0};pending.append(path)
            else:
                assert stat.S_ISREG(info.st_mode) and info.st_nlink==1
                assert path.name!='__pycache__' and path.suffix not in ('.pyc','.pyo')
                entry_pin=pin(path);total+=entry_pin['bytes'];assert total<=plan['retained_evidence_bounds']['maximum_total_retained_bytes']==279969792
                inventory[name]={'type':'file','bytes':entry_pin['bytes'],'sha256':entry_pin['sha256']}
assert inventory==expected_runtime
# Preserve the original preflight refusal and its already-frozen predecessor pins.
attempt_path=ROOT/plan['controller_environment_provenance']['root_preflight_receipt']['path']
pin(attempt_path,plan['controller_environment_provenance']['root_preflight_receipt']);attempt=load(attempt_path)
assert attempt['status']=='preflight-refused-before-test-launch' and attempt['candidate_imports_or_tests']==0
for key in ('release','controller'):pin(ROOT/attempt[key]['path'],attempt[key])
prior_runner=load(ROOT/'verification/swift-physical-verifier-host-runner-2/manifest.json')
old_manifest_path=ROOT/'verification/swift-physical-verifier-host-runner-1/manifest.json'
old_manifest=load(old_manifest_path,prior_runner['previous_attempt_provenance']['previous_runner_manifest_sha256'])
for entry in old_manifest['members']:pin(old_manifest_path.parent/entry['path'],entry)
# Current source bytes retain the reviewed observation/hash/cutoff sequence.
controller=raw(LANE/'run-capture.py').decode();tail=controller[controller.index('        save("capture-observation.json", capture_observation)'):]
assert tail.index('save("observations.json"')<tail.index('observations_sha = digest(')<tail.index('capture_observation_sha = digest(')<tail.index('signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)')<tail.index('cutoff = time.monotonic() - START')<tail.index('signal.sigpending()')<tail.index('save("receipt.json"')
assert tail.count('digest(')==2 and tail.count('verify_pins(')==0
before=sorted(PINS.values(),key=lambda item:item['path']);saved=dict(PINS);PINS.clear()
for path,expected in saved.items():pin(path,expected)
after=sorted(PINS.values(),key=lambda item:item['path']);assert before==after
save('checked-inputs.json',{'before':before,'after':after,'equal':True,'tree_sha256':sha(canonical(before)),'runtime_pins_reconstructed':len(EXPECTED)})
save('retained-inventory.json',{'member_count':count,'total_bytes':total,'members':[dict(path=name,**value) for name,value in sorted(inventory.items())],'IR_assembly_hash_only_no_interpretation':True})
result={
 'schema':1,'status':'FROZEN_INDEPENDENT_TERMINAL_REVIEW_RAW_CAPTURE_CUSTODY_ACCEPTED_ONLY',
 'at':datetime.now(timezone.utc).isoformat(),'findings':[],'raw_capture_custody_accepted':True,
 'command':[str(Path(sys.executable).resolve()),'-B',str(Path(__file__).resolve())],
 'review_script_sha256':sha(Path(__file__).read_bytes()),'python':sys.version,
 'elapsed_seconds':time.monotonic()-START,'checked_input_members':len(before),'before_after_custody_equal':True,
 'runtime_pins_reconstructed':len(EXPECTED),'source_members_verified':146,'compiler_sysroot_members_verified':67,
 'source_tree_sha256':source['tree_sha256'],'toolchain_tree_sha256':tools['tree_sha256'],
 'SDK_scope':'Pinned path and settings only;not full SDK implementation qualification.',
 'root_release':pin(release_path),'producer_seal':pin(LANE/'seal.json'),'controller_plan':pin(LANE/'plan.json'),
 'controller':pin(LANE/'run-capture.py'),'source_review_seal':pin(review_path),
 'receipt':pin(RUNTIME/'receipt.json'),'observation':pin(RUNTIME/'observations.json'),'capture_observation':pin(RUNTIME/'capture-observation.json'),
 'compiler_invocations':1,'automatic_retries':0,'compiler_exit':0,
 'root_observation_seconds':observation['elapsed_before_observation_seconds'],'root_signal_cutoff_seconds':receipt['signal_cutoff_seconds'],
 'compiler_child':{'pid':command['pid'],'completion':completion,'cleanup_path':command['cleanup_path'],'reaped':True,'group_absent':True,'active_signals':[]},
 'exact_diagnostics':{'whole_warnings':3,'success_summary':1,'stderr_bytes':len(stderr),'stderr_sha256':sha(stderr),'stdout_bytes':0,'policy_sha256':pin(LANE/'diagnostic-policy.json')['sha256']},
 'retained_artifacts':retained,'retained_generated_bytes':generated_bytes,'runtime_retained_members':count,'runtime_retained_bytes':total,
 'original_owned_command_tree_removed':True,'all_runtime_pins_rechecked':True,'observed_signals':[],'errors':[],
 'first_preflight_refusal_preserved':True,
 'accepted_boundary':'One exact unchanged-source compiler invocation emitted and retained bounded IR/assembly with exact diagnostics,owned-child closure,cleanup,unchanged source/tool pins and a finite final receipt. This is raw artifact custody only.',
 'recommendation':'Accept raw capture custody only. Root may separately select a bounded whole-function mapping/source review of the saved artifacts;no compiler retry,semantic-map approval,physical-region acceptance or actual-input verifier execution is implied.',
 'limits':[
  'IR/assembly were streamed through hashing only;no symbol/function interpretation,CFG mapping or native-target reachability conclusion.',
  'All four Caller/Closure/Dispatch/Body mappings stay unresolved and frontier_complete=false.',
  'Reported process custody is checked from saved evidence;this review performed no live process query.',
  'Finite receipt scope ends at the cutoff;later signals and unexercised failure/timeout branches are not qualified.',
  'Retained-tree limits are bounded observations,not a kernel sandbox or proof of instantaneous peak storage or writes elsewhere.',
  'No physical union,transitive/destruction/backing bound,numeric work price,grant,root funding,product integration,native/device acceptance,publication or GA.'
 ],
 'this_review_controller_import_compiler_tests_semantic_map_actual_verifier_runtime_or_process_probe_actions':0,
 'canonical_product_metadata_commit_push_actions':0,
 'raw_capture_only':True,'frontier_complete':False,'all_results_local_geometry_only':True,
 'complete_capacity_accepted':False,'physical_capacity_prices_backings_root_funding_product_GA_accepted':False
}
assert time.monotonic()-START<55
save('review-result.json',result)
print(json.dumps({'status':result['status'],'runtime_pins':len(EXPECTED),'checked_inputs':len(before),'retained_members':count,'retained_bytes':total,'elapsed_seconds':result['elapsed_seconds']}))
