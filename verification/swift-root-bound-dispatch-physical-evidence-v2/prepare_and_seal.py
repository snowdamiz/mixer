#!/usr/bin/env python3
"""Hash source text and freeze a proposed command; import no selected module."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json
import sys
import time

D=Path(__file__).resolve().parent
R=D.parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def row(path,base=R):
    assert path.is_file() and not path.is_symlink()
    raw=path.read_bytes()
    return {'path':path.relative_to(base).as_posix() if path.is_relative_to(base) else str(path),'bytes':len(raw),'sha256':sha(raw)}
def put(name,value):
    with (D/name).open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')
def sealed(relative,expected):
    path=R/relative;assert row(path)['sha256']==expected
    seal=json.loads(path.read_bytes());members=seal['members']
    assert len(members)==seal['member_count'] and sha(canonical(members))==seal['tree_sha256']
    for item in members:assert row(path.parent/item['path'],path.parent)==item
    return [path]+[path.parent/item['path'] for item in members]
def main():
    start=time.monotonic();assert not (D/'seal.json').exists() and not (D/'command').exists()
    selection=R/'verification/swift-semantic-adapter-root-review/dispatch-physical-verifier-selection.json'
    assert row(selection)['sha256']=='882b61f235ce51551f644958d3ac29382e6e71d1482a5d745f25b08b7e776f34'
    chosen=json.loads(selection.read_bytes());assert chosen['runtime_capture_actual_saved_input_parse_released'] is False
    old=R/'verification/swift-root-bound-dispatch-physical-evidence-v1'
    frozen=sealed('verification/swift-root-bound-dispatch-physical-evidence-v1/seal.json','674fcb6b158055b207c8f2afd1e66e56f06910ec80229f706cab3e29c679e474')
    frozen+=sealed('verification/swift-root-bound-dispatch-physical-evidence-independent/seal.json','6dcf38a8030b3639d87b08a5aacec51a9aee5a45cb25a36d9cbd7d4e280106d4')
    frozen+=sealed('verification/swift-root-bound-dispatch-physical-plan/seal.json','dae114f54519f570e009db7eda8308f96008305eb9d4cfd102ae6e69f10998db')
    frozen+=sealed('verification/swift-root-bound-dispatch-physical-plan-independent/seal.json','c56dc0fd93cde7ebb1ca603fb8c34bb75b921a3d1a4e6473ba384b229032c77f')
    expected_sources=[D/'source/region_certificate.py',D/'source/tests_region_certificate.py']
    assert sorted(p.name for p in (D/'source').iterdir())==sorted(p.name for p in expected_sources)
    sources=[row(path) for path in expected_sources]
    delta=''.join(''.join(difflib.unified_diff((old/'source'/path.name).read_text().splitlines(keepends=True),
        path.read_text().splitlines(keepends=True),fromfile='immutable-v1/source/'+path.name,tofile='v2/source/'+path.name)) for path in expected_sources)
    (D/'source-delta.patch').write_text(delta)
    names=[]
    for line in expected_sources[1].read_text().splitlines():
        stripped=line.strip()
        if stripped.startswith('def test_p'):names.append(stripped.split('(',1)[0][4:])
    assert len(names)==16 and len(set(names))==16 and [name[:8] for name in names]==[f'test_p{i:02}' for i in range(1,17)]
    # This inventory does not parse, import, compile, discover or execute tests.
    put('test-family-map.json',{'schema':1,'status':'TEXTUAL_DECLARATIONS_ONLY_NOT_IMPORTED_OR_EXECUTED',
        'families':[{'family':f'P{i:02}','test_method':name,'executed':False} for i,name in enumerate(names,1)],
        'R01_added_subcases':{'P09':['unknown/unreviewed/weak physical base facts','malformed and contradictory residues','stronger alignment requires independent support','numerical rebase does not move physical start'],
            'P10':['same-base delta-1/+1 contradictions','consistent delta0/8','known congruence propagates through reviewed delta','region requirements never mint absent evidence']},
        'fixture_scope':'Independently authored synthetic byte strings/records and private synthetic regular-file/symlink cases only; no actual compiler artifact.',
        'source_syntax_or_test_success_claimed':False,'all_synthetic_results_local_geometry_only':True,'complete_capacity_accepted':False})
    python=Path(sys.executable).resolve();python_pin=row(python)
    output=D/'command';argv=[str(python),'-B',str(expected_sources[1])]
    environment={'LANG':'C','LC_ALL':'C','PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0','TMPDIR':str(output/'tmp'),'TZ':'UTC'}
    put('host-test-plan.json',{'schema':1,'status':'FROZEN_SOURCE_PREPARATION_AWAITING_INDEPENDENT_SOURCE_REVIEW_AND_ROOT_TEST_RELEASE',
        'source_version':2,'correction':'R01 symbolic physical-base alignment congruences;coordinate rebasing supplies no alignment evidence',
        'original_packet':row(old/'seal.json'),'independent_R01_review':row(R/'verification/swift-root-bound-dispatch-physical-evidence-independent/seal.json'),
        'source_delta':row(D/'source-delta.patch'),
        'selection':row(selection),'source_files':sources,'python_tool':python_pin,'python_version_from_this_preparation':sys.version,
        'argv':argv,'argv_sha256_canonical_JSON':sha(canonical(argv)),'environment':environment,'cwd':str(R),
        'dependencies':'Python3.14 standard library only; no external package or product module',
        'invocation_scope':'Only sixteen synthetic unittest methods. The selected module is imported only by that future test process; no actual saved-input verification.',
        'bounds':{'wall_seconds':55,'test_deadline_seconds':44,'owned_cleanup_deadline_seconds':49,'posthash_deadline_seconds':53.5,
            'python_test_invocations':1,'automatic_retries':0,'compiler_capture_model_layout_version_formatter_invocations':0,
            'maximum_stdout_bytes':262144,'maximum_stderr_bytes':524288,'maximum_generated_members':64,'maximum_generated_bytes':16777216},
        'owned_outputs':{'directory':str(output),'temporary_directory':str(output/'tmp'),'must_be_absent_prelaunch':True,
            'root_precreates_fresh_directory_and_tmp_only':True,'synthetic_filesystem_test_uses_private_temporary_subdirectory':True,
            'no_preexisting_files_overwritten':True,'global_process_inventory_forbidden':True},
        'required_terminal_evidence':['Exact argv/full environment/cwd,Python identity and source/input pins before and after',
            'Full bounded stdout/stderr,exit and exactly16 distinct executed tests matching the frozen roster;none failed/skipped/expected-failure/unexpected-success',
            'No unexpected warning/traceback outside standard unittest output; failure or unrun stage is not a pass',
            'Root-owned exact child/group custody,completion,reap and absence;no global inventories',
            'Bounded owned-file inventory and cleanup after closure;preserve ambiguity;no bytecode files or external artifacts',
            'All hashes and observation before reviewed one-way signal cutoff;observation before final receipt;no retry'],
        'root_release_required':{'path':'verification/swift-semantic-adapter-root-review/dispatch-physical-verifier-v2-host-release.json',
            'exact_plan_sha256':True,'independent_source_review_seal_required':True,'python_test_lane_released':True,'python_test_invocations':1,'automatic_retries':0},
        'execution_so_far':{'selected_module_imports':0,'syntax_checks':0,'tests':0,'actual_saved_input_parses':0,'compiler_capture_model_layout_runtime':0},
        'all_results_local_geometry_only':True,'complete_capacity_accepted':False,'prices_backing_bounds_root_durability_product_GA_accepted':False})
    inputs=[selection]+frozen
    before=[row(path) for path in inputs]
    put('input-manifest.json',{'schema':1,'inputs':before,'source_files':sources,'selected_sources':2,'prospective_families':16,
        'source_version':2,'original_v1_packet_and_R01_review_verified_unchanged':True,'source_delta':row(D/'source-delta.patch'),
        'source146_binding':'91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f',
        'capture_plan_sha256':'bed9476b169810452ac0932605784125365f57c897d1e3bf74cd9eaa6ebb8184',
        'future_actual_inputs_and_trusted_approval_do_not_exist_in_this_packet':True,
        'canonical_policy_or_metadata_changed':False})
    assert [row(path) for path in inputs]==before and [row(path) for path in expected_sources]==sources
    summary={'status':'SOURCE_PREPARED_UNEXECUTED','selected_sources':2,'declared_synthetic_control_methods':16,
        'selected_module_imports_syntax_checks_tests_actual_input_parses':0,'all_results_local_geometry_only':True,'complete_capacity_accepted':False}
    (D/'preparation.stdout').write_text(json.dumps(summary,sort_keys=True)+'\n');(D/'preparation.stderr').write_bytes(b'')
    assert time.monotonic()-start<55
    put('preparation-receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command':[str(python),'-B',str(Path(__file__).resolve())],'cwd':str(R),'python':sys.version,'python_tool':python_pin,
        'preparation_source':row(Path(__file__).resolve()),'source_files':sources,'host_test_plan':row(D/'host-test-plan.json'),
        'input_manifest':row(D/'input-manifest.json'),'stdout':row(D/'preparation.stdout'),'stderr':row(D/'preparation.stderr'),
        'elapsed_seconds':time.monotonic()-start,'wall_ceiling_seconds':55,
        'scope':'Source writing/manual review,immutable input hashing and textual method inventory only. No selected-module import,syntax check or execution.',
        'tests_actual_saved_input_parser_compiler_capture_model_layout_native_UI_device_network_global_process_queries':0,'prior_frozen_packets_unchanged':True})
    members=[row(path,D) for path in sorted(D.rglob('*')) if path.is_file() and path.name!='seal.json']
    seal={'schema':1,'status':'FROZEN_TWO_FILE_OFFLINE_REGION_VERIFIER_SOURCE_AWAITING_INDEPENDENT_REVIEW','members':members,'member_count':len(members),
        'source_version':2,'correction':'R01 physical alignment congruence propagation',
        'member_bytes':sum(item['bytes'] for item in members),'tree_sha256':sha(canonical(members)),'host_test_plan_sha256':sha((D/'host-test-plan.json').read_bytes()),
        'selected_sources':2,'synthetic_control_methods':16,'module_import_syntax_test_actual_input_or_compiler_execution':0,
        'all_results_local_geometry_only':True,'complete_capacity_accepted':False,'canonical_policy_or_metadata_changed':False}
    put('seal.json',seal)
    print(json.dumps({'status':seal['status'],'members':len(members),'seal_sha256':sha((D/'seal.json').read_bytes()),
        'tree_sha256':seal['tree_sha256'],'host_test_plan_sha256':seal['host_test_plan_sha256'],'elapsed_seconds':time.monotonic()-start}))
if __name__=='__main__':main()
