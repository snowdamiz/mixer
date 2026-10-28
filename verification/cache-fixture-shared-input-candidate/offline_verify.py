#!/usr/bin/env python3
"""Audit-limited source/file/mock controls; this never runs the fixture or a child."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
import offline_audit
offline_audit.install(HERE)

import ast
from datetime import datetime, timezone
import hashlib
import io
import json
import os
import tempfile
import types
import unittest
from unittest import mock
import materialize_pack as m
import test_materializer
import test_runner

BASE = m.ROOT / 'verification/swift-cache-state-ci'
REVIEW = m.ROOT / 'verification/cache-fixture-shared-input-review'
EXCLUDED_RUNTIME_CONTROLS = {
    'test_checks_active_under_optimized_python',
    'test_missing_and_failed_commands_keep_raw_receipts',
    'test_timeout_owned_child_group_and_output_cap',
    'test_owned_descendant_group_is_stopped',
    'test_every_child_gets_owned_default_temporary_directory',
    'test_fixture_temporary_override_stays_inside_owned_scratch',
    'test_postflight_deadline_is_terminal_and_preserves_scratch',
    'test_retention_deadline_is_terminal_and_preserves_scratch',
}


def binding(path):
    return {'path': path.relative_to(m.ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': m.sha(path)}


def test_names(path):
    parsed = ast.parse(path.read_bytes())
    return {node.name for node in ast.walk(parsed) if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')}


def main():
    input_paths = [BASE / 'check_cache_state.py', BASE / 'test_runner.py']
    input_paths += sorted(path for path in (BASE / 'pack').rglob('*') if path.is_file())
    input_paths += sorted(path for path in REVIEW.rglob('*') if path.is_file())
    input_paths += [m.ROOT / 'verification/cache-fixture-debug-timeout-investigation/candidate/source/regression/independent_tests.rs']
    input_paths += [HERE / row['path'] for row in m.inventory(HERE, excluded={
        'logs', 'runs', 'control-scratch', 'materialized', '__pycache__'})
        if row['path'] not in {'seal.json', 'offline-controls.json', 'offline-controls.stdout'}]
    input_paths = sorted(set(input_paths))
    before = [binding(path) for path in input_paths]
    m.need(m.sha(BASE / 'check_cache_state.py') == '162b34dcf64fee840c53ead9ff0ee9ab7241741ac9708fbed8ccb697caff2bf3', 'Base runner preimage differs')
    m.need(m.sha(HERE / 'pack-overlay/source/regression/independent_tests.rs') == m.ACCEPTED_SOURCE_SHA256,
           'Accepted overlay source differs')
    original_tests = test_names(BASE / 'test_runner.py')
    candidate_tests = test_names(HERE / 'test_runner.py')
    m.need(original_tests <= candidate_tests and len(candidate_tests - original_tests) == 4,
           'Existing controls removed or unexpected control additions')
    for path in [HERE / 'check_cache_state.py', HERE / 'test_runner.py', HERE / 'materialize_pack.py',
                 HERE / 'test_materializer.py', HERE / 'verify_candidate.py', HERE / 'offline_audit.py']:
        ast.parse(path.read_bytes(), filename=str(path))
    runner = test_runner.r
    m.need((runner.CHILD_SECONDS, runner.ACTIVE_SECONDS, runner.CLEANUP_SECONDS, runner.OUTPUT_CAP)
           == (60, 600, 60, 8 * 1024 * 1024), 'Original command bounds changed')
    m.need((runner.EXPECTED_COMPILER_HOST, runner.EXPECTED_COMPILER_RELEASE)
           == ('aarch64-apple-darwin', '1.98.1'), 'Declared compiler changed')
    inputs = m.verify_inputs()
    selected = sorted(candidate_tests - EXCLUDED_RUNTIME_CONTROLS)
    m.need(EXCLUDED_RUNTIME_CONTROLS <= candidate_tests, 'Pending control inventory differs')
    scratch = HERE / 'control-scratch'
    scratch.mkdir(exist_ok=True)
    stream = io.StringIO()
    result = None
    try:
        with tempfile.TemporaryDirectory(prefix='offline-', dir=scratch) as raw:
            owner = Path(raw).resolve()
            with mock.patch.object(m, 'HERE', owner), mock.patch.object(m, 'MATERIALIZED', owner / 'materialized'):
                m.materialize()
                pack = m.MATERIALIZED / 'pack'
                # Base controls use tempfile's default directory. Keep even their
                # small synthetic files inside this assigned sibling.
                with mock.patch.object(tempfile, 'tempdir', str(owner)), mock.patch.object(runner, 'PACK', pack):
                    suite = unittest.TestSuite(test_runner.RunnerControls(name) for name in selected)
                    raw_usage = types.SimpleNamespace(ru_utime=0.0, ru_stime=0.0, ru_minflt=0, ru_majflt=0)
                    with mock.patch.object(runner.resource, 'getrusage', return_value=raw_usage):
                        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        materializer_result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromModule(test_materializer))
    finally:
        if scratch.exists() and not any(scratch.iterdir()):
            scratch.rmdir()
    after = [binding(path) for path in input_paths]
    m.need(before == after, 'Source/evidence read-set changed')
    m.need(not offline_audit.DENIED, 'Forbidden operation attempted')
    methods = m.load(BASE / 'pack/inventories/methods.json')
    # Compiler identity/sysroot (2), revision/tree before+after (4), 8 lane
    # compile+list pairs (16), all lane groups (25), and 56 library/API commands.
    commands = 2 + 4 + 16 + (7 + len(methods['producer_debug_partition'])) + 56
    report = {
        'schema': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'command': 'python3 -B verification/cache-fixture-shared-input-candidate/offline_verify.py',
        'python': sys.version, 'host_uname': list(os.uname()),
        'scope': 'Audited in-process Python file/source/mock controls only; no compiler, product, Git, process inventory, child, socket, signal, wait, UI, native, capture, held probe or dispatch',
        'status': 'passed-offline-preparation-controls' if result.wasSuccessful() and materializer_result.wasSuccessful() else 'failed',
        'runner_controls_total_preserved': len(original_tests), 'runner_controls_total_candidate': len(candidate_tests),
        'runner_controls_executed': selected, 'runner_controls_executed_count': result.testsRun,
        'runner_runtime_controls_pending': sorted(EXCLUDED_RUNTIME_CONTROLS),
        'materializer_controls_executed_count': materializer_result.testsRun,
        'denied_operation_attempts': offline_audit.DENIED,
        'inputs': inputs, 'readset': before, 'readset_tree_sha256': m.tree(before),
        'readset_postflight_unchanged': before == after,
        'command_budget': {'full_fixture_invocations': 1, 'expected_complete_fixture_child_commands': commands,
                           'per_child_seconds': 60, 'active_seconds': 600, 'cleanup_seconds': 60,
                           'per_stream_output_cap_bytes': 8 * 1024 * 1024, 'automatic_retries': 0},
        'cleanup': {'control_scratch_absent': not scratch.exists(), 'default_materialization_absent': not m.MATERIALIZED.exists(),
                    'no_native_or_capture_process_started': True},
        'pending': ['real compiler selection and compilation', 'all focused runtime/signal controls on CI',
                    'one complete Debug and optimized fixture closure on the declared compiler',
                    'actual phase and reaped-child accounting and cleanup/custody evidence'],
    }
    (HERE / 'offline-controls.stdout').write_text(stream.getvalue())
    m.save(HERE / 'offline-controls.json', report)
    print(json.dumps({key: report[key] for key in ['status', 'runner_controls_executed_count',
          'materializer_controls_executed_count', 'readset_tree_sha256', 'cleanup']}, sort_keys=True))
    m.need(report['status'] == 'passed-offline-preparation-controls', stream.getvalue())


if __name__ == '__main__':
    main()
