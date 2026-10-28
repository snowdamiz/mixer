#!/usr/bin/env python3
"""Source/text/hash review only; no target import, syntax check or execution."""
import time
START = time.monotonic()
from collections import Counter
import copy
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
D = Path(__file__).resolve().parent
LANE = ROOT/'verification/swift-root-bound-dispatch-physical-capture-v1'
PINS = {}
DATA = {}

def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def identity(info): return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)

def pin(path, expected=None):
    assert time.monotonic()-START < 53.5
    path = Path(path)
    if path not in PINS:
        info = path.lstat()
        assert stat.S_ISREG(info.st_mode) and path.resolve(strict=True) == path
        assert info.st_size <= 1073741824
        h = hashlib.sha256(); count = 0
        with path.open('rb') as stream:
            opened = os.fstat(stream.fileno())
            while chunk := stream.read(262144):
                assert time.monotonic()-START < 53.5
                count += len(chunk); assert count <= info.st_size; h.update(chunk)
            after = os.fstat(stream.fileno())
        assert count == info.st_size and identity(info) == identity(opened) == identity(after)
        PINS[path] = {'path':str(path),'bytes':count,'sha256':h.hexdigest()}
    actual = PINS[path]
    if expected:
        assert actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256'], str(path)
    return actual

def raw(path, expected_sha=None):
    path = Path(path); actual = pin(path)
    assert actual['bytes'] <= 1048576
    if path not in DATA:
        value = path.read_bytes()
        assert len(value) == actual['bytes'] and sha(value) == actual['sha256']
        DATA[path] = value
    if expected_sha: assert actual['sha256'] == expected_sha
    return DATA[path]

def load(path, expected_sha=None):
    def pairs(items):
        result = {}
        for key,value in items: assert key not in result; result[key]=value
        return result
    return json.loads(raw(path,expected_sha),object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))

def member_check(folder, packet):
    assert len(packet['members']) == packet['member_count'] and len({x['path'] for x in packet['members']}) == packet['member_count']
    assert sha(canonical(packet['members'])) == packet['tree_sha256']
    if 'member_bytes' in packet: assert sum(x['bytes'] for x in packet['members']) == packet['member_bytes']
    for item in packet['members']:
        assert not Path(item['path']).is_absolute() and all(part not in ('','.','..') for part in item['path'].split('/'))
        pin(folder/item['path'],item)

def save(name,value):
    with (D/name).open('x') as stream: json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')

packet = load(LANE/'seal.json','550f6e81fd3abcd5ad74999d953638d99f426f710d48369792922801f753430d')
member_check(LANE,packet)
assert packet['member_count']==12 and packet['tree_sha256']=='f35f490074a705a8956f9684598515fad8fc386d9896fdbaa52c7345c99e305a'
plan = load(LANE/'plan.json','3534a9d4bc5428335b3dec4cc295f0b55b1a8ea1c778e265fabdcb9fefb6743e')
controller = raw(LANE/'run-capture.py','1c8036e0dcd5e173c2e379ee6e711c06644638f6fb2caad312c4d41f29ddd98f').decode()
policy = load(LANE/'diagnostic-policy.json','707991556c4b7f023010a87ec47d85724daca83a1a891833d03b11fb40e8d879')
base_path = ROOT/plan['base_capture_plan']['path'];pin(base_path,plan['base_capture_plan'])
base = load(base_path,'bed9476b169810452ac0932605784125365f57c897d1e3bf74cd9eaa6ebb8184')
fields=('argv','environment','cwd','bounds','source_directory','source_tree_sha256','source_manifest','compiler','toolchain_manifest','SDK_manifest')
for field in fields: assert canonical(base[field])==canonical(plan[field]),field
assert sha(canonical(plan['argv']))=='4022ae1057439fe5ae31d18675a884b2dc3e56f317a8ddced08bfb163a410aaa'
assert plan['controller_argv']==[plan['python_tool']['path'],'-B',str(LANE/'run-capture.py')]
assert plan['source_tree_sha256']=='91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f'
assert plan['controller_environment']=={'LANG':'C','LC_ALL':'C','PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0','TMPDIR':plan['environment']['TMPDIR'],'TZ':'UTC','__CF_USER_TEXT_ENCODING':'0x1F5:0x0:0x0'}
assert len(plan['environment'])==8
assert plan['bounds']=={'automatic_retries':0,'compiler_invocations':1,'formatter_or_version_queries':0,'maximum_generated_members':64,'maximum_generated_total_bytes':268435456,'maximum_stderr_bytes':2097152,'maximum_stdout_bytes':1048576,'owned_cleanup_deadline_seconds':49,'posthash_deadline_seconds':53.5,'wall_seconds':55,'work_deadline_seconds':44}
assert plan['owned_output_directory']==str(ROOT/'verification/swift-root-bound-dispatch-physical-plan/command')
assert plan['environment']['TMPDIR']==plan['owned_output_directory']+'/tmp'
assert not os.path.lexists(plan['owned_output_directory']) and not os.path.lexists(LANE/'runtime')
assert not os.path.lexists(ROOT/plan['root_release_required']['path'])
manifest=load(LANE/'input-manifest.json')
assert manifest['original_source_members']==146 and manifest['compiler_sysroot_members']==67 and len(manifest['inputs'])<=384
for item in manifest['inputs']:
    path=Path(item['path']);pin(path if path.is_absolute() else ROOT/path,item)
source_path=ROOT/plan['source_manifest']['path'];pin(source_path,plan['source_manifest'])
source=load(source_path)
assert len(source['members'])==source['member_count']==146 and sha(canonical(source['members']))==source['tree_sha256']==plan['source_tree_sha256']
source_rows={x['path']:x for x in source['members']};assert len(source_rows)==146
for item in source['members']:pin(Path(plan['source_directory'])/item['path'],item)
tool_path=ROOT/plan['toolchain_manifest']['path'];pin(tool_path,plan['toolchain_manifest'])
tools=load(tool_path)
assert len(tools['members'])==67 and sha(canonical(tools['members']))==tools['tree_sha256']
for item in tools['members']:pin(Path(tools['root'])/item['path'],item)
pin(Path(plan['compiler']['path']),plan['compiler']);pin(Path(plan['python_tool']['path']),plan['python_tool'])
sdk_path=ROOT/plan['SDK_manifest']['path'];pin(sdk_path,plan['SDK_manifest']);sdk=load(sdk_path)
assert str(Path(sdk['requested']).resolve(strict=True))==sdk['resolved']
for item in sdk['settings']:pin(Path(item['path']),item)
assert plan['host_binary_invocations']==plan['layout_query_invocations']==plan['linker_invocations']==plan['model_test_invocations']==0
assert plan['source_edits']==0 and plan['emit_only']==['LLVM IR','assembly']
assert sum(arg.startswith('--emit=') for arg in plan['argv'])==1 and '--error-format=json' in plan['argv']
assert not any('link=' in arg or 'link-dead-code' in arg or 'always-encode-mir' in arg for arg in plan['argv'])
reference_path=ROOT/plan['reference_controller']['path'];pin(reference_path,plan['reference_controller']);reference=raw(reference_path).decode()
delta=''.join(difflib.unified_diff(reference.splitlines(keepends=True),controller.splitlines(keepends=True),fromfile='reviewed-runner2/run-synthetic16.py',tofile='capture-v1/run-capture.py'))
assert delta==raw(LANE/'controller-delta.patch').decode()
# Whole-warning rebinding is reconstructed from already-frozen classification metadata.
classifier_path=ROOT/'verification/swift-root-bound-layout-warning-classification/warning-source-bindings.json'
classifier=load(classifier_path)
provenance=load(LANE/'diagnostic-policy-provenance.json')
pin(classifier_path,provenance['baseline_classifier'])
assert classifier['original_source_tree_sha256']==source['tree_sha256']
assert len(classifier['warnings'])==len(provenance['warning_records'])==3
assert len(policy['records'])==4 and policy['source_tree']==source['tree_sha256']
span_count=0;bindings_checked=[]
def location(value,offset):
    prefix=value[:offset];return prefix.count(b'\n')+1,len(prefix.rsplit(b'\n',1)[-1].decode())+1
def spans(record):
    result=list(record['spans'])
    for child in record['children']:result+=spans(child)
    return result
for old,new,proof in zip(classifier['warnings'],policy['records'][:3],provenance['warning_records']):
    assert old['classification']==proof['classification']=='preexisting-accepted-IR02-source-warning'
    assert old['original_production_MIR_warning_observed'] is True
    assert new['level']=='warning' and old['exact_record']['level']=='warning'
    assert sha(canonical(old['exact_record']))==proof['source_record_sha256_canonical_JSON']
    assert sha(canonical(new))==proof['source146_record_sha256_canonical_JSON']
    assert old['record_line_sha256_including_newline']==proof['historical_raw_line_sha256_including_newline']
    reconstructed=copy.deepcopy(old['exact_record']);expected_spans=[];path_map={};line_map={}
    for entry in spans(reconstructed):
        matches=[item for item in old['source_binding'] if item['diagnostic_span']==entry]
        assert matches and all(item['original_byte_start']==matches[0]['original_byte_start'] and item['original_byte_end']==matches[0]['original_byte_end'] for item in matches)
        binding=matches[0];assert binding['intersects_three_edit_delta'] is False
        name=binding['relative_source_path'];path=Path(plan['source_directory'])/name;value=raw(path)
        assert pin(path)['sha256']==binding['original_member_sha256']==source_rows[name]['sha256']
        first,last=binding['original_byte_start'],binding['original_byte_end']
        assert value[first:last].decode()==binding['unchanged_bytes_utf8']
        start_line,start_column=location(value,first);end_line,end_column=location(value,last)
        assert (start_line,start_column)==(binding['original_line_start'],binding['original_column_start'])
        assert start_column==entry['column_start'] and end_column==entry['column_end']
        assert [x['text'] for x in entry['text']]==value.decode().splitlines()[start_line-1:end_line]
        old_span=copy.deepcopy(entry);path_map[entry['file_name']]=str(path)
        for number in range(entry['line_start'],entry['line_end']+1):
            replacement=number-entry['line_start']+start_line
            assert number not in line_map or line_map[number]==replacement
            line_map[number]=replacement
        entry.update(file_name=str(path),byte_start=first,byte_end=last,line_start=start_line,line_end=end_line,column_start=start_column,column_end=end_column)
        expected_spans.append({'old_span':old_span,'source146_span':copy.deepcopy(entry),'source146_member':source_rows[name]})
        span_count+=1
    rendered=reconstructed['rendered']
    for before,after in path_map.items():
        for number,replacement in line_map.items():rendered=rendered.replace(before+':'+str(number)+':',after+':'+str(replacement)+':')
        rendered=rendered.replace(before,after)
    adjusted=[]
    for line in rendered.splitlines(keepends=True):
        match=re.match(r'^( *)([0-9]+)( [|+-])',line)
        if match and int(match.group(2)) in line_map:
            number=str(line_map[int(match.group(2))]);line=line[:len(match.group(1))]+number+line[match.end(2):]
        adjusted.append(line)
    reconstructed['rendered']=''.join(adjusted)
    assert reconstructed==new
    assert Counter(canonical(item) for item in expected_spans)==Counter(canonical(item) for item in proof['span_reverse_bindings'])
    bindings_checked.append({'id':old['warning_id'],'record_sha256':sha(canonical(new)),'spans':len(expected_spans)})
summary={'$message_type':'diagnostic','children':[],'code':None,'level':'warning','message':'3 warnings emitted','rendered':'warning: 3 warnings emitted\n\n','spans':[]}
assert policy['records'][3]==provenance['success_summary']==summary
assert provenance['original_saved_raw_stderr_read_or_parsed_during_preparation'] is False and provenance['retrospective_original_rejection_changed'] is False
frontier_path=ROOT/plan['frontier']['path'];pin(frontier_path,plan['frontier']);frontier=load(frontier_path)
assert [x['id'] for x in frontier['targets']]==['Caller','Closure','Dispatch','Body']
assert plan['frontier_complete'] is False and plan['raw_capture_only'] is True and plan['complete_capacity_accepted'] is False
assert plan['root_release_required']['semantic_map_approved'] is plan['root_release_required']['actual_verifier_input_run_released'] is False
# These checks support the manual complete source review; they do not parse its syntax.
checks={
 'one_launch_site':controller.count('child = OwnedPopen(')==1 and controller.count('buffers = command(plan)')==1,
 'record_before_custody':controller.index('OWNED.append(record)')<controller.index('pgid=call(record'),
 'no_implicit_destructor_poll':'class OwnedPopen(subprocess.Popen):\n    def __del__(self):' in controller and not re.search(r'\.poll\(|communicate\(',controller),
 'sticky_permission':all(x in controller for x in ['error.errno in (errno.EPERM, errno.EACCES)','record["permission_refusal"] = True','if record.get("permission_refusal") or record.get("custody_uncertain"):']),
 'exact_wnowait':'os.waitid(os.P_PID, record["pid"], os.WEXITED | os.WNOHANG | os.WNOWAIT)' in controller,
 'completed_no_signals':'"Popen.wait only after WNOWAIT completion proof"' in controller and '"completed-child-no-signals"' in controller,
 'live_metadata_bound':'generated_inventory(44, hash_files=False, live=True)' in controller,
 'bounded_inventory_before_hash':controller.index('count <= 64')<controller.index('if hash_files:') and controller.index('size <= 268435456')<controller.index('if hash_files:'),
 'preserve_after_owned_closure':'if created_build and closed:\n                outcome["generated"], outcome["retained_generated_files"] = preserve_generated(49)' in controller,
 'actual_chunk_retention':'reader.read(min(262144, row["bytes"] - count + 1))' in controller and controller.index('require(count + len(chunk) <= row["bytes"]')<controller.index('writer.write(chunk)'),
 'reinventory_before_remove':'require(before == after, "generated files changed across retention")' in controller,
 'required_artifacts':'required = {"generated/dispatch.ll", "generated/dispatch.s"}' in controller,
 'stream_caps':'cap = 1048576 if key.data == "stdout" else 2097152' in controller,
 'exact_policy_memory':'duplicate diagnostic key' in controller and 'parse_constant=lambda value:' in controller and 'json.dumps(policy["records"], sort_keys=True, separators=(",", ":"))' in controller,
 'prepost_pins':'outcome["pins_before"] = verify_pins(44)' in controller and 'outcome["pins_after"] = verify_pins(53.5)' in controller,
 'unknown_tree_preserved':'outcome["generated_inventory_deferred_for_uncertain_closure"] = created_build' in controller,
 'retained_source_identity':'(root_info.st_dev, root_info.st_ino) == BUILD_IDENTITY' in controller,
 'signal_cap':'if len(SEEN) < 64:' in controller and 'not SIGNAL_OVERFLOW' in controller,
 'frontier_unresolved':'"mapping": "unresolved"' in controller and '"frontier_complete": False' in controller,
 'no_actual_verifier':not re.search(r'^import region_certificate|^from region_certificate',controller,re.M),
 'no_command_retries':'"signal before command or attempted retry"' in controller,
 'no_global_inventory':not any(x in controller for x in ['pgrep','psutil','killall','/bin/ps','/usr/bin/ps']),
}
assert all(checks.values()),[key for key,value in checks.items() if not value]
tail=controller[controller.index('        save("capture-observation.json", capture_observation)'):]
assert tail.index('save("observations.json"')<tail.index('observations_sha = digest(')<tail.index('capture_observation_sha = digest(')<tail.index('signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)')<tail.index('cutoff = time.monotonic() - START')<tail.index('signal.sigpending()')<tail.index('save("receipt.json"')
assert tail.count('digest(')==2 and tail.count('verify_pins(')==0
retention=plan['retained_evidence_bounds']
assert retention['maximum_generated_copy_bytes']+retention['maximum_stream_bytes']+retention['maximum_JSON_bytes_each']*retention['maximum_JSON_files']==retention['maximum_total_retained_bytes']==279969792
assert 64+1+2+3<=retention['maximum_retained_members']==80
assert controller.count('save("')==3
save('warning-bindings.json',{'warning_records':bindings_checked,'nested_spans':span_count,'summary':summary,'prospective_summary_not_observed':True,'previous_raw_stderr_reads_or_parses':0})
before=sorted(PINS.values(),key=lambda item:item['path']);saved=dict(PINS);PINS.clear()
for path,expected in saved.items():pin(path,expected)
after=sorted(PINS.values(),key=lambda item:item['path']);assert before==after
save('checked-inputs.json',{'before':before,'after':after,'equal':True,'tree_sha256':sha(canonical(before))})
result={
 'schema':1,'status':'FROZEN_INDEPENDENT_CAPTURE_CONTROLLER_SOURCE_REVIEW_SINGLE_COMPILER_RELEASE_RECOMMENDED',
 'at':datetime.now(timezone.utc).isoformat(),'findings':[],'compiler_release_recommended':True,
 'command':[str(Path(sys.executable).resolve()),'-B',str(Path(__file__).resolve())],
 'review_script_sha256':sha(Path(__file__).read_bytes()),'python':sys.version,
 'elapsed_seconds':time.monotonic()-START,'checked_input_members':len(before),'before_after_custody_equal':True,
 'producer_seal_sha256':pin(LANE/'seal.json')['sha256'],'producer_members_verified':12,'producer_tree_sha256':packet['tree_sha256'],
 'base_capture_plan_sha256':pin(base_path)['sha256'],'controller_plan_sha256':pin(LANE/'plan.json')['sha256'],
 'controller_sha256':pin(LANE/'run-capture.py')['sha256'],'diagnostic_policy_sha256':pin(LANE/'diagnostic-policy.json')['sha256'],
 'unchanged_argv_sha256':sha(canonical(plan['argv'])),'source146_tree_sha256':source['tree_sha256'],
 'source_members_verified':146,'compiler_sysroot_members_verified':67,'SDK_scope':'Pinned path and two settings files only;not full SDK implementation qualification.',
 'independently_rebound_warning_records':3,'warning_nested_spans':span_count,'prospective_literal_success_summary_objects':1,
 'controller_text_checks':checks,'complete_delta_reconstructed':True,
 'recommendation':'Root may release exactly one frozen compiler capture under this controller and plan,with explicit original output reservation and exact external source-review seal/subject. No retry,version/link/run/test/query,actual-input verifier or semantic-map approval. Any failure or unknown custody remains failed;missing actual targets cannot justify a fallback compile.',
 'accepted_boundary':'Source-only preparation. Future successful raw capture accepts only bounded IR/assembly/stream custody for this exact unchanged-source build;all four target mappings remain unresolved.',
 'limits':[
  'No target module/controller import,syntax check,compiler,capture,tests,model,version query,actual saved-input parse or process probe was performed.',
  'Prospective summary shape has no observation for this future command;any mismatch refuses without adaptation.',
  'Generated/stream limits are periodically checked observations and bounded copies,not a kernel sandbox or guarantee against transient overshoot or writes elsewhere.',
  'On unknown ownership or uncertain generated-tree custody,artifacts are preserved. Complete bounded copies may permit command-tree cleanup before later pin/posthash failure;such failure cannot pass.',
  'The narrow capture-observation has prospective fixed status;capture_complete/bounds flags and the final root receipt must all be checked. Only final receipt can accept capture after the finite signal cutoff.',
  'No frontier mapping,physical union,transitive/destruction/backing bound,numeric work price,grant,root funding,product integration or GA is accepted.'
 ],
 'this_review_candidate_import_syntax_compiler_capture_tests_actual_parser_runtime_or_process_probe_actions':0,
 'canonical_product_metadata_commit_push_actions':0,'raw_capture_only':True,'frontier_complete':False,
 'all_results_local_geometry_only':True,'complete_capacity_accepted':False,
 'physical_capacity_prices_backings_root_funding_product_GA_accepted':False
}
assert time.monotonic()-START<55
save('review-result.json',result)
print(json.dumps({'status':result['status'],'checked_inputs':len(before),'source':146,'tools':67,'warning_spans':span_count,'elapsed_seconds':result['elapsed_seconds']}))
