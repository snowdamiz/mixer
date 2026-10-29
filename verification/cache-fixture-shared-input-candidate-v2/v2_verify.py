#!/usr/bin/env python3
"""Bounded v2 delta checks and replay of six existing pure integration controls."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import offline_audit
offline_audit.install(HERE)

from datetime import datetime, timezone
import hashlib
import io
import json
import tempfile
import types
import unittest
from unittest import mock
import materialize_pack as m
import test_runner

OLD = ROOT / 'verification/cache-fixture-shared-input-candidate'


def main():
    old_seal = m.load(OLD / 'seal.json')
    m.need(m.sha(OLD / 'seal.json') == 'db6ba0fcb4c66f5a38dd0f93ce9dc381a869b12fbf8eda7ecb8f5b3f57bfeca7', 'Original seal differs')
    for row in old_seal['members']:
        m.need(m.sha(OLD / row['path']) == row['sha256'], 'Original candidate changed')
    old_manifest = m.load(OLD / 'overlay-manifest.json')
    new_manifest = m.load(HERE / 'overlay-manifest.json')
    m.need((OLD / 'check_cache_state.py').read_text().replace(old_manifest['candidate_manifest_sha256'], new_manifest['candidate_manifest_sha256'])
           == (HERE / 'check_cache_state.py').read_text(), 'Runner logic changed')
    m.need((OLD / 'materialize_pack.py').read_text().replace(m.sha(OLD / 'overlay-manifest.json'), m.sha(HERE / 'overlay-manifest.json'))
           == (HERE / 'materialize_pack.py').read_text(), 'Materializer logic changed')
    expected_control = (OLD / 'test_runner.py').read_text().replace('capture_output=True,timeout=15);self.assertNotEqual(p.returncode,0)',
                                          'capture_output=True,timeout=15,cwd=HERE);self.assertNotEqual(p.returncode,0)')
    m.need(expected_control == (HERE / 'test_runner.py').read_text(), 'Unexpected runner control change')
    for path in ['test_materializer.py', 'offline_audit.py', 'command-budget.json',
                 'pack-overlay/inventories/bindings.json', 'pack-overlay/source/regression/independent_tests.rs']:
        m.need((OLD / path).read_bytes() == (HERE / path).read_bytes(), 'Unexpected change: ' + path)
    m.need((OLD / 'pack-overlay/inventories/source-roster.json').read_text()
           .replace('verification/cache-fixture-shared-input-candidate/pack-overlay/', 'verification/cache-fixture-shared-input-candidate-v2/pack-overlay/')
           == (HERE / 'pack-overlay/inventories/source-roster.json').read_text(), 'Unexpected source roster change')
    expected_workflow = (OLD / 'workflow/cache-fixture-shared-input-diagnostic.yml').read_text() \
        .replace('name: Shared-input cache fixture diagnostic', 'name: Shared-input cache fixture controls v2') \
        .replace('shared-input-cache-fixture-${{ github.ref }}', 'shared-input-cache-fixture-controls-v2-${{ github.ref }}') \
        .replace('cache-fixture-shared-input-candidate', 'cache-fixture-shared-input-candidate-v2') \
        .replace('cache-fixture-shared-input-diagnostic.yml', 'cache-fixture-shared-input-controls-v2.yml') \
        .replace('name: cache-fixture-shared-input-${{ github.sha }}', 'name: cache-fixture-shared-input-controls-v2-${{ github.sha }}')
    m.need(expected_workflow == (HERE / 'workflow/cache-fixture-shared-input-controls-v2.yml').read_text(), 'Unexpected workflow change')
    inputs = m.verify_inputs()
    r = test_runner.r
    m.need((r.CHILD_SECONDS, r.ACTIVE_SECONDS, r.CLEANUP_SECONDS, r.OUTPUT_CAP) == (60, 600, 60, 8388608), 'Bounds changed')
    m.need((r.EXPECTED_COMPILER_HOST, r.EXPECTED_COMPILER_RELEASE) == ('aarch64-apple-darwin', '1.98.1'), 'Compiler changed')
    budget = m.load(HERE / 'command-budget.json')
    m.need(budget['fixture_child_commands'] == 103 and budget['focused_runner_controls'] == 36
           and budget['context_cases_per_invocation'] == 1003 and budget['automatic_retries'] == 0, 'Roster changed')
    # Replay the exact existing class/helper. Its old main/seal acceptance is
    # never called; this is a same-agent test replay, not independent review.
    review_source_path = ROOT / 'verification/cache-fixture-overlay-independent/review.py'
    source = review_source_path.read_text()
    needle = "CANDIDATE = ROOT / 'verification/cache-fixture-shared-input-candidate'"
    m.need(source.count(needle) == 1, 'Independent control import binding differs')
    adapted = source.replace(needle, "CANDIDATE = ROOT / 'verification/cache-fixture-shared-input-candidate-v2'")
    module = types.ModuleType('v2_existing_integration_replay')
    module.__file__ = str(HERE / 'existing_integration_replay.py')
    exec(compile(adapted, str(review_source_path), 'exec'), module.__dict__)
    scratch = HERE / 'scratch'
    scratch.mkdir()
    stream = io.StringIO()
    try:
        with tempfile.TemporaryDirectory(prefix='pure-controls-', dir=scratch) as raw:
            with mock.patch.object(tempfile, 'tempdir', raw):
                result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
                    unittest.defaultTestLoader.loadTestsFromTestCase(module.IndependentIntegrationControls))
    finally:
        scratch.rmdir()
    m.need(result.testsRun == 6 and result.wasSuccessful(), stream.getvalue())
    m.need(not offline_audit.DENIED, 'Forbidden operation attempted')
    m.need(m.verify_inputs() == inputs, 'Input binding changed')
    m.need(all(m.sha(OLD / row['path']) == row['sha256'] for row in old_seal['members']), 'Original candidate changed')
    report = {'schema': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
              'command': 'python3 -B verification/cache-fixture-shared-input-candidate-v2/v2_verify.py',
              'python': sys.version, 'scope': 'Allowed-delta checks plus same-agent replay of six existing in-process source/file/mock controls; no new independent review',
              'status': 'passed-v2-pure-integration-controls', 'control_count': result.testsRun,
              'existing_control_source': {'path': str(review_source_path.relative_to(ROOT)), 'sha256': hashlib.sha256(source.encode()).hexdigest()},
              'inputs': inputs, 'accepted_rust_source_unchanged': True, 'original_candidate_preserved': True,
              'runner_logic_changed': False, 'materializer_logic_changed': False,
              'test_change': 'cwd=HERE only in optimized-Python subprocess control',
              'controls_36_fixture_103_vectors_1003_and_limits_preserved': True,
              'denied_operation_attempts': offline_audit.DENIED, 'scratch_absent': not scratch.exists(),
              'actual_compiler_or_optimized_subprocess_executed': False, 'remote_dispatch_or_retry': False}
    (HERE / 'v2-integration-controls.stdout').write_text(stream.getvalue())
    m.save(HERE / 'v2-integration-controls.json', report)
    print(json.dumps({'status': report['status'], 'control_count': result.testsRun, 'denied_operation_attempts': offline_audit.DENIED}))


if __name__ == '__main__':
    main()
