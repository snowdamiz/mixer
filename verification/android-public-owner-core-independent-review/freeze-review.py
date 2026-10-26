#!/usr/bin/env python3
"""Freeze only this independent review lane after checking its exact evidence."""
from pathlib import Path
import datetime
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
DOC = ROOT / 'docs/android-public-owner-core-independent-review.md'
CORE = ROOT / 'native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java'


def digest(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def read(path):
    return json.loads(path.read_bytes())


def write(path, obj):
    path.write_text(json.dumps(obj, sort_keys=True, indent=2) + '\n')


def main():
    assert not (BASE / 'seal.json').exists(), 'final packet is already frozen'
    producer_manifest_path = ROOT / 'verification/android-public-owner-core/manifest.json'
    producer = read(producer_manifest_path)
    assert len(producer['members']) == 48
    producer_bytes = 0
    for name, expected in producer['members'].items():
        assert digest(ROOT / name) == expected, name
        producer_bytes += expected['bytes']
    assert producer_bytes == 183472
    binding = read(ROOT / 'verification/android-public-owner-core/source-bindings.json')
    tree_inputs = {key: value for key, value in binding.items() if not key.startswith('tree_')}
    binding_tree = hashlib.sha256(json.dumps(tree_inputs, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert binding_tree == binding['tree_sha256'] == 'c5597d41313b506ef39a0dcd36ebde7fd8f50c78db436410681262c1c233833d'
    source_count = 0
    for group in ['implementation', 'unchanged_source_pair_1']:
        for name, expected in binding[group].items():
            assert digest(ROOT / name) == expected, name
            source_count += 1
    assert source_count == 46 and len(binding['unchanged_source_pair_1']) == 42
    assert digest(CORE) == {'bytes': 12473, 'sha256': '4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6'}
    root_seal_path = ROOT / 'verification/android-public-owner-core-root-review/preaccess-seal.json'
    assert digest(root_seal_path)['sha256'] == 'afc099d49f365c143b3db12d880693d528ea48db67baa3b07f61913354515a09'
    assert digest(BASE / 'preaccess-seal.json')['sha256'] == '3b049f8b4a7d84276fd62a2d14e92d38a906883062d68c55a41dc26d6569a653'
    preaccess = read(BASE / 'preaccess-seal.json')
    assert preaccess['candidate_source_accessed'] is False
    for name, expected in preaccess['members'].items():
        assert digest(ROOT / name) == expected, name
    snapshots = read(BASE / 'input-snapshots.json')
    for name, expected in snapshots['members'].items():
        assert digest(BASE / 'inputs' / name) == expected, name
    expected_basis = {
        'docs/android-public-owner-contract.md': '6afb09416bbc28820c2cb11ec7f7d204d359d8053737df99d394f96f6b1400f3',
        'verification/android-public-owner-root-review/implementation-selection.json': '763f049c2c95a006874d78ad5cd473d19fc147482c952bbd0725348e7609d5a9'}
    for name, expected in expected_basis.items():
        assert digest(ROOT / name)['sha256'] == expected
        assert digest(BASE / 'inputs' / name)['sha256'] == expected

    attempts = {}
    child_count = 0
    for label, method_count, scenario_count, assertion_count in [('first', 32, 70, 264250), ('final', 33, 71, 264289)]:
        folder = BASE / 'attempts' / label
        receipt = read(folder / 'receipt.json')
        assert receipt['success'] and not receipt['errors']
        summary = receipt['summary']
        assert (summary['methods'], summary['scenarios'], summary['assertions'], summary['failures']) == (method_count, scenario_count, assertion_count, 0)
        assert set(summary['control_passed_methods']) == {f'R{i:02}' for i in range(1, 16)}
        assert summary['wrong_thread_calls'] == 134 and summary['stress_cycles'] == 20000
        assert summary['max_batch'] == 4
        commands = read(folder / 'commands.json')
        assert len(commands) == 6
        for command in commands:
            assert command['returned_and_reaped'] and command['returncode'] == 0 and not command['timed_out']
            assert command['timeout_seconds'] <= 60 and command['elapsed_seconds'] < 180
            assert digest(folder / (command['name'] + '.stdout')) == command['stdout']
            assert digest(folder / (command['name'] + '.stderr')) == command['stderr']
        compiler = next(row for row in commands if row['name'] == 'compile')['argv']
        assert compiler[-2:] == [str(CORE), str(BASE / 'IndependentOwnerLifecycleReview.java')]
        for option in ['-Xlint:all', '-Werror', '-proc:none', '-classpath', '-sourcepath']:
            assert option in compiler
        assert compiler[compiler.index('--release') + 1] == '17'
        assert compiler[compiler.index('-classpath') + 1] == compiler[compiler.index('-sourcepath') + 1]
        assert not (folder / 'compile.stdout').read_bytes() and not (folder / 'compile.stderr').read_bytes()
        source_bindings = read(folder / 'source-bindings.json')
        for name, expected in source_bindings['sources'].items():
            assert digest(folder / 'inputs' / Path(name).name) == expected, name
            if label == 'final':
                assert digest(ROOT / name) == expected, name
        assert digest(folder / 'inputs' / 'OwnerLifecycleV2.java') == digest(CORE)
        classes = read(folder / 'classes.json')
        assert classes['count'] == len(classes['classes']) == 14
        assert {row['major_version'] for row in classes['classes'].values()} == {61}
        cleanup = read(folder / 'cleanup.json')
        assert cleanup['all_owned_children_returned_and_reaped']
        assert cleanup['only_owned_scratch_removed_after_children_reaped'] and not Path(cleanup['owned_scratch']).exists()
        assert cleanup['max_child_timeout_seconds'] + cleanup['max_kill_reap_timeout_seconds'] <= 180
        assert not cleanup['native_capture_device_or_unrelated_processes_started_or_queried']
        child_count += len(commands)
        attempts[label] = {'summary': summary, 'receipt': digest(folder / 'receipt.json'), 'classes': classes['count'], 'cleanup': cleanup}

    assert digest(BASE / 'attempts/first/inputs/IndependentOwnerLifecycleReview.java') != digest(BASE / 'attempts/final/inputs/IndependentOwnerLifecycleReview.java')
    for name, expected in read(BASE / 'toolchain-bindings.json')['members'].items():
        assert digest(Path(name)) == {key: value for key, value in expected.items() if key != 'resolved_path'}
    static = read(BASE / 'git-diff-check.json')
    assert static['exit_code'] == 0 and static['output'] == ''
    authored = [BASE / 'IndependentOwnerLifecycleReview.java', BASE / 'run-review.py', Path(__file__).resolve(), DOC]
    for path in authored:
        text = path.read_text()
        assert text.endswith('\n') and '\r' not in text
        assert all(line == line.rstrip() for line in text.splitlines()), path

    context_revision = (BASE / 'attempts/final/context.stdout').read_text().strip()
    at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt = {
        'schema': 1, 'at': at, 'status': 'independent-host-review-passed-awaiting-root-review',
        'command': [sys.executable, '-B', str(Path(__file__).resolve())], 'python': sys.version,
        'scope': 'Only selected package-private pure Java ownership decisions and focused retained-state source review.',
        'context_revision': context_revision, 'candidate': {'path': str(CORE.relative_to(ROOT)), **digest(CORE)},
        'root_preaccess_seal_sha256': digest(root_seal_path)['sha256'],
        'independent_preaccess_seal_sha256': digest(BASE / 'preaccess-seal.json')['sha256'],
        'producer_manifest': {'path': str(producer_manifest_path.relative_to(ROOT)), **digest(producer_manifest_path), 'members_verified': 48, 'bytes_verified': producer_bytes},
        'producer_source_binding_tree_sha256': binding_tree,
        'producer_current_source_inputs_verified': source_count, 'unchanged_source_pair_1_members_verified': 42,
        'attempts': attempts, 'attempt_counts_are_nonadditive': True,
        'attempt_history': 'First attempt passed unchanged. Final adds only the independently identified INPUTTING invalidation control; harness main executes the full set. No compiler, harness, oracle or candidate failure was observed in either run.',
        'candidate_defects': [], 'harness_or_oracle_defects': [],
        'source_review': digest(BASE / 'source-review.json'),
        'static_checks': {'tracked_diff_whitespace_exit': 0, 'new_authored_text_whitespace_checked_files': len(authored)},
        'owned_host_child_count': child_count,
        'all_owned_children_returned_and_reaped': True,
        'owned_scratch_removed_only_after_children_returned': True,
        'maximum_child_timeout_plus_forced_reap_seconds': 75,
        'producer_tests_runner_verifier_imported_or_executed': False,
        'native_capture_device_or_unrelated_processes_started_or_queried': False,
        'hosted_catalog_inspector_authority_driver_rejected_WorkerV2_or_broad_hosted_harness_accessed': False,
        'patch_or_skip_implementation_tests_generated_sources_or_dependencies_accessed': False,
        'product_source_or_root_metadata_edited': False,
        'root_acceptance_claimed': False, 'public_routing_selected': False, 'GA_qualified': False,
        'pending_limits': [
            'An operation that never returns leaves actual resource reclamation pending.',
            'Trusted injected thread check does not establish actual Android main-Looper identity.',
            'Decisions and cleanup reports do not prove Android listener registration/removal, native gate sealing, setter reentrancy, JNI behavior, fatal-error propagation or the commit/finish interval.',
            'Later effect runner, public Activity integration, native simulator/emulator runtime checks and final physical-phone matrix remain pending under the active pause.',
            'No new API28-35, accessibility/resources/fonts, saved-state continuity, signed/store/operational or OTA support is established.',
            'Immutable published separate-repository FieldLog consumption and accountable GA review remain pending.'
        ]
    }
    write(BASE / 'receipt.json', receipt)
    members = {}
    for path in sorted(BASE.rglob('*')):
        if path.is_file() and path not in [BASE / 'manifest.json', BASE / 'seal.json']:
            members[str(path.relative_to(ROOT))] = digest(path)
    members[str(DOC.relative_to(ROOT))] = digest(DOC)
    manifest = {'schema': 1, 'scope': 'Independent Android owner-core review packet and its single owned documentation file.', 'members': dict(sorted(members.items()))}
    write(BASE / 'manifest.json', manifest)
    seal = {
        'schema': 1, 'at': at, 'context_revision': context_revision,
        'manifest': {'path': str((BASE / 'manifest.json').relative_to(ROOT)), **digest(BASE / 'manifest.json')},
        'member_count': len(members), 'member_bytes': sum(row['bytes'] for row in members.values()),
        'members_tree_algorithm': 'sha256 of compact sorted-key UTF-8 JSON of manifest members',
        'members_tree_sha256': hashlib.sha256(json.dumps(manifest['members'], sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'independent_review_passed': True, 'root_acceptance_claimed': False
    }
    write(BASE / 'seal.json', seal)
    for name, expected in members.items():
        assert digest(ROOT / name) == expected, name
    print(json.dumps({'seal_sha256': digest(BASE / 'seal.json')['sha256'], **seal}, indent=2))


if __name__ == '__main__':
    main()
