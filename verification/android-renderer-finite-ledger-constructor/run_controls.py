#!/usr/bin/env python3
"""Two bounded ordinary-Java controls, exact sealed inputs and leased compiler only."""
from pathlib import Path, PurePosixPath
import datetime
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time

D = Path(__file__).resolve().parent
ROOT = D.parent.parent
OVERLAY = ROOT / 'verification/android-source-pair5-coherent-integration-preparation'
SEMANTIC = ROOT / 'verification/android-renderer-semantic-policy-preparation'
FINITE = ROOT / 'verification/android-renderer-finite-membership-controls'
INDEPENDENT = ROOT / 'verification/android-renderer-finite-membership-independent'
OTHER_LEDGER = ROOT / 'verification/android-finite-ledger-controls'
PACKETS = [
    (OVERLAY, '0dc913d88d4ee7d1e6583bdf00e1e407cc6b446ac7c7aaf6180a36a45b021e9b', 380),
    (SEMANTIC, '35e5cf5d97652a76829bfd10c967898d1d32d7315104a592ab1a34c26c560c9b', 34),
    (FINITE, 'e901741635c6827b0d14b70c51248ea64a5a4071defd0d8a4c58c9fbdb904f93', 849),
    (INDEPENDENT, 'af43bfee836562f3d8925bb3904d9ea7b4703e96e76ea2db9cfb316380096f92', 25),
    (OTHER_LEDGER, 'f90c7fd6240fd8fc63c3c16ac01997e673747d222136271764e1e657ad447a0b', 836),
]
CONTEXT = '1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
JDK = ROOT / 'verification/android-editor-membership-compiled-boundary-qualification/state-qualification/owned-tool-scratch/jdk-17.0.21+9/Contents/Home'
CONTROL = 'FiniteRendererLedgerConstructorControls.java'
LEDGER_ID = 'dev/mixer/android/NativeRenderer#rememberV2(Ljava/lang/Throwable;)V'
CONSTRUCTOR_ID = 'dev/mixer/android/NativeRenderer$PreservationMembership#<init>(Ldev/mixer/android/NativeRenderer$NativeState;Ldev/mixer/android/NativeAppearanceViewsV2$FieldPreservation;)V'
SELECTED_IDS = {LEDGER_ID, CONSTRUCTOR_ID}


def identity(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def verify_packet(root, expected, count):
    assert identity(root / 'seal.json')['sha256'] == expected
    seal = json.loads((root / 'seal.json').read_bytes())
    assert seal['member_count'] == len(seal['members']) == count
    paths = set()
    for item in seal['members']:
        relative = PurePosixPath(item['path'])
        assert not relative.is_absolute() and '..' not in relative.parts and str(relative) not in paths
        paths.add(str(relative))
        path = root / str(relative)
        assert path.is_file() and not path.is_symlink()
        assert identity(path) == {'bytes': item['bytes'], 'sha256': item['sha256']}, path
    actual = set()
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            assert not (Path(base) / name).is_symlink()
        for name in files:
            actual.add((Path(base) / name).relative_to(root).as_posix())
    assert actual == paths | {'seal.json'}, (root.name, 'closed members mismatch')
    return {'packet': str(root.relative_to(ROOT)), 'seal_sha256': expected,
            'member_count': count, 'member_bytes': sum(item['bytes'] for item in seal['members']),
            'closed_manifest_verified': True, 'no_symlinks': True}


def prepare_inputs(verified):
    directory = D / 'inputs'
    directory.mkdir(exist_ok=True)
    source_map = json.loads((FINITE / 'inputs/selected-product-source-map.json').read_bytes())
    class_map = json.loads((FINITE / 'inputs/selected-product-class-map.json').read_bytes())
    assert len(source_map) == 16 and len(class_map) == 209
    finite_seal = json.loads((FINITE / 'seal.json').read_bytes())
    members = {item['path']: item for item in finite_seal['members']}
    leaves = sorted(name for name in members if name.startswith('inputs/host-leaves/') and name.endswith('.java'))
    assert len(leaves) == 87
    roster = []

    def copy_input(source, relative, origin):
        target = directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert identity(target) == identity(source), ('existing input altered', relative)
        else:
            shutil.copyfile(source, target)
        roster.append({'path': 'inputs/' + relative, 'sealed_origin': origin, **identity(target)})

    for name, expected in sorted(source_map.items()):
        source = OVERLAY / 'source/native/android/app/src/dev/mixer/android' / name
        assert identity(source) == expected == identity(FINITE / 'inputs/product' / name)
        copy_input(source, 'product/' + name, str(source.relative_to(ROOT)))
    for name in leaves:
        copy_input(FINITE / name, name.removeprefix('inputs/'), str((FINITE / name).relative_to(ROOT)))
    for name in ['SelectedIdentityMembershipReviewControls.java', 'descriptor.json', 'selected-product-source-map.json', 'selected-product-class-map.json']:
        copy_input(FINITE / 'inputs' / name, name, str((FINITE / 'inputs' / name).relative_to(ROOT)))
    full = json.loads((SEMANTIC / 'inputs/complete-280-checklist.json').read_bytes())
    semantic = json.loads((SEMANTIC / 'proposal.json').read_bytes())
    assert len(full['subjects']) == 280 and len(semantic['subjects']) == 24
    original = [subject for subject in full['subjects'] if subject['id'] in SELECTED_IDS]
    prepared = [subject for subject in semantic['subjects'] if subject['id'] in SELECTED_IDS]
    assert len(original) == len(prepared) == 2
    for subject in original:
        selected = next(item for item in prepared if item['id'] == subject['id'])
        assert subject['categories'] == selected['original_categories']
        assert subject['required_semantic_cases'] == selected['original_required_case_ids']
    save(directory / 'original-two-subjects.json', {'subjects': original, 'complete280_checklist': identity(SEMANTIC / 'inputs/complete-280-checklist.json')})
    save(directory / 'original-two-semantic-proposals.json', {'subjects': prepared, 'original24_proposal': identity(SEMANTIC / 'proposal.json')})
    save(D / 'inputs-verified.json', {'status': 'passed', 'packets': verified, 'source_context': CONTEXT,
         'original_subjects_categories_and_cases_preserved': True, 'product_sources': 16, 'concrete_B_leaves': 87,
         'all_209_expected_product_classes': 209, 'source_roster': roster})
    return source_map, class_map, roster


def main():
    assert len(sys.argv) == 2 and sys.argv[1].startswith('run-')
    run_name = sys.argv[1]
    assert '/' not in run_name and '..' not in run_name
    assert not (D / 'seal.json').exists(), 'closed packet must not be rerun or mutated'
    run_dir = D / run_name
    assert not run_dir.exists(), 'fresh authoring run required'
    run_dir.mkdir()
    scratch = run_dir / 'owned-scratch'
    commands = []
    env = dict(os.environ)
    for name in ['_JAVA_OPTIONS', 'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', 'CLASSPATH', 'JAVA_OPTS', 'JDK_JAVAC_OPTIONS']:
        env.pop(name, None)

    def run(name, argv, seconds):
        out_path, err_path = run_dir / (name + '.stdout'), run_dir / (name + '.stderr')
        began = time.monotonic()
        with out_path.open('wb') as out, err_path.open('wb') as err:
            child = subprocess.Popen([str(item) for item in argv], cwd=D, env=env, stdout=out, stderr=err, start_new_session=True)
            timeout = False
            try:
                child.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                timeout = True
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        entry = {'name': name, 'argv': [str(item) for item in argv], 'cwd': str(D), 'timeout_seconds': seconds,
                 'exit': child.returncode, 'timeout': timeout, 'reaped': True, 'elapsed_seconds': time.monotonic() - began,
                 'stdout': {'path': out_path.name, **identity(out_path)}, 'stderr': {'path': err_path.name, **identity(err_path)}}
        commands.append(entry)
        save(run_dir / 'commands.json', commands)
        print(name, child.returncode, flush=True)
        assert child.returncode == 0 and not timeout, name

    try:
        verified = [verify_packet(*packet) for packet in PACKETS]
        save(run_dir / 'input-seal-verification.json', verified)
        source_map, class_map, roster = prepare_inputs(verified)
        scratch.mkdir()
        empty = scratch / 'empty'
        empty.mkdir()
        classes = run_dir / 'classes'
        classes.mkdir()
        shutil.copyfile(D / CONTROL, run_dir / CONTROL)
        shutil.copyfile(Path(__file__), run_dir / 'run_controls.py')
        source_roster = {entry['path']: {'bytes': entry['bytes'], 'sha256': entry['sha256']} for entry in roster}
        save(run_dir / 'source-roster.json', source_roster)
        sources = [D / name for name in source_roster if name.endswith('.java')]
        assert len(sources) == 104
        sources.append(run_dir / CONTROL)
        tools = {name: identity(JDK / name) for name in ['bin/java', 'bin/javac', 'lib/modules', 'lib/server/libjvm.dylib']}
        assert tools == json.loads((FINITE / 'run-3/provenance.json').read_bytes())['tools']
        save(run_dir / 'provenance.json', {
            'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_context': CONTEXT,
            'source_revision_context': '6450104dc3b02d0f4d4e572c6b05ad7fdc6657b2', 'packets': verified,
            'python': sys.version, 'host': list(os.uname()), 'tools': tools,
            'tool_lease': str(JDK.relative_to(ROOT)), 'lease_scope': 'only tool bytes and java/javac execution; no surrounding active-lane reads or deletion',
            'runner': identity(Path(__file__)), 'control': identity(D / CONTROL), 'source_roster': identity(run_dir / 'source-roster.json'),
            'launch_command': [sys.executable, '-B', str(Path(__file__)), run_name],
            'default_debug_information_no_explicit_g': True,
            'selected_method_descriptors': sorted(SELECTED_IDS)})
        run('java-version', [JDK / 'bin/java', '-version'], 20)
        run('javac-version', [JDK / 'bin/javac', '-version'], 20)
        run('compile', [JDK / 'bin/javac', '--release', '17', '-proc:none', '-Xlint:all', '-Werror', '-sourcepath', empty, '-classpath', empty, '-d', classes, *sources], 60)
        actual_map = {name: identity(classes / name) for name in class_map}
        assert actual_map == class_map, 'all 209 product class bytes must match before invocation'
        actual_sources = {name: identity(D / 'inputs/product' / name) for name in source_map}
        context = hashlib.sha256(json.dumps({'source_map': actual_sources, 'class_map': actual_map}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        assert context == CONTEXT
        save(run_dir / 'actual-product-class-map.json', actual_map)
        save(run_dir / 'compile-identity.json', {'source_context': context, 'all_209_exact_matches': True,
             'product_sources': 16, 'concrete_B_leaves': 87, 'original_fixture': 1, 'bounded_control': 1,
             'default_debug_information_no_explicit_g': True, 'no_source_or_BCI_rewrite': True,
             'scope': 'JDK host-Java compilation only; no native runtime/compiler/device qualification'})
        run('finite-controls', [JDK / 'bin/java', '-ea', '-Xmx256m', '-cp', classes, 'dev.mixer.android.FiniteRendererLedgerConstructorControls',
            D / 'inputs/descriptor.json', run_dir / 'actual-results.json', run_dir / 'snapshots.json', run_dir / 'boundary.json'], 60)
        results = json.loads((run_dir / 'actual-results.json').read_bytes())
        snapshots = json.loads((run_dir / 'snapshots.json').read_bytes())['snapshots']
        assert results['invocations'] == len(results['rows']) == 41
        assert results['remember_invocations'] == 32 and results['constructor_invocations'] == 9
        assert results['source_context'] == CONTEXT and len(snapshots) == 82
        assert results['original_boundary_counts'] == [2, 2, 3] and results['original_final_counts'] == [0, 0, 0]
        assert results['original_edit_completed_after_finally_restores'] and results['fixture_close_returned']
        assert len({(row['subject_id'], row['control_case']) for row in results['rows']}) == 41
        for row in results['rows']:
            assert row['subject_id'] in SELECTED_IDS and row['actual_after'] == row['literal_expected_after']
            assert row['unchanged_non_target_fields_and_containers'] and row['counts_before'] == row['counts_after'] == [2, 2, 3]
            assert row['native_effects'] == 0 and row['native_events_before'] == row['native_events_after']
            assert row['actual_typed_outcome']['exception'] is None
            assert row['actual_typed_outcome']['kind'] == ('void' if row['subject_id'] == LEDGER_ID else 'constructed-reference')
            for when in ['before', 'after']:
                snapshot = snapshots[row['snapshot_' + when + '_index']]
                raw = json.dumps(snapshot, separators=(',', ':'), ensure_ascii=False).encode()
                assert hashlib.sha256(raw).hexdigest() == row['snapshot_' + when + '_sha256']
        save(run_dir / 'receipt.json', {
            'status': 'passed-two-finite-host-Java-controls-root-selection-pending', 'source_context': CONTEXT,
            'invocations': 41, 'per_subject': {LEDGER_ID: 32, CONSTRUCTOR_ID: 9}, 'checks': results['checks'],
            'all_209_exact_product_class_hashes_reproduced_before_execution': True,
            'original_real_fixture': 'SelectedIdentityMembershipReviewControls.Fixture(true,true)',
            'ordinary_edit_boundary': 'first actual A View.invalidate entry with A/C registered scopes',
            'original_counts': {'at_boundary': [2, 2, 3], 'after_edit': [0, 0, 0]},
            'original_edit_completed_after_finally_restores': True, 'all_finite_direct_calls_zero_native_effects': True,
            'snapshot_scope': results['snapshot_scope'], 'snapshot_count': 82,
            'constructor_additional_default_fields': [], 'constructor_only_two_original_final_reference_fields': True,
            'private_ledger_component_seeds_do_not_establish_enclosing_lifecycle_reachability': True,
            'native_callback_helper_returns': 'source-only unless independently directly executed and joined; no return helper acceptance in this packet',
            'original_enclosing_count_cleanup_authority_allocation_failure_cases_all_pending': True,
            'complete_matrix_canonical_native_OTA_GA_accepted': False})
    except BaseException as failure:
        save(run_dir / 'failure.json', {'status': 'failed-authoring-attempt-no-pass-credit', 'type': type(failure).__name__, 'message': str(failure)})
        raise
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)
        save(run_dir / 'cleanup.json', {
            'all_started_children_bounded_and_reaped': all(command['reaped'] for command in commands),
            'owned_compile_scratch_removed': not scratch.exists(), 'leased_JDK_preserved': True,
            'native_devices_simulators_emulators_UI_capture_computer_use_started': False,
            'process_inventories_run': False, 'other_projects_processes_touched': False,
            'original_fixture_close': 'Called by harness finally after restoring component seeds; catches product errors itself, so host disposal only',
            'physical_native_cleanup_credit': False})


if __name__ == '__main__':
    main()
