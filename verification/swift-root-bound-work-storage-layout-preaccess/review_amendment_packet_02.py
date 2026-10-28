#!/usr/bin/env python3
"""Focused independent V2 custody/source review; no producer imports or replay."""
from datetime import datetime, timezone
import difflib
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
A = ROOT / 'verification/swift-root-bound-layout-observation-amendment'
V2 = ROOT / 'verification/swift-root-bound-layout-observation-amendment-v2'


def main():
    start = time.monotonic()
    spec = importlib.util.spec_from_file_location('frozen_independent_review_helpers_v2', HERE / 'review_v3_packet.py')
    H = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(H)
    H.packet(A, '298d2f3e9ac0f5ef0abacdeb24996d3a8d1031de02c91cb2cba82a62236a8723', 22)
    H.packet(V2, '409a1e4fcea8ac54cd7e96b4ab179bab397f4e49c19d019b1751307ab8e3d8a3', 16)
    assert H.sha((V2 / 'plan.json').read_bytes()) == '96a08ff362f1e5a4f7b12a51d41873a27c79ddedf585cfdfe9bd046b0c735130'
    H.stage('amendment-preaccess-seal.json', 'a3c35353d4749fac7c814489596e8927cf0c268d72fcb41b6e162174a9334b0a', 10)
    H.stage('amendment-review-01-seal.json', 'c0daaec0379bc1b51aa89669ccf617fa0eb78bba222b88e15365fa33c1331186', 5)
    H.stage('terminal-v3-review-seal.json', '4e42f67ff992fe7f3c9192b638ea9960eee4d3787bf5eeb40443113f5592760e', 5)
    H.stage('preaccess-seal.json', '001ec6fbfb69a6c784083615323df670c9d932ecace8fd598fc68447867d9d67', 22)
    old, new = H.load(A / 'plan.json'), H.load(V2 / 'plan.json')
    preserved = ['bounds', 'candidate_layouts_require_complete_amended_stream_and_later_review', 'closed_summary_policy',
        'closed_warning_policy', 'closure_symbols_derived_from_frozen_full_expressions', 'diagnostic146_tree', 'execution',
        'layouts_prices_backing_peak_funding_full_ownership_native_FieldLog_OTA_GA_accepted', 'original_contract_accepted',
        'policy', 'python', 'retrospective_policy', 'root_release_required', 'saved_command_directory', 'saved_command_scope',
        'saved_query_plan_sha256', 'saved_stderr', 'source146_tree', 'source_revision_from_pinned_historical_root_release',
        'unchanged_refusals', 'warning_baseline_justification']
    for field in preserved:
        assert old[field] == new[field], field
    assert new['required_source_span_count'] == 346
    assert (V2 / 'policy.json').read_bytes() == (A / 'policy.json').read_bytes()
    assert set(row['path'] for row in old['inputs']).issubset({row['path'] for row in new['inputs']})
    for row in new['inputs']:
        H.pin(row, ROOT)
    for row in new['scripts']:
        H.pin(row, V2)
    H.pin(new['policy'], V2)
    patch = ''
    for name in ['check.py', 'parser.py', 'controls.py', 'run.py', 'prepare.py', 'verify_and_seal.py']:
        patch += ''.join(difflib.unified_diff((A / name).read_text().splitlines(True), (V2 / name).read_text().splitlines(True), fromfile='amendment/' + name, tofile='amendment-v2/' + name))
    patch += ''.join(difflib.unified_diff([], (V2 / 'input_bytes.py').read_text().splitlines(True), fromfile='/dev/null', tofile='amendment-v2/input_bytes.py'))
    assert patch.encode() == (V2 / 'correction-delta.patch').read_bytes()
    expected_parser = (A / 'parser.py').read_text().replace('    layouts=[]\n', "    need(span_count==346,'complete-346-source-span-cardinality')\n    layouts=[]\n", 1)
    assert (V2 / 'parser.py').read_text() == expected_parser
    reader = (V2 / 'input_bytes.py').read_text()
    read = reader.index("raw=handle.read(expected['bytes']+1)")
    assert read < reader.index("type(raw) is bytes") < reader.index("len(raw)==expected['bytes']") < reader.index("sha(raw)==expected['sha256']") < reader.index('return raw')
    runner = (V2 / 'run.py').read_text()
    pre = runner.index("need(hashed(V3/'command/stderr',deadline)==plan['saved_stderr']")
    stderr = runner.index("stderr=read_pinned_bytes(V3/'command/stderr',plan['saved_stderr'],deadline)")
    stdout = runner.index("stdout=read_pinned_bytes(V3/'command/stdout',{'bytes':0,'sha256':sha(b'')},deadline)")
    parse = runner.index('calls+=1;candidate=parse_diagnostics(stderr,stdout,1')
    post = runner.index('check(args.plan_sha256,start+51)', parse)
    assert pre < stderr < stdout < parse < post
    assert runner.count('candidate=parse_diagnostics(') == 1
    controls = H.load(V2 / 'controls-result.json')
    previous = H.load(A / 'controls-result.json')
    assert len(controls['adverse_controls']) == controls['adverse_controls_passed'] == 126
    assert all(row['rejected'] is True for row in controls['adverse_controls'])
    assert {row['name'] for row in previous['adverse_controls']}.issubset({row['name'] for row in controls['adverse_controls']})
    assert len(controls['positive_memory_controls']) == 2 and all(row['passed'] is True for row in controls['positive_memory_controls'])
    assert controls['positive_synthetic_span_count'] == 346 and controls['total_controls'] == 128
    assert controls['actual_saved_raw_parser_calls'] == 0
    receipt = H.load(V2 / 'commands/final-offline/receipt.json')
    assert receipt['exit'] == 0 and receipt['error'] is None and receipt['actual_saved_raw_parser_calls'] == 0
    terminal = H.load(HERE / 'terminal-v3-review.json')
    H.packet(H.OLD, 'c0e4da5b92f9fc076db21cb59700876bda60efaa7dc4b3c191124b707436fad9', 173)
    H.packet(H.V2, '76fda3e073db9bb7408275cf5d8eb494cf491e5a9cd0a894ba8cca35171127f8', 16)
    H.packet(H.V3, '898e88217ab2f04505d09571dbd8748b85cabc3b443a0dde12c47f4c800ed72c', 17, False)
    for row in terminal['saved_command_members']:
        H.pin(row, H.V3 / 'command')
    vp = H.load(H.V3 / 'plan.json')
    for field, base in [('original_source', Path(vp['original_source']['directory'])), ('diagnostic_source', H.OLD / 'source/vm')]:
        rows = vp[field]['members']
        assert len(rows) == 146 and H.sha(H.canonical(rows)) == vp[field]['tree_sha256']
        for row in rows:
            H.pin(row, base)
    tools = H.load(H.OLD / 'toolchain-manifest.json')
    for row in tools['members']:
        H.pin(row, Path(tools['root']))
    H.pin(vp['compiler'], ROOT)
    H.pin(vp['python']['tool'], ROOT)
    assert sys.version == vp['python']['version']
    for row in H.load(H.OLD / 'sdk-path-settings.json')['settings']:
        H.pin(row, ROOT)
    assert not (H.OLD / 'build').exists() and not (A / 'actual').exists() and not (V2 / 'actual').exists()
    report = {
        'schema': 2, 'at': datetime.now(timezone.utc).isoformat(),
        'status': 'V2_AMENDMENT_MEMORY_PIN_AND_346_GUARD_VERIFIED_ONE_OFFLINE_RAW_CALL_RECOMMENDED',
        'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))], 'python': sys.version,
        'script_sha256': H.sha(Path(__file__).read_bytes()), 'elapsed_seconds': time.monotonic() - start,
        'producer_v2_seal_sha256': H.sha((V2 / 'seal.json').read_bytes()),
        'producer_v2_plan_sha256': H.sha((V2 / 'plan.json').read_bytes()), 'producer_v2_members_verified': 16,
        'prior_amendment22_and_all_previous_source_raw_custody_verified': True,
        'complete_seven_file_delta_reconstructed': True, 'literal_policy_byte_identical': True,
        'all_previous_numeric_warning_symbol_summary_guards_unchanged': True,
        'A01_closed': 'One pinnedlength+1 read per input; exact returned bytes type/length/SHA checks complete for stderr and stdout before call increment and parser; path pre/post custody remains.',
        'explicit_346_span_requirement_closed': True,
        'producer_retained_adverse_controls_read': 116, 'producer_new_adverse_controls_read': 10,
        'producer_positive_memory_controls_read': 2, 'producer_positive_synthetic_geometries': 346,
        'producer_checker_parser_or_controls_replayed': False,
        'root_offline_release_recommended': True,
        'release_scope': 'Root alone may release ONE exact V2 offline saved-raw parse, no retry, under 20/45/51/55-second bounds. No compiler or child. Candidate layouts remain unaccepted until independent/root review.',
        'actual_amended_saved_raw_parser_calls': 0, 'compiler_runtime_version_native_ui_capture_process_queries': 0,
        'original_oracle_accepted': False, 'amended_actual_observation_accepted': False,
        'all_prices_backing_peak_funding_ownership_native_FieldLog_OTA_GA_pending': True,
        'cleanup': 'No compiler/native/capture process, actual output or generated build artifact created; no such cleanup owed.'}
    with (HERE / 'amendment-packet-review-02.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'producer_v2_members_verified', 'root_offline_release_recommended',
          'actual_amended_saved_raw_parser_calls', 'compiler_runtime_version_native_ui_capture_process_queries')}))


if __name__ == '__main__':
    main()
