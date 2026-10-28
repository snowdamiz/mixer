#!/usr/bin/env python3
"""Pin two Rust sources and a root-owned host plan. No Rust tools are executed."""
from pathlib import Path
import datetime
import hashlib
import json
import sys
import time

D=Path(__file__).resolve().parent;R=D.parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()
def row(path,base=R):
    assert path.is_file() and not path.is_symlink();digest=hashlib.sha256();size=0
    with path.open('rb') as handle:
        while raw:=handle.read(262144):digest.update(raw);size+=len(raw)
    return {'path':path.relative_to(base).as_posix() if path.is_relative_to(base) else str(path),'bytes':size,'sha256':digest.hexdigest()}
def put(name,obj):
    with (D/name).open('x') as handle:json.dump(obj,handle,indent=2,sort_keys=True);handle.write('\n')
def main():
    start=time.monotonic();assert not (D/'seal.json').exists() and not (D/'command').exists()
    selection=R/'verification/swift-semantic-adapter-root-review/dispatch-region-model-selection.json'
    chosen=json.loads(selection.read_bytes())['selection'];assert chosen['compiler_or_runtime_released'] is False
    query=R/'verification/swift-root-bound-work-storage-layout-probe-v3/plan.json';prior=json.loads(query.read_bytes())
    original=R/'verification/swift-root-bound-work-storage-layout-probe'
    toolmanifest=original/'toolchain-manifest.json';sdkmanifest=original/'sdk-path-settings.json'
    sdk=json.loads(sdkmanifest.read_bytes())
    clang=Path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang').resolve(strict=True)
    ld=Path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/ld').resolve(strict=True)
    compiler=Path(prior['compiler']['path']);actual=row(compiler)
    assert {k:actual[k] for k in ['bytes','sha256']}=={k:prior['compiler'][k] for k in ['bytes','sha256']}
    sources=[row(D/'source/model.rs'),row(D/'source/tests.rs')]
    names=[]
    for line in (D/'source/tests.rs').read_text().splitlines():
        if line.startswith('fn t'):names.append(line.split('(',1)[0][3:])
    assert len(names)==20 and [name[:3] for name in names]==[f't{i:02}' for i in range(1,21)]
    # This is a textual declaration inventory only, not Rust parsing/testing.
    put('test-family-map.json',{'schema':1,'status':'SOURCE_DECLARATIONS_ONLY_NOT_COMPILED_OR_EXECUTED',
        'families':[{'contract_family':f'T{i:02}','rust_test':name,'executed':False} for i,name in enumerate(names,1)],
        'numeric_fixture_scope':'All work/capacity numbers, identities, physical declarations and reviewed-looking labels in tests are hypothetical model inputs;no product grant.'})
    binary=D/'command/model-tests'
    compile_argv=[str(compiler),'--edition=2021','--target','aarch64-apple-darwin','--test',str(D/'source/model.rs'),
        '-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind','-C','linker='+str(clang),'-o',str(binary)]
    host_argv=[str(binary),'--test-threads=1','--nocapture']
    environment={'LANG':'C','LC_ALL':'C','PATH':'/usr/bin:/bin','SDKROOT':sdk['requested'],'TMPDIR':str(D/'command/tmp'),'TZ':'UTC'}
    inputs=[selection,query,toolmanifest,sdkmanifest]
    for key in ['contract_seal','review_seal','implementation_specification']:
        path=R/chosen[key]['path'];assert row(path)['sha256']==chosen[key]['sha256'];inputs.append(path)
    inputs += [R/'verification/swift-root-bound-dispatch-lifetime-contract/CONTRACT.md',R/'verification/swift-root-bound-dispatch-lifetime-contract/events.json',
        R/'verification/swift-root-bound-dispatch-lifetime-contract/regions.json',R/'verification/swift-root-bound-dispatch-lifetime-contract/quote-partitions.json',
        R/'verification/swift-root-bound-dispatch-lifetime-contract/prospective-tests.json',R/'verification/swift-root-bound-dispatch-lifetime-contract-independent/REVIEW.md',
        R/'verification/swift-semantic-adapter-root-review/layout-accounting-join-acceptance.json']
    put('input-manifest.json',{'schema':1,'inputs':[row(p) for p in inputs],'source_files':sources,
        'source146_contract_binding':'91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f',
        'compiler':prior['compiler'],'compiler_version_from_pinned_prior_receipt':prior['toolchain_version'],
        'toolchain_manifest':row(toolmanifest),'linker_driver':row(clang),'link_editor':row(ld),
        'SDK_settings':[row(Path(item['path'])) for item in sdk['settings']],
        'qualification':'Reused immutable tool identities and source contract. No version query, compiler, formatter, test or physical/capacity measurement.'})
    put('host-test-plan.json',{'schema':1,'status':'FROZEN_SOURCE_PREPARATION_AWAITING_ROOT_REVIEW_AND_EXACT_HOST_RELEASE',
        'selection':row(selection),'source_files':sources,'source_stdlib_dependencies':['Rust standard collections/types only;no external crate or product module'],
        'commands':[{'kind':'compile','argv':compile_argv,'expected_exit':0,'execute_only_after_root_release':True},
            {'kind':'host-tests','argv':host_argv,'expected_exit':0,'execute_only_if_compile_exit_zero':True}],
        'execution_mode':'One root-owned serial operation;exact two argv arrays share one55-second cumulative budget. This packet contains no producer runtime driver.',
        'cwd':str(R),'environment':environment,'compiler':prior['compiler'],'compiler_version_from_prior_receipt':prior['toolchain_version'],
        'compiler_manifest':row(toolmanifest),'linker_driver':row(clang),'link_editor':row(ld),'SDK_manifest':row(sdkmanifest),
        'bounds':{'wall_seconds':55,'compile_deadline_seconds':30,'host_test_deadline_seconds':45,'owned_cleanup_deadline_seconds':49,'posthash_deadline_seconds':53.5,
            'compiler_invocations':1,'host_test_invocations':1,'formatter_or_version_invocations':0,'automatic_retries':0,'test_threads':1,
            'maximum_stdout_bytes_per_command':262144,'maximum_stderr_bytes_per_command':524288,'maximum_generated_members':64,'maximum_generated_bytes':33554432},
        'owned_outputs':{'directory':str(D/'command'),'binary':str(binary),'temporary_directory':str(D/'command/tmp'),
            'must_be_absent_prelaunch':True,'new_process_sessions_and_exact_owned_cleanup_required':True,'global_process_inventory_forbidden':True},
        'root_release_required':{'path':'verification/swift-semantic-adapter-root-review/dispatch-region-model-host-release.json',
            'required_fields':{'plan_sha256':'exact digest of this plan','isolated_model_host_lane_released':True,'compiler_invocations':1,'host_test_invocations':1,'automatic_retries':0}},
        'required_terminal_evidence':['Exact source/input/toolchain/linker/SDK hashes before and after','Both exact argv/full environments/cwd/exit/output hashes and truncated-output refusal',
            'Exactly20 executed tests,none ignored,all passing;retain failures without retry','Owned child/group reaped and absent for compiler and test;no global inventories',
            'Hash binary before execution and after;inventory/hash owned generated files and remove only after owned closure;preserve ambiguity','Receipt and evidence before55s;failure or unrun stage never a pass'],
        'execution_so_far':{'compiler':0,'tests':0,'formatter':0,'version_queries':0},
        'all_assessments_model_only':True,'physical_capacity_price_grant_root_funding_full_ownership_native_FieldLog_OTA_GA_accepted':False})
    summary={'two_rust_sources_prepared':True,'declared_test_families':20,'compiler_tests_formatter_version_queries':0,'model_only':True}
    (D/'preparation.stdout').write_text(json.dumps(summary,sort_keys=True)+'\n');(D/'preparation.stderr').write_bytes(b'')
    assert time.monotonic()-start<55
    put('preparation-receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command':[str(Path(sys.executable).resolve()),'-B',str(Path(__file__).resolve())],'cwd':str(R),'python':sys.version,'python_tool':row(Path(sys.executable).resolve()),
        'writer_source':row(Path(__file__).resolve()),'source_files':sources,'host_plan_sha256':sha((D/'host-test-plan.json').read_bytes()),
        'input_manifest':row(D/'input-manifest.json'),'outputs':[row(D/'preparation.stdout'),row(D/'preparation.stderr')],
        'elapsed_seconds':time.monotonic()-start,'wall_ceiling_seconds':55,'compiler_test_formatter_version_commands':0,
        'scope':'Source writing/manual review and pinned input hashing/textual declaration inventory only. Rust syntax,compilation,tests and runtime behavior unverified.',
        'native_UI_capture_phone_network_global_process_inventory':False})
    members=[row(p,D) for p in sorted(D.rglob('*')) if p.is_file() and p.name!='seal.json']
    seal={'schema':1,'status':'FROZEN_TWO_FILE_ISOLATED_DISPATCH_REGION_MODEL_SOURCE_AWAITING_ROOT_HOST_RELEASE','members':members,'member_count':len(members),
        'member_bytes':sum(item['bytes'] for item in members),'tree_sha256':sha(canonical(members)),'host_plan_sha256':sha((D/'host-test-plan.json').read_bytes()),
        'rust_source_files':2,'declared_test_families':20,'compiler_tests_formatter_or_version_commands_executed':0,'all_assessments_model_only':True,
        'canonical_policy_changed':False,'physical_capacity_prices_grants_funding_full_ownership_GA_accepted':False}
    put('seal.json',seal)
    print(json.dumps({'status':seal['status'],'members':len(members),'plan_sha256':seal['host_plan_sha256'],'seal_sha256':sha((D/'seal.json').read_bytes()),
        'tree_sha256':seal['tree_sha256'],'Rust_compiler_tests_formatter_unrun':True}))
if __name__=='__main__':main()
