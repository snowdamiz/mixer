#!/usr/bin/env python3
"""Prepare/pin one prospective capture; never import or run the controller."""
from pathlib import Path
import copy
import datetime
import difflib
import hashlib
import json
import sys
import time

D=Path(__file__).resolve().parent
R=D.parents[1]
BASE=R/'verification/swift-root-bound-dispatch-physical-plan/capture-plan.json'
BASE_SHA='bed9476b169810452ac0932605784125365f57c897d1e3bf74cd9eaa6ebb8184'
ARGV_SHA='4022ae1057439fe5ae31d18675a884b2dc3e56f317a8ddced08bfb163a410aaa'
REFERENCE=R/'verification/swift-physical-verifier-host-runner-2/run-synthetic16.py'
REFERENCE_SHA='57f839f5b7a1c92c889db7738463090286f89766a968a9994b15189adfd71f1a'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def row(path,base=R):
    assert path.is_file() and not path.is_symlink()
    h=hashlib.sha256();size=0
    with path.open('rb') as stream:
        while raw:=stream.read(262144):h.update(raw);size+=len(raw)
    return {'path':path.relative_to(base).as_posix() if path.is_relative_to(base) else str(path),'bytes':size,'sha256':h.hexdigest()}
def put(name,value):
    with (D/name).open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')
def sealed(relative,expected):
    path=R/relative;assert row(path)['sha256']==expected
    value=json.loads(path.read_bytes());members=value['members']
    assert value.get('member_count',len(members))==len(members)
    if 'tree_sha256' in value:assert value['tree_sha256']==sha(canonical(members))
    for member in members:assert row(path.parent/member['path'],path.parent)==member
    return [path]+[path.parent/member['path'] for member in members]
def location(raw,position):
    prefix=raw[:position];return prefix.count(b'\n')+1,len(prefix.rsplit(b'\n',1)[-1].decode('utf-8'))+1
def rebase_warning(warning,source,source_rows):
    record=copy.deepcopy(warning['exact_record']);bindings=warning['source_binding'];index={}
    for binding in bindings:
        key=canonical(binding['diagnostic_span']);index.setdefault(key,[]).append(binding)
    proof=[];rewrites={};old_paths={};stack=[record]
    while stack:
        node=stack.pop()
        for span in node['spans']:
            matches=index[canonical(span)];binding=matches[0]
            for other in matches:assert other['original_byte_start']==binding['original_byte_start'] and other['original_byte_end']==binding['original_byte_end']
            assert binding['intersects_three_edit_delta'] is False and warning['original_production_MIR_warning_observed'] is True
            relative=binding['relative_source_path'];path=source/relative;raw=path.read_bytes()
            assert source_rows[relative]['sha256']==binding['original_member_sha256']==row(path)['sha256']
            begin,end=binding['original_byte_start'],binding['original_byte_end']
            assert raw[begin:end].decode('utf-8')==binding['unchanged_bytes_utf8']
            first,column=location(raw,begin);last,end_column=location(raw,end)
            assert first==binding['original_line_start'] and column==binding['original_column_start']
            assert column==span['column_start'] and end_column==span['column_end']
            lines=raw.splitlines();assert len(span['text'])==last-first+1
            for item,line in zip(span['text'],lines[first-1:last]):assert item['text']==line.decode('utf-8')
            old_path=span['file_name'];new_path=str(path)
            old_paths[old_path]=new_path
            for line in range(span['line_start'],span['line_end']+1):
                new_line=first+line-span['line_start'];assert len(str(line))==len(str(new_line))
                pair=(old_path,line);assert pair not in rewrites or rewrites[pair]==new_line;rewrites[pair]=new_line
            before=copy.deepcopy(span)
            span.update(file_name=new_path,byte_start=begin,byte_end=end,line_start=first,line_end=last,column_start=column,column_end=end_column)
            proof.append({'old_span':before,'source146_span':copy.deepcopy(span),'source146_member':source_rows[relative]})
        stack.extend(node['children'])
    rendered=record['rendered']
    for old_path,new_path in old_paths.items():rendered=rendered.replace(old_path,new_path)
    for (old_path,old_line),new_line in rewrites.items():
        new_path=old_paths[old_path];rendered=rendered.replace(new_path+':'+str(old_line)+':',new_path+':'+str(new_line)+':')
    adjusted=[]
    line_map={old:new for (_path,old),new in rewrites.items()}
    for line in rendered.splitlines(keepends=True):
        indent=len(line)-len(line.lstrip(' '));tail=line[indent:]
        for old,new in line_map.items():
            if any(tail.startswith(str(old)+marker) for marker in (' |',' -',' +')):
                line=line[:indent]+str(new)+tail[len(str(old)):];break
        adjusted.append(line)
    record['rendered']=''.join(adjusted)
    assert all(old not in record['rendered'] for old in old_paths)
    return record,{'warning_id':warning['warning_id'],'classification':warning['classification'],
        'source_record_sha256_canonical_JSON':sha(canonical(warning['exact_record'])),
        'historical_raw_line_sha256_including_newline':warning['record_line_sha256_including_newline'],
        'source146_record_sha256_canonical_JSON':sha(canonical(record)),'span_reverse_bindings':proof,
        'rendered_path_rebindings':old_paths,'rendered_line_rebindings':[{'old_path':p,'old_line':n,'source146_line':v} for (p,n),v in rewrites.items()]}

def main():
    start=time.monotonic();assert not (D/'seal.json').exists() and not (D/'runtime').exists()
    assert row(BASE)['sha256']==BASE_SHA and row(REFERENCE)['sha256']==REFERENCE_SHA
    base=json.loads(BASE.read_bytes());assert sha(canonical(base['argv']))==ARGV_SHA
    build=Path(base['owned_output_directory']);assert not build.exists() and not build.is_symlink()
    assert build==R/'verification/swift-root-bound-dispatch-physical-plan/command' and base['environment']['TMPDIR']==str(build/'tmp')
    frozen=sealed('verification/swift-root-bound-dispatch-physical-plan/seal.json','dae114f54519f570e009db7eda8308f96008305eb9d4cfd102ae6e69f10998db')
    frozen+=sealed('verification/swift-root-bound-dispatch-physical-plan-independent/seal.json','c56dc0fd93cde7ebb1ca603fb8c34bb75b921a3d1a4e6473ba384b229032c77f')
    frozen+=sealed('verification/swift-root-bound-layout-warning-classification/seal.json','39976085aa6fd3cebf5c12bb6376358c46b11223df8347b8fb70ef12c20be5ab')
    source=Path(base['source_directory']);source_manifest=R/base['source_manifest']['path'];source_doc=json.loads(source_manifest.read_bytes())
    assert row(source_manifest)==base['source_manifest'] and source_doc['member_count']==146 and sha(canonical(source_doc['members']))==base['source_tree_sha256']
    source_rows={member['path']:member for member in source_doc['members']};assert len(source_rows)==146
    source_paths=[]
    for name,member in source_rows.items():
        path=source/name;assert row(path,source)==member;source_paths.append(path)
    tool_manifest=R/base['toolchain_manifest']['path'];tools=json.loads(tool_manifest.read_bytes())
    assert row(tool_manifest)==base['toolchain_manifest'] and len(tools['members'])==67 and sha(canonical(tools['members']))==tools['tree_sha256']
    tool_paths=[]
    for member in tools['members']:
        path=Path(tools['root'])/member['path'];assert row(path,Path(tools['root']))==member;tool_paths.append(path)
    assert row(Path(base['compiler']['path']))==base['compiler']
    sdk_path=R/base['SDK_manifest']['path'];sdk=json.loads(sdk_path.read_bytes());assert row(sdk_path)==base['SDK_manifest']
    assert str(Path(sdk['requested']).resolve(strict=True))==sdk['resolved']
    sdk_paths=[Path(item['path']) for item in sdk['settings']]
    for path,item in zip(sdk_paths,sdk['settings']):assert row(path)==item
    warning_path=R/'verification/swift-root-bound-layout-warning-classification/warning-source-bindings.json'
    warnings=json.loads(warning_path.read_bytes())['warnings'];assert len(warnings)==3
    records=[];proofs=[]
    for warning in warnings:
        record,proof=rebase_warning(warning,source,source_rows);records.append(record);proofs.append(proof)
    summary={'$message_type':'diagnostic','message':'3 warnings emitted','code':None,'level':'warning','spans':[],'children':[],
        'rendered':'warning: 3 warnings emitted\n\n'}
    records.append(summary)
    put('diagnostic-policy.json',{'schema':1,'status':'frozen-exact-source-bound-baseline-diagnostics','source_tree':base['source_tree_sha256'],'records':records})
    put('diagnostic-policy-provenance.json',{'schema':1,'baseline_classifier':row(warning_path),'source146_manifest':row(source_manifest),
        'warning_records':proofs,'three_baseline_warnings_remain_warnings':True,'unknown_or_missing_or_extra_record_rejects':True,
        'success_summary':summary,'success_summary_provenance':'Prospective exact JSON success-summary form,with the existing plain-text production-MIR summary as historical provenance;not observed for this new command.',
        'historical_command_metadata':row(R/'verification/swift-root-bound-layout-warning-classification/prior-command-evidence.json'),
        'original_saved_raw_stderr_read_or_parsed_during_preparation':False,'retrospective_original_rejection_changed':False})
    reference_manifest=R/'verification/swift-physical-verifier-host-runner-2/manifest.json'
    reference_plan=R/'verification/swift-physical-verifier-host-runner-2/host-test-plan.json'
    environment_receipt=R/'verification/swift-semantic-adapter-root-review/dispatch-physical-verifier-v2-host-attempt-1.json'
    reference_doc=json.loads(reference_manifest.read_bytes())
    for member in reference_doc['members']:assert row(reference_manifest.parent/member['path'],reference_manifest.parent)==member
    python=Path(sys.executable).resolve();frontier=R/'verification/swift-root-bound-dispatch-physical-plan/target-frontier.json'
    binding={'source_tree':base['source_tree_sha256'],'compiler_commit':'b940084d7eb6a299eb4bfeb8e34901bc051e7ac4','target':'aarch64-apple-darwin',
        'features':['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache'],
        'fixture_cfg':'mixer_bootstrap_one_fixture_v1','opt_level':0,'mir_opt_level':0,'overflow_checks':True,'panic':'unwind','codegen_units':1,'debuginfo':2,
        'capture_plan_sha256':BASE_SHA,'argv_sha256':ARGV_SHA}
    controller_environment={'LANG':'C','LC_ALL':'C','PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0',
        'TMPDIR':str(build/'tmp'),'TZ':'UTC','__CF_USER_TEXT_ENCODING':'0x1F5:0x0:0x0'}
    plan=copy.deepcopy(base)
    plan.update(status='FROZEN_CONTROLLER_SOURCE_PROPOSAL_AWAITING_INDEPENDENT_REVIEW_AND_ROOT_RELEASE',base_capture_plan=row(BASE),
        controller_path=str(D/'run-capture.py'),controller_argv=[str(python),'-B',str(D/'run-capture.py')],
        controller_environment=controller_environment,python_tool=row(python),python_version_from_this_preparation=sys.version,
        controller_environment_provenance={'root_preflight_receipt':row(environment_receipt),'reviewed_runner2_plan':row(reference_plan),
            'compiler_child_environment_unchanged':True,'new_environment_probe':False},
        frontier=row(frontier),verifier_binding=binding,
        ownership_selection='Root direct selection of the original predeclared command/TMPDIR reservation;new lane owns controller and retained evidence only.',
        retained_evidence_bounds={'maximum_generated_copy_bytes':268435456,'maximum_stream_bytes':3145728,
            'maximum_JSON_files':8,'maximum_JSON_bytes_each':1048576,'maximum_retained_members':80,'maximum_total_retained_bytes':279969792},
        reference_controller=row(REFERENCE),raw_capture_only=True,frontier_complete=False,
        all_results_local_geometry_only=True,complete_capacity_accepted=False)
    plan['root_release_required']={'path':str((R/'verification/swift-semantic-adapter-root-review/dispatch-physical-capture-release.json').relative_to(R)),
        'compiler_lane_released':True,'compiler_invocations':1,'automatic_retries':0,'reserved_output_authorized':True,
        'exact_base_capture_plan_controller_plan_packet_controller_and_independent_review_pins':True,
        'semantic_map_approved':False,'actual_verifier_input_run_released':False}
    for key in ('argv','environment','cwd','bounds','source_directory','source_tree_sha256','source_manifest','compiler','toolchain_manifest','SDK_manifest'):
        assert canonical(plan[key])==canonical(base[key])
    assert sha(canonical(plan['argv']))==ARGV_SHA
    put('plan.json',plan);plan_sha=sha((D/'plan.json').read_bytes())
    controller=D/'run-capture.py';text=controller.read_text();assert text.count('PREPARED_PLAN_SHA256')==1
    controller.write_text(text.replace('PREPARED_PLAN_SHA256',plan_sha))
    delta=''.join(difflib.unified_diff(REFERENCE.read_text().splitlines(keepends=True),controller.read_text().splitlines(keepends=True),
        fromfile='reviewed-runner2/run-synthetic16.py',tofile='capture-v1/run-capture.py'))
    (D/'controller-delta.patch').write_text(delta)
    put('release-schema.json',{'schema':1,'path':plan['root_release_required']['path'],'required_fields':{
        'schema':1,'compiler_lane_released':True,'compiler_invocations':1,'automatic_retries':0,'reserved_output_authorized':True,
        'base_capture_plan_sha256':BASE_SHA,'controller_plan_sha256':plan_sha,'argv_sha256':ARGV_SHA,
        'controller_sha256':row(controller)['sha256'],'capture_packet_seal_sha256':'exact seal.json SHA,filled by root after freeze',
        'independent_source_review_accepted':True,'independent_source_review':{'path':'root-selected verification/.../seal.json','bytes':'exact bytes','sha256':'exact SHA'},
        'independent_source_review_subject':{'base_capture_plan_sha256':BASE_SHA,'controller_plan_sha256':plan_sha,'controller_sha256':row(controller)['sha256'],
            'capture_packet_seal_sha256':'same exact capture seal SHA'},'semantic_map_approved':False,'actual_verifier_input_run_released':False},
        'preparation_does_not_supply_or_authorize_this_release':True})
    inputs=[BASE,source_manifest,tool_manifest,sdk_path,frontier,REFERENCE,reference_manifest,reference_plan,environment_receipt]+frozen+source_paths+tool_paths+sdk_paths
    inputs += [reference_manifest.parent/member['path'] for member in reference_doc['members']]
    inputs=list(dict.fromkeys(inputs));assert len(inputs)<=384
    before=[row(path) for path in inputs]
    put('input-manifest.json',{'schema':1,'inputs':before,'original_source_members':146,'compiler_sysroot_members':67,
        'source_tree_sha256':base['source_tree_sha256'],'base_capture_plan_sha256':BASE_SHA,'unchanged_argv_sha256':ARGV_SHA,
        'reference_controller_sha256':REFERENCE_SHA,'preparation_imports_controller_or_verifier':False,
        'original_raw_stderr_or_actual_capture_artifacts_parsed':False})
    assert [row(path) for path in inputs]==before
    summary_out={'status':'SOURCE_ONLY_CAPTURE_CONTROLLER_PREPARED','compiler_controller_dummy_test_version_runtime_invocations':0,
        'argv_sha256_unchanged':ARGV_SHA,'source_members':146,'tool_members':67,'frontier_complete':False,'complete_capacity_accepted':False}
    (D/'preparation.stdout').write_text(json.dumps(summary_out,sort_keys=True)+'\n');(D/'preparation.stderr').write_bytes(b'')
    assert time.monotonic()-start<55
    put('preparation-receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command':[str(python),'-B',str(Path(__file__).resolve())],'cwd':str(R),'python':sys.version,'python_tool':row(python),
        'preparation_source':row(Path(__file__).resolve()),'controller_source':row(controller),'controller_plan':row(D/'plan.json'),
        'input_manifest':row(D/'input-manifest.json'),'stdout':row(D/'preparation.stdout'),'stderr':row(D/'preparation.stderr'),
        'elapsed_seconds':time.monotonic()-start,'wall_ceiling_seconds':55,
        'scope':'Source writing/manual review,pinned metadata warning rebinding and immutable-file hashing only;no controller import/syntax check/command or raw-input parser.',
        'compiler_capture_version_model_test_native_runtime_actual_saved_input_process_probes':0,'prior_frozen_packets_and_canonical_metadata_changed':False})
    members=[row(path,D) for path in sorted(D.rglob('*')) if path.is_file() and path.name!='seal.json']
    seal={'schema':1,'status':'FROZEN_ONE_SHOT_COMPILER_CAPTURE_CONTROLLER_SOURCE_AWAITING_REVIEW','members':members,'member_count':len(members),
        'member_bytes':sum(value['bytes'] for value in members),'tree_sha256':sha(canonical(members)),
        'base_capture_plan_sha256':BASE_SHA,'controller_plan_sha256':plan_sha,'controller_sha256':row(controller)['sha256'],
        'unchanged_argv_sha256':ARGV_SHA,'compiler_controller_import_syntax_test_dummy_or_process_probes':0,
        'raw_capture_only':True,'frontier_complete':False,'complete_capacity_accepted':False,'canonical_or_global_metadata_changed':False}
    put('seal.json',seal)
    print(json.dumps({'status':seal['status'],'members':len(members),'seal_sha256':sha((D/'seal.json').read_bytes()),
        'controller_plan_sha256':plan_sha,'controller_sha256':seal['controller_sha256'],'tree_sha256':seal['tree_sha256'],'elapsed_seconds':time.monotonic()-start}))
if __name__=='__main__':main()
