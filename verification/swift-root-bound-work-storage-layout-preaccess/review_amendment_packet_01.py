#!/usr/bin/env python3
"""Independent amendment preparation review; no producer imports or replay."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
A = ROOT / 'verification/swift-root-bound-layout-observation-amendment'
W = ROOT / 'verification/swift-root-bound-layout-warning-classification'


def main():
    start = time.monotonic()
    spec = importlib.util.spec_from_file_location('independent_frozen_review_helpers', HERE / 'review_v3_packet.py')
    H = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(H)
    H.packet(A, '298d2f3e9ac0f5ef0abacdeb24996d3a8d1031de02c91cb2cba82a62236a8723', 22)
    assert H.sha((A / 'plan.json').read_bytes()) == '8e4a9684888ac96834a1a584f75d993a2bf463e06b45104444c8af0f50b209ff'
    H.packet(H.OLD, 'c0e4da5b92f9fc076db21cb59700876bda60efaa7dc4b3c191124b707436fad9', 173)
    H.packet(H.V2, '76fda3e073db9bb7408275cf5d8eb494cf491e5a9cd0a894ba8cca35171127f8', 16)
    H.packet(H.V3, '898e88217ab2f04505d09571dbd8748b85cabc3b443a0dde12c47f4c800ed72c', 17, False)
    for name, digest, count in [
        ('preaccess-seal.json', '001ec6fbfb69a6c784083615323df670c9d932ecace8fd598fc68447867d9d67', 22),
        ('review-01-seal.json', 'edbf7e50d0d8b1847ac75d391d47ba6a16c17e73e6811b153203b8cafe5fc15c', 5),
        ('review-02-seal.json', '8409755f4e955a4ccdc2132eeea5b3218aee44fbe87127d288f434360852a0fa', 5),
        ('review-03-seal.json', '373f849c3ce8aafa861ca4c9585d9521794cd85f43259df47ef4858fa0bcb753', 5),
        ('terminal-v3-review-seal.json', '4e42f67ff992fe7f3c9192b638ea9960eee4d3787bf5eeb40443113f5592760e', 5),
        ('amendment-preaccess-seal.json', 'a3c35353d4749fac7c814489596e8927cf0c268d72fcb41b6e162174a9334b0a', 10)]:
        H.stage(name, digest, count)
    assert H.sha((W / 'seal.json').read_bytes()) == '39976085aa6fd3cebf5c12bb6376358c46b11223df8347b8fb70ef12c20be5ab'
    warning_seal = H.load(W / 'seal.json')
    assert len(warning_seal['members']) == 9
    for row in warning_seal['members']:
        H.pin(row, W)
    assert sorted(path.relative_to(W).as_posix() for path in W.rglob('*') if path.is_file()) == sorted([row['path'] for row in warning_seal['members']] + ['seal.json'])
    plan = H.load(A / 'plan.json')
    policy = H.load(A / 'policy.json')
    independent = H.load(HERE / 'amendment-independent-policy.json')
    v3 = H.load(H.V3 / 'plan.json')
    terminal = H.load(HERE / 'terminal-v3-review.json')
    for row in plan['scripts']:
        H.pin(row, A)
    for row in plan['inputs']:
        H.pin(row, ROOT)
    H.pin(plan['policy'], A)
    assert plan['saved_stderr'] == independent['saved_stderr']
    assert plan['source146_tree'] == independent['source146_tree']
    assert plan['diagnostic146_tree'] == independent['diagnostic146_tree']
    for actual, expected in zip(policy['warning_records'], independent['whole_exact_warnings']):
        assert actual['record_index'] + 1 == expected['record_line']
        assert H.canonical(actual['record']) == H.canonical(expected['exact_record'])
    assert len(policy['warning_records']) == 3
    for actual, expected in zip(plan['closure_symbols_derived_from_frozen_full_expressions'], independent['closure_function_spans']):
        assert actual['operation'] == expected['operation']
        assert actual['symbol'] == expected['symbol_span']
        assert all(actual['expression'][key] == value for key, value in expected['complete_expression_span'].items())
        assert actual['expression']['text'] == expected['complete_expression']
    assert len(plan['closure_symbols_derived_from_frozen_full_expressions']) == 2
    for row in terminal['saved_command_members']:
        H.pin(row, H.V3 / 'command')
    assert not (H.OLD / 'build').exists()
    raw = (H.V3 / 'command/stderr').read_bytes()
    assert H.sha(raw) == independent['saved_stderr']['sha256'] and len(raw) == independent['saved_stderr']['bytes']
    # Literal summaries only are joined here; the actual 58-error stream is
    # never supplied to any amended parser during preparation review.
    lines = raw.splitlines()
    assert len(policy['summaries']) == 3
    for index, row in enumerate(policy['summaries']):
        assert row['record_index'] == 61 + index
        actual = json.loads(lines[row['record_index']], object_pairs_hook=H.unique_object)
        assert H.canonical(row['record']) == H.canonical(actual)
        assert row['raw_record_sha256'] == H.sha(lines[row['record_index']])
    assert policy['summaries'][0]['record']['message'] == independent['required_summary']
    assert [row['record']['message'] for row in policy['summaries'][1:]] == independent['required_failure_notes']
    for field, base in [('original_source', Path(v3['original_source']['directory'])),
                        ('diagnostic_source', H.OLD / 'source/vm')]:
        rows = v3[field]['members']
        assert len(rows) == 146 and H.sha(H.canonical(rows)) == v3[field]['tree_sha256']
        assert sorted(path.relative_to(base).as_posix() for path in base.rglob('*') if path.is_file()) == sorted(row['path'] for row in rows)
        for row in rows:
            H.pin(row, base)
    tools = H.load(H.OLD / 'toolchain-manifest.json')
    for row in tools['members']:
        H.pin(row, Path(tools['root']))
    H.pin(v3['compiler'], ROOT)
    H.pin(v3['python']['tool'], ROOT)
    assert sys.version == v3['python']['version']
    for row in H.load(H.OLD / 'sdk-path-settings.json')['settings']:
        H.pin(row, ROOT)
    parser = (A / 'parser.py').read_text()
    runner = (A / 'run.py').read_text()
    read = runner.index("stderr=(V3/'command/stderr').read_bytes()")
    path_hash = runner.index("need(hashed(V3/'command/stderr',deadline)==plan['saved_stderr']", read)
    parse = runner.index('candidate=parse_diagnostics(stderr,stdout,1', path_hash)
    assert read < path_hash < parse
    assert 'sha(stderr)' not in runner and 'len(stderr)' not in runner
    assert 'source_spans_verified' in parser and 'span_count==346' not in parser and 'span_count == 346' not in parser
    controls = H.load(A / 'controls-result.json')
    assert controls['positive_synthetic_streams'] == 1 and len(controls['adverse_controls']) == controls['adverse_controls_passed'] == 116
    assert all(row['rejected'] is True for row in controls['adverse_controls'])
    assert controls['actual_saved_raw_parser_calls'] == 0
    assert H.load(A / 'commands/final-offline/receipt.json')['error'] == {'message': "'member_count'", 'type': 'KeyError'}
    assert H.load(A / 'commands/final-offline-2/receipt.json')['exit'] == 0
    assert plan['execution']['actual_saved_raw_parser_calls'] == 0
    assert plan['bounds'] == {'actual_saved_raw_parser_calls': 1, 'automatic_retries': 0, 'child_workloads': 0,
        'compiler_invocations': 0, 'parse_deadline_seconds': 45, 'posthash_deadline_seconds': 51, 'preflight_seconds': 20, 'wall_seconds': 55}
    assert not (A / 'actual').exists()
    report = {
        'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'status': 'AMENDMENT_PREPARATION_CUSTODY_VERIFIED_MEMORY_INPUT_PIN_CORRECTION_REQUIRED',
        'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))], 'python': sys.version,
        'script_sha256': H.sha(Path(__file__).read_bytes()), 'elapsed_seconds': time.monotonic() - start,
        'producer_seal_sha256': H.sha((A / 'seal.json').read_bytes()),
        'producer_plan_sha256': H.sha((A / 'plan.json').read_bytes()), 'producer_members_verified': 22,
        'independent_preaccess_seal_sha256': H.sha((HERE / 'amendment-preaccess-seal.json').read_bytes()),
        'original173_v2_16_v3prep17_source146_toolchain67_and_saved_command_unchanged': True,
        'whole_exact_three_warning_policy_matches': True,
        'two_exact_source_reconstructed_function_symbol_bindings_match': True,
        'whole_exact_58_error_3_warning_summary_and_two_notes_match': True,
        'original_refusal_and_numeric_constraints_preserved': True,
        'producer_synthetic_controls_read_not_replayed': 116,
        'finding': {'id': 'A01', 'file': 'run.py',
            'detail': 'The adapter reads stderr into memory, then hashes the path separately. A path restoration before that hash and posthash can satisfy custody while the earlier bytes supplied to the parser differ from the exact saved stream.',
            'required': 'Read at most pinned byte length plus one, require exact in-memory length and SHA256 before incrementing actual parser calls or parsing; independently retain path pre/post custody checks.',
            'synthetic_expectations': ['exact bounded memory accepted by input guard', 'changed memory with separately correct path hash refuses before parser',
                'short/truncated memory refuses before parser', 'overlong/overflow read refuses before parser', 'input failure leaves actual parser calls zero']},
        'geometry_difference': {'independent_requirement': 346, 'producer_requirement': 'Validate every recognized span and report count; no exact count guard.',
            'producer_positive_synthetic_geometry_count_by_source_construction': 178,
            'recommendation': 'Add explicit required346 guard and construct secondary-span synthetic fixture to exercise it, matching the frozen independent oracle. Exact raw memory pin would otherwise constrain the sole saved input; independent acceptance still requires346.'},
        'root_offline_release_recommended': False, 'actual_amended_saved_raw_parser_calls': 0,
        'producer_parser_checker_or_controls_replayed': False,
        'compiler_runtime_version_native_ui_capture_process_queries': 0,
        'original_oracle_accepted': False, 'amended_actual_observation_accepted': False,
        'all_prices_backing_peak_funding_ownership_native_FieldLog_OTA_GA_pending': True,
        'cleanup': 'No compiler/native/capture process, actual output or build artifact created; no such cleanup owed.'}
    with (HERE / 'amendment-packet-review-01.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'producer_members_verified', 'root_offline_release_recommended',
          'actual_amended_saved_raw_parser_calls', 'compiler_runtime_version_native_ui_capture_process_queries')}))


if __name__ == '__main__':
    main()
