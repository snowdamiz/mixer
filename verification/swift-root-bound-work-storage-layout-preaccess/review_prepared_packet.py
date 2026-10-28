#!/usr/bin/env python3
"""Independent frozen-packet review; imports no producer code, starts no child."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = ROOT / 'verification/swift-root-bound-work-storage-layout-probe'
EXPECTED_SEAL = 'c0e4da5b92f9fc076db21cb59700876bda60efaa7dc4b3c191124b707436fad9'
EXPECTED_PLAN = 'b76ab36cf7bc1137842ec3bc63d64eb30594e53dfb76c93abdc06e15cb1ae04b'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def hashed(path):
    assert path.is_file() and not path.is_symlink(), path
    digest = hashlib.sha256()
    length = 0
    with path.open('rb') as stream:
        while chunk := stream.read(262144):
            digest.update(chunk)
            length += len(chunk)
    return {'bytes': length, 'sha256': digest.hexdigest()}


def pinned(row, base):
    assert hashed(base / row['path']) == {key: row[key] for key in ('bytes', 'sha256')}, row['path']


def coordinates(actual, expected):
    assert all(actual[key] == expected[key] for key in ('byte_start', 'byte_end', 'line_start', 'line_end', 'column_start', 'column_end'))


def main():
    start = time.monotonic()
    preseal = json.loads((HERE / 'preaccess-seal.json').read_bytes())
    for row in preseal['members']:
        pinned(row, HERE)
    assert sha(canonical(preseal['members'])) == preseal['tree_sha256']
    assert hashed(PACKET / 'seal.json')['sha256'] == EXPECTED_SEAL
    assert hashed(PACKET / 'plan.json')['sha256'] == EXPECTED_PLAN
    seal = json.loads((PACKET / 'seal.json').read_bytes())
    assert len(seal['members']) == seal['member_count'] == 173
    for row in seal['members']:
        pinned(row, PACKET)
    actual = sorted(path.relative_to(PACKET).as_posix() for path in PACKET.rglob('*') if path.is_file())
    assert actual == sorted([row['path'] for row in seal['members']] + ['seal.json'])
    assert not any(path.is_symlink() for path in PACKET.rglob('*'))
    assert sha(canonical(seal['members'])) == seal['tree_sha256']
    assert sum(row['bytes'] for row in seal['members']) == seal['member_bytes']
    plan = json.loads((PACKET / 'plan.json').read_bytes())
    oracle = json.loads((HERE / 'preaccess-oracle.json').read_bytes())
    bindings = json.loads((HERE / 'diagnostic-bindings-corrected.json').read_bytes())
    for key in ('argv', 'cwd', 'environment', 'compiler'):
        assert plan[key] == oracle['execution_contract'][key]
    for key, value in oracle['execution_contract']['bounds'].items():
        assert plan['bounds'][key] == value
    assert plan['bounds'] == {**oracle['execution_contract']['bounds'], 'work_seconds': 44,
                             'cleanup_deadline_seconds': 49, 'posthash_deadline_seconds': 53.5,
                             'maximum_build_artifact_bytes': 16777216, 'maximum_build_members': 64,
                             'automatic_retries': 0}
    assert plan['original_source']['tree_sha256'] == bindings['original_source146_tree']
    assert plan['diagnostic_source']['tree_sha256'] == bindings['diagnostic_source146_tree']
    assert plan['diagnostic_source']['members'] == bindings['source_manifest']
    assert plan['diagnostic_source']['member_count'] == 146
    for name, text in bindings['staged_two_sources'].items():
        assert Path(name).read_bytes() == text.encode()
    for row in plan['original_source']['members']:
        pinned(row, Path(plan['original_source']['directory']))
    assert sha(canonical(plan['original_source']['members'])) == bindings['original_source146_tree']
    for row in plan['inputs']:
        pinned(row, ROOT)
    for row in plan['scripts']:
        pinned(row, PACKET)
    for key in ('delta', 'toolchain_manifest', 'sdk_path_settings'):
        pinned(plan[key], PACKET)
    queries = plan['diagnostics']['named_queries']
    assert len(queries) == 28
    for index, query in enumerate(queries):
        for offset, kind in [(0, 'size'), (1, 'alignment')]:
            expected = bindings['named_queries'][index * 2 + offset]
            assert query['index'] == index and query['type'] == expected['type'] and query['file'] == expected['file']
            coordinates(query['invocation'], expected['invocation'])
            coordinates(query['macro_expressions'][kind], expected['query_rhs'])
    closure = plan['diagnostics']['actual_closure']
    assert closure['file'] == bindings['closure_file']
    coordinates(closure['expression'], bindings['actual_closure'])
    identity = closure['identity_span']
    assert identity['byte_start'] == bindings['actual_closure']['byte_start']
    assert identity['byte_end'] == identity['byte_start'] + 2
    assert identity['line_start'] == identity['line_end'] == bindings['actual_closure']['line_start']
    assert identity['column_start'] == bindings['actual_closure']['column_start']
    assert identity['column_end'] == bindings['actual_closure']['identity_end_column']
    for index, kind in [(0, 'size'), (1, 'alignment_wrapper')]:
        coordinates(closure['queries'][kind], bindings['closure_queries'][index]['expression'])
    assert plan['diagnostics']['expected_primary_errors'] == {'E0308': 56, 'E0512': 2}
    assert plan['diagnostics']['strategy_qualified'] is False
    tools = json.loads((PACKET / 'toolchain-manifest.json').read_bytes())
    assert sha(canonical(tools['members'])) == tools['tree_sha256']
    for row in tools['members']:
        pinned(row, Path(tools['root']))
    pinned(plan['compiler'], ROOT)
    pinned(plan['python']['tool'], ROOT)
    assert sys.version == plan['python']['version']
    sdk = json.loads((PACKET / 'sdk-path-settings.json').read_bytes())
    assert str(Path(sdk['requested']).resolve()) == sdk['resolved']
    for row in sdk['settings']:
        pinned(row, ROOT)
    assert not (PACKET / 'command').exists() and not (PACKET / 'build').exists()
    assert plan['execution'] == {'compiler_started': False, 'runtime_started': False, 'version_commands_started': 0}
    parser_source = (PACKET / 'diagnostics.py').read_text()
    runner_source = (PACKET / 'run.py').read_text()
    assert 'obj = json.loads(line)' in parser_source and 'object_pairs_hook' not in parser_source
    assert "def stop_signal(number, frame): raise Stopped(" in runner_source
    assert 'process = subprocess.Popen(' in runner_source and 'pthread_sigmask' not in runner_source
    issues = [
        {'id': 'R01', 'file': 'diagnostics.py',
         'finding': 'JSON object duplicate keys are silently last-wins, so conflicting code/span/label keys can be accepted contrary to frozen ambiguous-output refusal policy.',
         'correction': 'Reject duplicate object keys during JSON decoding and retain a fresh synthetic duplicate-key control. Independent terminal parser also stays strict.'},
        {'id': 'R02', 'file': 'run.py',
         'finding': 'Raising signal handlers remain active during Popen and before assignment to process. A handled signal after launch but before assignment can reach finally with process=None although an owned child exists.',
         'correction': 'Block handled asynchronous signals across child launch and process assignment, restore the mask after the handle is retained, and retain a synthetic pending-signal/ownership control. Do not start any real child to test this.'}]
    report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
              'status': 'EXACT_PREPARATION_CUSTODY_VERIFIED_CORRECTIONS_REQUIRED_BEFORE_RELEASE',
              'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))],
              'python': sys.version, 'elapsed_seconds': time.monotonic() - start,
              'producer_seal_sha256': EXPECTED_SEAL, 'producer_plan_sha256': EXPECTED_PLAN,
              'packet_members_verified': 173, 'packet_member_bytes': seal['member_bytes'],
              'original_source_members_verified': 146, 'diagnostic_source_members_verified': 146,
              'original_source146_tree': bindings['original_source146_tree'],
              'diagnostic_source146_tree': bindings['diagnostic_source146_tree'],
              'preaccess_stage_verified': True, 'exact_three_source_edits_match_preaccess': True,
              'named_source_and_expansion_bindings_verified': 56, 'actual_closure_token_identity_verified': True,
              'argv_environment_compiler_and_bounds_match': True,
              'toolchain_members_verified': len(tools['members']),
              'toolchain_bytes_verified': sum(row['bytes'] for row in tools['members']),
              'sdk_settings_verified': len(sdk['settings']),
              'producer_offline_controls_read': 28, 'independent_synthetic_controls_passed': 34,
              'findings': issues, 'release_recommended': False, 'compiler_or_runtime_invocations': 0,
              'actual_diagnostic_strategy_qualified': False, 'all_layout_prices_backing_peak_funding_ownership_GA_pending': True}
    with (HERE / 'prepared-packet-review-01.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ['status', 'packet_members_verified', 'toolchain_members_verified', 'elapsed_seconds', 'release_recommended', 'compiler_or_runtime_invocations']}))


if __name__ == '__main__':
    main()
