"""Read-only custody, exact composition and fresh-build receipt reconciliation."""
from pathlib import Path
import json
import os
import struct
import sys

sys.dont_write_bytecode = True
from prepare import (HERE, ROOT, COMPILE_KEYS, sha, canonical, roster, checked_candidate,
                     compose, write, SUPPORT_TREE)
from run import packed, packed_environment, RELEASE_SHA

LABELS = ['metadata-production', 'metadata-unit', 'interactions-debug', 'interactions-optimized']


def unpacked(data):
    assert len(data) >= 8
    count = struct.unpack_from('<Q', data, 0)[0]
    offset = 8
    values = []
    for _ in range(count):
        assert offset + 8 <= len(data)
        extent = struct.unpack_from('<Q', data, offset)[0]
        offset += 8
        assert offset + extent <= len(data)
        values.append(data[offset:offset+extent])
        offset += extent
    assert offset == len(data)
    return values


def verify():
    source, hosts = checked_candidate()
    base, repeated, _, custody, releases, source_checks, operations = compose()
    assert source == repeated
    assert json.loads((HERE / 'source-controls.json').read_bytes()) == source_checks
    assert (HERE / 'root-dependent-release.json').is_file()
    root_release = json.loads((HERE / 'root-dependent-release.json').read_bytes())
    assert root_release['root_acceptance']['sha256'] == RELEASE_SHA
    assert sha((ROOT / root_release['root_acceptance']['path']).read_bytes()) == RELEASE_SHA
    source_tree = roster(source)['tree_sha256']
    assert source_tree == '270cf2c4b2e72452470d2b6cacea9f87d3c02bd0ab5916ea7b579614a799892a'
    assert roster(hosts)['tree_sha256'] == SUPPORT_TREE
    overlay = json.loads((HERE / 'test-overlay-manifest.json').read_bytes())
    test_source = dict(source)
    for operation in overlay['append_operations']:
        before = test_source[operation['path']]
        assert sha(before) == operation['base_sha256'] and len(before) == operation['base_bytes']
        appendix = Path(operation['append']['path']).read_bytes()
        assert sha(appendix) == operation['append']['sha256'] and len(appendix) == operation['append']['bytes']
        test_source[operation['path']] += appendix
    assert roster(test_source) == overlay['source']
    assert overlay['exact_product_source'] == roster(source)
    assert overlay['expected_unit_floor_before'] == 1898105
    assert overlay['expected_unit_floor_combined'] == 1899541
    assert overlay['delta'] == 1436
    build_results = []
    groups = []
    compiler_identity = None
    for label in LABELS:
        preimage = HERE / 'preimages' / label
        closure_raw = (preimage / 'manifest.json').read_bytes()
        closure = json.loads(closure_raw)
        binding = json.loads((preimage / 'binding.json').read_bytes())
        receipt = json.loads((HERE / 'commands' / label / 'receipt.json').read_bytes())
        version_receipt = json.loads((HERE / 'commands' / (label + '-rustc-version') / 'receipt.json').read_bytes())
        version = (preimage / 'compiler-version.txt').read_bytes()
        argv = (preimage / 'argv.bin').read_bytes()
        environment = (preimage / 'environment.bin').read_bytes()
        interactions = label.startswith('interactions-')
        assert closure_raw == canonical(closure)
        assert len(closure_raw) <= 65536 and all(len(data) <= 16384 for data in [argv, environment, version])
        assert closure['distribution'] == roster(source)
        assert closure['host_support'] == roster(hosts)
        assert closure['compiled_source'] == roster(test_source if interactions else source)
        assert closure['test_overlay'] == interactions
        assert closure['root_acceptance'] == root_release['root_acceptance']
        assert binding['distribution_source_tree_sha256'] == source_tree
        assert binding['compiled_source_tree_sha256'] == closure['compiled_source']['tree_sha256']
        assert binding['host_support_tree_sha256'] == SUPPORT_TREE
        assert binding['host_support_members'] == 11 and binding['source_members'] == 145
        assert packed(receipt['argv']) == argv
        assert unpacked(argv) == [os.fsencode(value) for value in receipt['argv']]
        bare_environment = {key:value for key,value in receipt['environment'].items() if key not in COMPILE_KEYS}
        assert packed_environment(bare_environment) == environment
        assert len(unpacked(environment)) == len(bare_environment)
        expected_keys = dict(zip(COMPILE_KEYS, [sha(closure_raw), sha(argv), sha(environment),
            closure['tools']['rustc']['sha256'], sha(version)]))
        assert binding['compile_identity_keys'] == expected_keys
        assert {key:receipt['environment'][key] for key in COMPILE_KEYS} == expected_keys
        assert version == (HERE / 'commands' / (label + '-rustc-version') / 'stdout').read_bytes()
        for item in [closure['tools']['rustc'], closure['tools']['python'], closure['tools']['cc'],
                     *closure['tools']['SDK_headers'], *closure['orchestration']]:
            data = Path(item['path']).read_bytes()
            assert len(data) == item['bytes'] and sha(data) == item['sha256'], item['path']
        if compiler_identity is None:
            compiler_identity = closure['tools']['rustc']
        assert closure['tools']['rustc'] == compiler_identity
        artifact = json.loads((HERE / 'commands' / label / 'artifact.json').read_bytes())
        assert artifact['executed'] == interactions
        if label == 'metadata-unit':
            assert artifact['bytes'] == 0
            assert artifact['sha256'] == sha(b'')
        else:
            assert artifact['bytes'] > 0
        assert not Path(artifact['path']).exists()
        cleanup = json.loads((HERE / 'commands' / label / 'cleanup.json').read_bytes())
        assert cleanup['completed'] and cleanup['recorded_owned_groups_absent'] and cleanup['owned_scratch_removed']
        assert cleanup['removed_artifact']['sha256'] == artifact['sha256']
        for command_label, command in [(label, receipt), (label + '-rustc-version', version_receipt)]:
            assert command['expectation_met'] and command['exit_code'] == 0
            assert not command['timed_out_or_output_limited']
            assert command['child_reaped'] and command['owned_group_absent']
            folder = HERE / 'commands' / command_label
            assert sha((folder / 'stdout').read_bytes()) == command['stdout_sha256']
            assert sha((folder / 'stderr').read_bytes()) == command['stderr_sha256']
            groups.append(command['owned_process_group'])
        if interactions:
            test_label = label + '-tests'
            test = json.loads((HERE / 'commands' / test_label / 'receipt.json').read_bytes())
            assert test['expectation_met'] and test['exit_code'] == 0
            assert test['child_reaped'] and test['owned_group_absent']
            assert not test['timed_out_or_output_limited']
            assert test['argv'][1:] == ['combined_source_interaction_', '--nocapture', '--test-threads=1']
            output = (HERE / 'commands' / test_label / 'stdout').read_bytes()
            assert sha(output) == test['stdout_sha256']
            assert b'4 passed; 0 failed; 0 ignored; 0 measured; 468 filtered out' in output
            assert sha((HERE / 'commands' / test_label / 'stderr').read_bytes()) == test['stderr_sha256']
            groups.append(test['owned_process_group'])
        build_results.append(dict(label=label, product_source_tree_sha256=source_tree,
            compiled_source_tree_sha256=binding['compiled_source_tree_sha256'],
            five_compile_keys_reconciled=True, artifact_sha256=artifact['sha256'],
            artifact_bytes=artifact['bytes'],
            nonempty_loader_output_descriptor_qualified=False,
            test_count=4 if interactions else 0))
    assert len(set(groups)) == len(groups) == 10
    assert not (HERE / 'owned-work').exists()
    # Recheck only recorded, owned groups; no process enumeration is performed.
    for group in groups:
        try:
            os.killpg(group, 0)
        except ProcessLookupError:
            continue
        raise AssertionError('previously recorded owned group now exists: ' + str(group))
    return dict(schema=1, source_tree_sha256=source_tree, source_members=145,
        test_overlay_tree_sha256=roster(test_source)['tree_sha256'], host_support_tree_sha256=SUPPORT_TREE,
        host_support_members=11, whole_frozen_input_packets=4, selected_frozen_host_roster_verified=11,
        all_six_component_orders_byte_identical=True, exact_changed_source_paths=source_checks['changed_paths'],
        metadata_builds=2, new_interaction_builds=2, new_interaction_tests_each_mode=4,
        build_preimages=build_results, owned_command_groups_terminal_and_absent=len(groups),
        owned_scratch_removed=True, source_only_driver_failures_preserved=2,
        reconciliation_assumption_failures_preserved=1,
        unit_metadata_output='Observed successful --test --emit=metadata output is zero bytes; unit typechecking only, no usable nonempty loader output descriptor claim',
        helper_unused=True, WorkAuditPending_preserved=True,
        native_device_simulator_emulator_UI_capture='paused and pending',
        genuine_loader_guest_cache_scope_construct_or_writer_executed=False,
        bootstrap_H_full_funding_healthy_cleanup_real_writer_canonical_OTA_or_GA_qualified=False,
        verification_scope='Frozen bytes and fresh compile identity; exact metadata plus four filtered synthetic privatecore -> A commit -> actual complete host interactions per mode')


if __name__ == '__main__':
    result = verify()
    if not (HERE / 'seal.json').exists():
        write('verification-results.json', result)
    print(json.dumps(result, sort_keys=True))
