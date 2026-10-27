"""Offline replay of the bounded independent review; never invokes rustc/tests."""
from pathlib import Path
import gzip
import json
import sys
sys.dont_write_bytecode = True
from review import (HERE, ROOT, P, ACCOUNT, PROFILE, KEYS, TREE, HOST_TREE,
    inputs, testing_source, read, row, roster, sha, canonical, packed, packed_env, identity, write)

def output(folder, name):
    path = folder/name
    return path.read_bytes() if path.exists() else gzip.decompress((folder/(name+'.gz')).read_bytes())

def main():
    source, hosts, custody = inputs()
    assert custody == read(HERE/'input-custody.json')
    compiled = []
    history = []
    available_tools = [HERE/'review.py'] + sorted((HERE/'attempts').glob('*/review-at-start.py'))
    for folder in sorted((HERE/'preimages').iterdir()):
        mode = folder.name
        manifest_data = (folder/'manifest.json').read_bytes()
        manifest = json.loads(manifest_data)
        rec = read(HERE/'commands'/mode/'receipt.json')
        binding = read(folder/'binding.json')
        assert packed(rec['argv']) == (folder/'argv.bin').read_bytes()
        assert packed_env({k:v for k,v in rec['environment'].items() if k not in KEYS}) == (folder/'environment.bin').read_bytes()
        version = (folder/'compiler-version.txt').read_bytes()
        compiler = manifest['tools']['rustc']
        assert identity(Path(compiler['path'])) == compiler
        expected = dict(zip(KEYS, [sha(manifest_data), sha((folder/'argv.bin').read_bytes()),
            sha((folder/'environment.bin').read_bytes()), compiler['sha256'], sha(version)]))
        assert binding['keys'] == expected == {k:rec['environment'][k] for k in KEYS}
        assert manifest['distribution'] == roster(source) and manifest['host_support'] == roster(hosts)
        if mode == 'exact146-metadata-mir': actual = source
        elif mode == 'actual90-layout-queries':
            actual = dict(source)
            actual[ACCOUNT] += (HERE/'layout-queries.inc.rs').read_bytes()
            actual['src/lib.rs'] = b'#![feature(never_type)]\n'+actual['src/lib.rs']
        elif mode == 'synthetic-optimized':
            actual = testing_source(source)
            actual['src/experimental_swift_reactor/control_tests.rs'] += (HERE/'extra-interactions.inc.rs').read_bytes()
        else: raise AssertionError(mode)
        assert manifest['compiled_source'] == roster(actual)
        assert binding['source_members'] == 146 and binding['host_members'] == 11
        assert binding['host_tree'] == HOST_TREE and binding['distribution_tree'] == TREE
        assert binding['compiled_tree'] == roster(actual)['tree_sha256']
        for tool in manifest['orchestration']:
            path = Path(tool['path'])
            if identity(path) == tool: continue
            matches = [p for p in available_tools if p.stat().st_size == tool['bytes'] and sha(p.read_bytes()) == tool['sha256']]
            assert matches, tool
            history.append(dict(compile=mode, original=tool,
                preserved_snapshot=str(matches[0].relative_to(HERE)),
                reason='Reviewer source changed after compile for query alias handling; original bytes preserved'))
        compiled.append(dict(mode=mode, compile_identity_keys=expected, distribution_tree=TREE,
            compiled_tree=roster(actual)['tree_sha256'], host_tree=HOST_TREE))
    assert len(compiled) == 3
    commands = []
    command_folders = list((HERE/'commands').iterdir())
    historical_folders = list((HERE/'attempts').glob('*/commands/*'))
    for folder in command_folders+historical_folders:
        if not (folder/'receipt.json').exists(): continue
        rec = read(folder/'receipt.json')
        assert rec['expectation_met'] and rec['exit_code'] == rec['expected_exit_code']
        assert rec['child_reaped'] and rec['owned_group_absent'] and not rec['timed_out_or_output_limited']
        assert rec['timeout_seconds'] <= 180 and not rec['global_process_inventory']
        for stream in ['stdout','stderr']:
            raw = output(folder,stream)
            assert rec[stream] == row(stream,raw)
        if rec['required_output']:
            assert rec['required_output'].encode() in output(folder,'stdout')+output(folder,'stderr')
        snapshots = [p for p in available_tools if p.stat().st_size == rec['runner']['bytes'] and sha(p.read_bytes()) == rec['runner']['sha256']]
        assert snapshots, rec['runner']
        commands.append(dict(path=str(folder.relative_to(HERE)), expected_exit=rec['expected_exit_code'],
            owned_group_reaped_and_absent=True, output_hashes_verified=True,
            historical='attempts' in folder.parts))
    assert len(commands) == 13 and sum(not c['historical'] for c in commands) == 10
    for mode in ['exact146-metadata-mir','actual90-layout-queries','synthetic-optimized']:
        clean = read(HERE/'commands'/mode/'cleanup.json')
        assert clean['completed'] and clean['child_groups_reaped_and_absent'] and clean['owned_scratch_removed']
        assert clean['removed_artifact'] and not clean['global_process_inventory'] and not clean['native_device_simulator_emulator_UI_capture']
    assert not (HERE/'owned-work').exists()
    artifact = read(HERE/'commands/exact146-metadata-mir/artifact.json')
    assert artifact['nonempty'] and artifact['metadata_only'] and not artifact['executed']
    assert artifact['bytes'] == 25580724 and not Path(artifact['path']).exists()
    layout = read(HERE/'fresh-layout-results.json')
    assert layout['diagnostic_queries'] == 90 and layout['distinct_nonunit_types'] == 89
    assert layout['role_count'] == 396 and layout['logical_source_object_bytes'] == 311071
    assert layout['closure_bytes'] == 8 and layout['closure_roles'] == 4
    assert layout['phases']['P0-pre-existing-parent-account-bookkeeping'] == dict(functions=15,roles=208,logical_bytes=234375)
    mir = read(HERE/'mir-and-closure.json')
    assert mir['function_count'] == 19 and mir['roles'] == 396
    assert mir['closure']['fresh_actual_compiler_print_type_size']
    assert all(f['identical_normalized_body_and_types'] for f in mir['functions'])
    selected_mir = output(HERE,'entry-and-account.mir')
    assert selected_mir.count(b'\n}\n') == 19
    summary = dict(schema=1, status='accepted-bounded-exact146-private-typed-composition-with-fresh-layouts',
        source_members=146, source_tree_sha256=TREE, host_members=11, host_tree_sha256=HOST_TREE,
        producer_members_verified=152, producer_bytes_verified=1301753,
        upstream_packets_reverified=3, funding_source_members_verified=144,
        producer_builds_audited=9, producer_identity_keys_audited=45, producer_command_receipts_audited=19,
        producer_metadata_bytes=25579436, independent_metadata_bytes=artifact['bytes'],
        final_independent_builds=3, final_independent_identity_keys=15,
        final_independent_commands=10, preserved_historical_commands=3,
        superseded_metadata_compiler_successes=1, total_whole_tree_compiler_invocations=4,
        preserved_reviewer_assumption_failures=4, product_defects_found=0,
        production_private_typed_route_compile_only=True,
        fresh_MIR_functions=19, fresh_MIR_roles=396, fresh_concrete_layout_queries=90,
        distinct_nonunit_concrete_types=89, selected_dispatch_closure_bytes=8,
        fresh_logical_source_object_bytes=311071, P0_roles=208, P0_logical_source_object_bytes=234375,
        complete_dynamic_backing_stack_RSS_allocator_CPU_work_quote_or_P0_policy=False,
        synthetic_optimized_tests=19, frozen_combined_regressions=4, account_regressions=11,
        producer_composition_interactions=2, independent_focused_interactions=2,
        producer_debug_and_optimized_tests_each_mode_audited=17,
        privacy_negative_controls_audited=5, privacy_positive_controls_audited=1,
        source145_loader_quote_applies_to146=False, future146_quote_rebinding_required=True,
        RootPolicyPending=True, WholeQuotePending=True, WorkAuditPending=True,
        selected_execution_work=451814442, C=79676, S=941467, A=430175, H=81327,
        selected_unit_construction=1469366, final_selected_retention=1899541,
        product_work_limit=1000000000, product_storage_limit_bytes=268435456,
        healthy_cleanup_or_complete_host_funding=False,
        real_fixture_loader_VM_cache_scope_construct_writer_executed=False,
        native_device_simulator_emulator_UI_capture_global_process_inventory=False,
        native_checks_pending=True, OTA_FieldLog_GA_operational_authority=False,
        all_owned_children_reaped_and_groups_absent=True, all_owned_scratch_removed=True,
        git_root_canonical_sibling_frozen_files_changed=False,
        compile_identity_preimages=compiled, commands=commands, tool_history=history,
        offline_verification_command=['python3','verification/swift-guarded-snapshot-host-composition-independent/verify.py'],
        verification_python_version=sys.version, verification_tool_sha256=sha(Path(__file__).read_bytes()))
    if (HERE/'seal.json').exists(): assert read(HERE/'results.json') == summary
    else: write('results.json',summary)
    print(json.dumps({k:summary[k] for k in ['status','source_members','fresh_concrete_layout_queries','fresh_logical_source_object_bytes','synthetic_optimized_tests','all_owned_scratch_removed']}))

if __name__ == '__main__': main()
