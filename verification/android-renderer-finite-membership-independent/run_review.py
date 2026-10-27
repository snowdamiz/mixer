#!/usr/bin/env python3
"""Bounded independent review using only the closed ordinary finite-controls packet."""
from pathlib import Path, PurePosixPath
import collections
import datetime
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import time

D = Path(__file__).resolve().parent
ROOT = D.parent.parent
SOURCE = ROOT / 'verification/android-renderer-finite-membership-controls'
SEAL = 'e901741635c6827b0d14b70c51248ea64a5a4071defd0d8a4c58c9fbdb904f93'
CONTEXT = '1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
JDK = ROOT / 'verification/android-editor-membership-compiled-boundary-qualification/state-qualification/owned-tool-scratch/jdk-17.0.21+9/Contents/Home'


def identity(path):
    value = path.read_bytes()
    return {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}


def save(name, value):
    (D / name).write_text(json.dumps(value, indent=2) + '\n')


def verify_source():
    assert identity(SOURCE / 'seal.json')['sha256'] == SEAL
    seal = json.loads((SOURCE / 'seal.json').read_bytes())
    assert seal['member_count'] == 849 and seal['member_bytes'] == 4260485
    paths = set()
    for item in seal['members']:
        relative = PurePosixPath(item['path'])
        assert not relative.is_absolute() and '..' not in relative.parts and str(relative) not in paths
        paths.add(str(relative))
        path = SOURCE / str(relative)
        assert path.is_file() and not path.is_symlink()
        assert identity(path) == {'bytes': item['bytes'], 'sha256': item['sha256']}
    actual = set()
    for base, dirs, files in os.walk(SOURCE, followlinks=False):
        for name in dirs + files:
            assert not (Path(base) / name).is_symlink()
        for name in files:
            actual.add((Path(base) / name).relative_to(SOURCE).as_posix())
    assert actual == paths | {'seal.json'}
    assert len(paths) == 849 and sum(item['bytes'] for item in seal['members']) == 4260485
    save('input-seal-verification.json', {'status': 'passed', 'closed_manifest': True, 'seal_sha256': SEAL,
         'member_count': 849, 'member_bytes': 4260485, 'source_revision_context': seal['source_revision_context'], 'source_context': seal['source_context'], 'selected_run': seal['selected_run']})
    return seal


def review_joins():
    original = json.loads((SOURCE / 'inputs/original-six-subjects.json').read_bytes())['subjects']
    semantic = json.loads((SOURCE / 'inputs/original-six-semantic-proposals.json').read_bytes())['subjects']
    proposal = json.loads((SOURCE / 'proposal.json').read_bytes())
    result = json.loads((SOURCE / 'run-3/actual-results.json').read_bytes())
    rows = result['rows']
    assert result['source_context'] == CONTEXT and result['invocations'] == len(rows) == 142
    assert result['checks'] == 11035945 and result['count_at_original_boundary'] == 3
    assert result['original_edit_completed_after_restores'] and result['original_final_counts'] == [0, 0, 0]
    assert len({(row['subject_id'], row['control_case']) for row in rows}) == 142
    expected_counts = dict(zip(['preservationMembershipV2', 'fieldPreservationCapturedV2', 'preservationProvenanceV2', 'fieldPreservationIdentityV2', 'preservationCohortV2', 'preservationFailureFundedV2'], [23, 31, 18, 10, 30, 30]))
    assert {subject['method']: sum(row['subject_id'] == subject['id'] for row in rows) for subject in original} == expected_counts
    class_map = json.loads((SOURCE / 'inputs/selected-product-class-map.json').read_bytes())
    assert len(class_map) == 209
    assert json.loads((SOURCE / 'run-3/actual-product-class-map.json').read_bytes()) == class_map
    for name, expected in class_map.items():
        assert identity(SOURCE / 'run-3/classes' / name) == expected
    for row in rows:
        subject = next(subject for subject in original if subject['id'] == row['subject_id'])
        assert row['class_sha256'] == subject['class_sha256'] and row['source_context'] == CONTEXT
        assert row['subject_id'] == 'dev/mixer/android/NativeRenderer#' + subject['method'] + row['descriptor']
        assert row['actual'] == row['expected'] and row['all_snapshots_unchanged']
        assert row['snapshot_before_sha256'] == row['snapshot_after_sha256']
        assert row['counts_before'] == row['counts_after'] and row['native_effects'] == 0
        assert row['native_events_before'] == row['native_events_after']
        assert row['case_id'] == 'renderer-finite-source-invariants'
    join_count = 0

    def validate_join(join, subject, exact=None):
        nonlocal join_count
        join_count += 1
        assert join['results'] == {'path': 'run-3/actual-results.json', **identity(SOURCE / 'run-3/actual-results.json')}
        assert join['source_context'] == CONTEXT and join['control_source'] == identity(SOURCE / 'FiniteMembershipControls.java')
        assert join['enclosing_obligations_accepted'] is False
        indices = join['row_indices_zero_based']
        assert len(indices) == len(set(indices))
        assert all(type(index) is int and 0 <= index < 142 and rows[index]['subject_id'] == subject['id'] for index in indices)
        if exact is not None:
            assert indices == exact

    for source in original:
        subject = next(subject for subject in proposal['subjects'] if subject['id'] == source['id'])
        clone = dict(subject)
        extension = clone.pop('finite_control_extension')
        assert clone == source
        indices = [index for index, row in enumerate(rows) if row['subject_id'] == source['id']]
        validate_join(extension['finite_execution_join'], source, indices)
        assert extension['independent_invocations'] == len(indices)
        assert extension['original_case_or_subject_accepted'] is False
        dispositions = extension['original_case_dispositions']
        assert [case['original_case_id'] for case in dispositions] == source['required_semantic_cases']
        for case in dispositions:
            assert case['status'] == 'pending-enclosing-or-runtime-obligation' and case['original_case_accepted'] is False
            if case['original_case_id'] == 'allocation-failure-source-proof-only-pending-runtime':
                assert case['finite_execution_join'] is None
            else:
                validate_join(case['finite_execution_join'], source)
        prepared = next(subject for subject in proposal['selected_prepared_semantic_subjects'] if subject['id'] == source['id'])
        old = next(subject for subject in semantic if subject['id'] == source['id'])
        assert {key: value for key, value in prepared.items() if key != 'required_cases'} == {key: value for key, value in old.items() if key != 'required_cases'}
        assert [case['id'] for case in prepared['required_cases']] == [case['id'] for case in old['required_cases']]
        for case in prepared['required_cases']:
            if case['id'] == 'renderer-finite-source-invariants':
                validate_join(case['execution_join'], source, indices)
                assert case['status'] == 'finite-host-observed-root-selection-pending'
            else:
                assert case['execution_join'] is None and case['status'] == 'pending-enclosing-original-control'
    assert proposal['complete_matrix_policy_canonical_native_OTA_GA_accepted'] is False
    attempt1 = json.loads((SOURCE / 'run-1/failure.json').read_bytes())
    assert attempt1['status'] == 'failed-authoring-attempt-no-pass-credit'
    assert json.loads((SOURCE / 'run-2/actual-results.json').read_bytes())['invocations'] == 136
    for attempt in ['run-1', 'run-2', 'run-3']:
        commands = json.loads((SOURCE / attempt / 'commands.json').read_bytes())
        assert all(command['reaped'] and command['timeout'] is False for command in commands)
        compile_command = next(command for command in commands if command['name'] == 'compile')
        argv = compile_command['argv']
        assert argv[1:6] == ['--release', '17', '-proc:none', '-Xlint:all', '-Werror']
        assert not any(value.startswith('-g') for value in argv)
    save('producer-structural-review.json', {'status': 'passed', 'source_context': CONTEXT, 'selected_run': 'run-3', 'direct_cases': 142,
         'per_subject': expected_counts, 'validated_case_joins': join_count, 'all_209_selected_class_hashes_verified': True,
         'original_subjects_and_all_categories_cases_preserved': True, 'all_original_cases_pending': True,
         'all_actual_expected_counts_snapshot_digests_and_native_prefixes_match': True,
         'repeated_snapshot_assertions_not_semantic_cases': 11035945, 'run1_no_pass_credit': True, 'run2_superseded': True})


def main():
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    seal = verify_source()
    review_joins()
    scratch = D / 'scratch'
    assert not scratch.exists()
    scratch.mkdir()
    commands = []
    env = dict(os.environ)
    for name in ['_JAVA_OPTIONS', 'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', 'CLASSPATH', 'JAVA_OPTS', 'JDK_JAVAC_OPTIONS']:
        env.pop(name, None)

    def run(name, argv, seconds):
        stdout = D / (name + '.stdout')
        stderr = D / (name + '.stderr')
        began = time.monotonic()
        with stdout.open('wb') as out, stderr.open('wb') as err:
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
                 'stdout': {'path': stdout.name, **identity(stdout)}, 'stderr': {'path': stderr.name, **identity(stderr)}}
        commands.append(entry)
        save('commands.json', commands)
        print(name, child.returncode, flush=True)
        assert child.returncode == 0 and not timeout

    try:
        inputs = scratch / 'inputs'
        classes = scratch / 'classes'
        empty = scratch / 'empty'
        inputs.mkdir(); classes.mkdir(); empty.mkdir()
        roster = []
        source_map = json.loads((SOURCE / 'inputs/selected-product-source-map.json').read_bytes())
        class_map = json.loads((SOURCE / 'inputs/selected-product-class-map.json').read_bytes())
        assert len(source_map) == 16 and len(class_map) == 209
        sealed = {item['path']: item for item in seal['members']}
        names = sorted('inputs/product/' + name for name in source_map)
        leaves = sorted(name for name in sealed if name.startswith('inputs/host-leaves/') and name.endswith('.java'))
        assert len(leaves) == 87
        names.extend(leaves)
        names.append('inputs/SelectedIdentityMembershipReviewControls.java')
        sources = []
        for name in names:
            source = SOURCE / name
            target = inputs / name.removeprefix('inputs/')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            assert identity(target) == identity(source)
            sources.append(target)
            roster.append({'sealed_path': name, **identity(target)})
        control = scratch / 'IndependentFiniteControls.java'
        shutil.copyfile(D / control.name, control)
        sources.append(control)
        save('source-roster.json', roster)
        provenance = json.loads((SOURCE / 'run-3/provenance.json').read_bytes())
        tools = {name: identity(JDK / name) for name in ['bin/java', 'bin/javac', 'lib/modules', 'lib/server/libjvm.dylib']}
        assert tools == provenance['tools']
        save('provenance.json', {'at': started, 'source_revision_context': seal['source_revision_context'], 'source_context': CONTEXT,
             'input_seal_sha256': SEAL, 'tools': tools, 'tool_lease': str(JDK.relative_to(ROOT)), 'python': sys.version, 'platform': platform.platform(),
             'control': identity(D / 'IndependentFiniteControls.java'), 'runner': identity(Path(__file__)),
             'source_roster': identity(D / 'source-roster.json'), 'launch_command': [sys.executable, '-B', str(Path(__file__))]})
        run('java-version', [JDK / 'bin/java', '-version'], 20)
        run('javac-version', [JDK / 'bin/javac', '-version'], 20)
        run('compile', [JDK / 'bin/javac', '--release', '17', '-proc:none', '-Xlint:all', '-Werror', '-sourcepath', empty, '-classpath', empty, '-d', classes, *sources], 60)
        actual_map = {name: identity(classes / name) for name in class_map}
        assert actual_map == class_map, 'all 209 exact product classes required before invocation'
        actual_sources = {name: identity(inputs / 'product' / name) for name in source_map}
        context = hashlib.sha256(json.dumps({'source_map': actual_sources, 'class_map': actual_map}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        assert context == CONTEXT
        save('actual-product-class-map.json', actual_map)
        save('compile-identity.json', {'source_context': context, 'all_209_exact_matches': True, 'product_sources': 16, 'concrete_B_leaves': 87,
             'default_debug_information_no_explicit_g': True, 'compiler_scope': 'JDK host only; no Android native compilation or runtime'})
        run('independent-controls', [JDK / 'bin/java', '-ea', '-Xmx256m', '-cp', classes, 'dev.mixer.android.IndependentFiniteControls', SOURCE / 'inputs/descriptor.json', D / 'actual-results.tsv', D / 'boundary-frames.txt'], 30)
        results = []
        for line in (D / 'actual-results.tsv').read_text().splitlines():
            method, label, expected, actual, before, after, effects = line.split('\t')
            assert expected == actual and before == after and effects == '0'
            results.append({'subject': 'dev/mixer/android/NativeRenderer#' + method, 'label': label, 'expected': expected, 'actual': actual,
                            'counts_before': json.loads(before), 'counts_after': json.loads(after), 'native_host_effects': int(effects)})
        assert len(results) == 37 and len({(row['subject'], row['label']) for row in results}) == 37
        save('actual-results.json', {'scope': 'independently authored finite direct host controls only', 'source_context': CONTEXT, 'invocations': 37,
             'snapshot_scope': 'Bounded direct relevant objects, inherited fields, states array, scope hooks, all NativeBridge static fields/arrays, exact native host event prefix; no recursive graph claim',
             'original_counts_at_boundary': [2, 2, 3], 'original_final_counts': [0, 0, 0], 'original_edit_completed_after_restores': True, 'rows': results})
        save('execution-receipt.json', {'status': 'passed-independent-finite-host-controls', 'source_context': CONTEXT, 'invocations': 37,
             'all_209_exact_product_classes_reproduced_before_invocations': True, 'native_host_effects_during_calls': 0,
             'original_edit_completed_after_finally_restores': True, 'original_counts': {'at_boundary': [2, 2, 3], 'after_edit': [0, 0, 0]},
             'producer_142_results_reviewed_separately_not_replayed': True, 'physical_native_cleanup_credit': False,
             'native_devices_simulators_emulators_UI_capture_computer_use_process_inventories_started': False,
             'enclosing_callback_exception_allocation_release_authority_and_complete_matrix_accepted': False, 'native_OTA_GA_accepted': False})
    except BaseException as failure:
        save('failure.json', {'type': type(failure).__name__, 'message': str(failure), 'status': 'failed-independent-attempt-no-pass-credit'})
        raise
    finally:
        shutil.rmtree(scratch)
        save('cleanup.json', {'all_started_children_bound_and_reaped': all(command['reaped'] for command in commands),
             'owned_scratch_removed': not scratch.exists(), 'leased_JDK_preserved': True, 'native_instances_started': 0,
             'process_inventories_run': False, 'other_projects_processes_touched': False, 'physical_native_cleanup_credit': False,
             'original_fixture_close_catches_errors': 'Host disposal only; no physical cleanup qualification'})


if __name__ == '__main__':
    main()
