#!/usr/bin/env python3
"""Independent V3 custody/delta review. No producer imports, replay or child."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'verification/swift-root-bound-work-storage-layout-probe'
V2 = ROOT / 'verification/swift-root-bound-work-storage-layout-probe-v2'
V3 = ROOT / 'verification/swift-root-bound-work-storage-layout-probe-v3'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, 'duplicate object key'
        result[key] = value
    return result


def load(path):
    return json.loads(path.read_bytes(), object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def hashed(path):
    assert path.is_file() and not path.is_symlink(), path
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        while chunk := stream.read(262144):
            digest.update(chunk)
            size += len(chunk)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def pin(row, base):
    assert hashed(base / row['path']) == {key: row[key] for key in ('bytes', 'sha256')}, row['path']


def packet(base, expected, count, closure=True):
    assert hashed(base / 'seal.json')['sha256'] == expected
    seal = load(base / 'seal.json')
    assert len(seal['members']) == seal['member_count'] == count
    assert len({row['path'] for row in seal['members']}) == count
    assert sha(canonical(seal['members'])) == seal['tree_sha256']
    assert sum(row['bytes'] for row in seal['members']) == seal['member_bytes']
    for row in seal['members']:
        pin(row, base)
    if closure:
        assert not any(path.is_symlink() for path in base.rglob('*'))
        assert sorted(path.relative_to(base).as_posix() for path in base.rglob('*') if path.is_file()) == sorted([row['path'] for row in seal['members']] + ['seal.json'])
    return seal


def stage(name, expected, count):
    assert hashed(HERE / name)['sha256'] == expected
    seal = load(HERE / name)
    assert len(seal['members']) == seal['member_count'] == count
    assert sha(canonical(seal['members'])) == seal['tree_sha256']
    for row in seal['members']:
        pin(row, HERE)
    return seal


def main():
    started = time.monotonic()
    packet(OLD, 'c0e4da5b92f9fc076db21cb59700876bda60efaa7dc4b3c191124b707436fad9', 173)
    packet(V2, '76fda3e073db9bb7408275cf5d8eb494cf491e5a9cd0a894ba8cca35171127f8', 16)
    frozen = packet(V3, '898e88217ab2f04505d09571dbd8748b85cabc3b443a0dde12c47f4c800ed72c', 17)
    assert sha((V3 / 'plan.json').read_bytes()) == '95e3ebb57acc3c5ea9e7baac1f657c05ae36ffc957d86b77b38231f4480f958e'
    stage('preaccess-seal.json', '001ec6fbfb69a6c784083615323df670c9d932ecace8fd598fc68447867d9d67', 22)
    stage('review-01-seal.json', 'edbf7e50d0d8b1847ac75d391d47ba6a16c17e73e6811b153203b8cafe5fc15c', 5)
    stage('review-02-seal.json', '8409755f4e955a4ccdc2132eeea5b3218aee44fbe87127d288f434360852a0fa', 5)
    stage('v3-expectations-seal.json', '9356fbbb77e0b53a2a76b3dc0f1ab9ba9fd20beb746409825638e6a22706ccad', 4)
    expectations = load(HERE / 'v3-preaccess-expectations.json')
    assert expectations['v3_packet_accessed'] is False and len(expectations['independent_review_cases']) == 11
    old, prior, plan = [load(directory / 'plan.json') for directory in (OLD, V2, V3)]
    preserved = ['argv', 'cwd', 'environment', 'original_source', 'diagnostic_source', 'diagnostics', 'bounds',
                 'compiler', 'python', 'toolchain_manifest', 'toolchain_version', 'sdk_path_settings', 'inputs',
                 'delta', 'execution', 'root_release_required', 'pending', 'all_price_layout_backing_peak_funding_ownership_GA_authority']
    for name in preserved:
        assert plan[name] == prior[name] == old[name], name
    assert plan['argv_sha256_canonical_JSON'] == sha(canonical(plan['argv']))
    assert plan['environment_sha256_canonical_JSON'] == sha(canonical(plan['environment']))
    oracle = load(HERE / 'preaccess-oracle.json')
    for name in ('argv', 'cwd', 'environment', 'compiler'):
        assert plan[name] == oracle['execution_contract'][name], name
    assert plan['bounds'] == {**oracle['execution_contract']['bounds'], 'work_seconds': 44,
        'cleanup_deadline_seconds': 49, 'posthash_deadline_seconds': 53.5,
        'maximum_build_artifact_bytes': 16777216, 'maximum_build_members': 64, 'automatic_retries': 0}
    bindings = load(HERE / 'diagnostic-bindings-corrected.json')
    assert plan['original_source']['tree_sha256'] == bindings['original_source146_tree']
    assert plan['diagnostic_source']['tree_sha256'] == bindings['diagnostic_source146_tree']
    assert plan['diagnostic_source']['members'] == bindings['source_manifest']
    for name, raw in bindings['staged_two_sources'].items():
        assert Path(name).read_bytes() == raw.encode()
    for key, base in [('original_source', Path(plan['original_source']['directory'])),
                      ('diagnostic_source', OLD / 'source/vm')]:
        rows = plan[key]['members']
        assert len(rows) == 146
        assert sha(canonical(rows)) == plan[key]['tree_sha256']
        assert not any(path.is_symlink() for path in base.rglob('*'))
        assert sorted(path.relative_to(base).as_posix() for path in base.rglob('*') if path.is_file()) == sorted(row['path'] for row in rows)
        for row in rows:
            pin(row, base)
    for row in plan['inputs']:
        pin(row, ROOT)
    for row in plan['scripts']:
        pin(row, V3)
    for name in ('toolchain_manifest', 'sdk_path_settings', 'delta'):
        pin(plan[name], OLD)
    tools = load(OLD / 'toolchain-manifest.json')
    assert sha(canonical(tools['members'])) == tools['tree_sha256']
    for row in tools['members']:
        pin(row, Path(tools['root']))
    pin(plan['compiler'], ROOT)
    pin(plan['python']['tool'], ROOT)
    assert sys.version == plan['python']['version']
    sdk = load(OLD / 'sdk-path-settings.json')
    assert str(Path(sdk['requested']).resolve()) == sdk['resolved']
    for row in sdk['settings']:
        pin(row, ROOT)
    patch = ''
    for name in ['check.py', 'controls.py', 'diagnostics.py', 'run.py', 'launch.py', 'strict_json.py']:
        patch += ''.join(difflib.unified_diff((V2 / name).read_text().splitlines(True), (V3 / name).read_text().splitlines(True), fromfile='v2/' + name, tofile='v3/' + name))
    patch += ''.join(difflib.unified_diff([], (V3 / 'publication.py').read_text().splitlines(True), fromfile='/dev/null', tofile='v3/publication.py'))
    assert patch.encode() == (V3 / 'correction-delta.patch').read_bytes()
    assert (V3 / 'diagnostics.py').read_bytes() == (V2 / 'diagnostics.py').read_bytes()
    assert (V3 / 'strict_json.py').read_bytes() == (V2 / 'strict_json.py').read_bytes()
    launch = (V3 / 'launch.py').read_text()
    runner = (V3 / 'run.py').read_text()
    publication = (V3 / 'publication.py').read_text()
    # These assertions retain exact supporting source-order facts; human source
    # review, not their presence alone, establishes the recommendation.
    begin = launch[launch.index('    def begin_publication('):launch.index('    def start(')]
    assert begin.index('self.publication_cutoff = True') < begin.index('self.cutoff_monotonic = self.clock()') < begin.index('self.frozen_pre_cutoff_pending = tuple(self.pending)')
    handler = launch[launch.index('    def handle_signal('):launch.index('    def raise_pending(')]
    assert handler.index('if self.publication_cutoff:') < handler.index('return') < handler.index('self.pending.append(')
    assert 'min(self.post_cutoff_signal_count + 1, 2147483647)' in handler
    assert 'self.frozen_pre_cutoff_pending if self.publication_cutoff' in launch
    assert publication.index('cutoff = launch.begin_publication()') < publication.index('launch.record_interruption_failure(failures)')
    assert publication.index("writer(out / 'diagnostic-observation.json'") < publication.index('receipt = make_receipt(') < publication.index("writer(out / 'receipt.json'")
    final = runner[runner.index("phase = 'finite-publication'"):]
    assert all(token not in final for token in ('hash_file(', 'check(', 'parse(', 'Popen(', 'stop_owned(', 'cleanup_build('))
    assert runner.count('subprocess.Popen(') == 1
    writer = runner[runner.index('def write_once('):runner.index('def absent(')]
    assert writer.index("with staged.open('xb')") < writer.index('runtime evidence staged-write deadline') < writer.index('os.link(staged, path)')
    controls = load(V3 / 'controls-result.json')
    assert len(controls['controls']) == 64 and controls['actual_layout_strategy_qualified'] is False
    assert all(row.get('passed') is True or row.get('rejected') is True for row in controls['controls'])
    receipt = load(V3 / 'commands/final-offline/receipt.json')
    assert receipt['exit'] == 0 and receipt['error'] is None
    assert receipt['compiler_runtime_or_child_processes_started'] == 0
    for directory in (OLD, V2, V3):
        assert not (directory / 'command').exists()
    assert not (OLD / 'build').exists()
    report = {
        'schema': 3, 'at': datetime.now(timezone.utc).isoformat(),
        'status': 'V3_FROZEN_CUSTODY_AND_FINITE_CUTOFF_PUBLICATION_REVIEWED_ROOT_ONE_COMMAND_RELEASE_RECOMMENDED',
        'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))],
        'python': sys.version, 'elapsed_seconds': time.monotonic() - started,
        'script_sha256': sha(Path(__file__).read_bytes()),
        'producer_v3_seal_sha256': sha((V3 / 'seal.json').read_bytes()),
        'producer_v3_plan_sha256': sha((V3 / 'plan.json').read_bytes()),
        'v3_members_verified': 17, 'v3_member_bytes': frozen['member_bytes'],
        'original173_and_v2_16_complete_custody_verified': True,
        'frozen_preaccess_review32_and_expectation4_members_unchanged': True,
        'original_and_diagnostic146_members_and_trees_verified': True,
        'source146_tree': bindings['original_source146_tree'],
        'diagnostic146_tree': bindings['diagnostic_source146_tree'],
        'exact_two_changed_diagnostic_sources_match_preaccess_reconstruction': True,
        'source_queries_argv_environment_toolchain_bounds_preserved': True,
        'toolchain_members_verified': len(tools['members']),
        'toolchain_bytes_verified': sum(row['bytes'] for row in tools['members']),
        'sdk_settings_verified': len(sdk['settings']),
        'complete_seven_file_delta_reconstructed': True,
        'R01_strict_JSON_remains_closed': True, 'R02_launch_cleanup_remain_closed': True,
        'R02_publication_closed_for_explicit_finite_handler_observation_scope': True,
        'finite_cutoff_source_review': 'One-way flag assignment precedes clock and snapshot. Same-main-thread record-only handlers classify before/after flag. Every frozen pre-cutoff record rejects. Later handlers cannot append pending and are expressly outside persisted evidence.',
        'publication_source_review': 'All compiler/cleanup/hash/parser work precedes cutoff. Successful observation publication precedes accepted receipt construction/publication. Closed staged bytes are atomically linked without overwrite; writer failure before final link cannot create a final accepted receipt.',
        'frozen_case_review': {
            'C01': 'Retained constructor controls for all four signals and unchanged launch.start ownership path.',
            'C02': 'Retained constructor failure control; pending request follows same frozen pre-cutoff rejection path.',
            'C03': 'Retained record-only owned cleanup controls; no raising handler replacement.',
            'C04': 'Caller source order and final pre-cutoff snapshot cover every posthash/parser interval without a special pending checkpoint.',
            'C05': 'Four new before-cutoff controls reject and persist the pending request.',
            'C06': 'Four new injected-clock controls execute after flag assignment before snapshot; classify outside observation.',
            'C07': 'Same post-cutoff-only handler branch; frozen receipt reads snapshot. No compiler/hash/parser calls follow cutoff.',
            'C08': 'Four new observation-write controls preserve observation-before-receipt and post-cutoff scope.',
            'C09': 'Four new receipt-write controls preserve completed observation and post-cutoff scope.',
            'C10': 'Observation writer failure control produces rejected receipt; actual staged/link writer withholds final name before success.',
            'C11': 'Receipt writer failure control retains observation and no completed final receipt; actual staged/link writer withholds final name before success.'},
        'producer_offline_controls_read': 64, 'producer_controls_or_checker_replayed': False,
        'compiler_runtime_version_native_ui_capture_invocations': 0,
        'release_recommended': True,
        'release_scope': 'Root alone may release one exact frozen compiler-only command; no retry or runtime/version command.',
        'actual_diagnostic_strategy_qualified': False,
        'independent_terminal_parser_conditions_preserved': True,
        'all_actual_layout_prices_backing_peak_funding_ownership_native_FieldLog_OTA_GA_pending': True,
        'cleanup': 'No compiler/runtime/native/capture process or build artifact created by reviewer; no such cleanup owed.'}
    with (HERE / 'prepared-packet-review-03.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'v3_members_verified', 'toolchain_members_verified',
          'release_recommended', 'compiler_runtime_version_native_ui_capture_invocations', 'elapsed_seconds')}))


if __name__ == '__main__':
    main()
