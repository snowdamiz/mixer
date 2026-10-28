#!/usr/bin/env python3
"""Independent v2 bytes/delta check; no producer imports, replay or child."""
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
NEW = ROOT / 'verification/swift-root-bound-work-storage-layout-probe-v2'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def verify_packet(directory, expected, count):
    assert sha((directory / 'seal.json').read_bytes()) == expected
    seal = json.loads((directory / 'seal.json').read_bytes())
    assert len(seal['members']) == seal['member_count'] == count
    for row in seal['members']:
        path = directory / row['path']
        assert path.is_file() and not path.is_symlink()
        data = path.read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
    assert not any(path.is_symlink() for path in directory.rglob('*'))
    assert sorted(path.relative_to(directory).as_posix() for path in directory.rglob('*') if path.is_file()) == sorted([row['path'] for row in seal['members']] + ['seal.json'])
    assert sha(canonical(seal['members'])) == seal['tree_sha256']
    assert sum(row['bytes'] for row in seal['members']) == seal['member_bytes']
    return seal


def main():
    start = time.monotonic()
    old_seal = verify_packet(OLD, 'c0e4da5b92f9fc076db21cb59700876bda60efaa7dc4b3c191124b707436fad9', 173)
    new_seal = verify_packet(NEW, '76fda3e073db9bb7408275cf5d8eb494cf491e5a9cd0a894ba8cca35171127f8', 16)
    assert sha((NEW / 'plan.json').read_bytes()) == 'ac581da773865faf19b72eef8f2b12d3693b6e691ca910130f4e01f97e241c3d'
    old = json.loads((OLD / 'plan.json').read_bytes())
    new = json.loads((NEW / 'plan.json').read_bytes())
    preserved = ['argv', 'cwd', 'environment', 'original_source', 'diagnostic_source', 'diagnostics', 'bounds',
                 'compiler', 'python', 'toolchain_manifest', 'toolchain_version', 'sdk_path_settings', 'inputs',
                 'delta', 'execution', 'root_release_required', 'pending', 'all_price_layout_backing_peak_funding_ownership_GA_authority']
    for field in preserved:
        assert new[field] == old[field], field
    assert new['original_packet']['seal']['sha256'] == sha((OLD / 'seal.json').read_bytes())
    assert new['original_packet']['plan']['sha256'] == sha((OLD / 'plan.json').read_bytes())
    assert new['diagnostic_source_directory'] == str(OLD / 'source/vm')
    assert new['execution_build_directory'] == str(OLD / 'build')
    assert new['argv_sha256_canonical_JSON'] == sha(canonical(new['argv']))
    assert new['environment_sha256_canonical_JSON'] == sha(canonical(new['environment']))
    patch = ''
    for name in ['check.py', 'controls.py', 'diagnostics.py', 'run.py']:
        patch += ''.join(difflib.unified_diff((OLD / name).read_text().splitlines(True), (NEW / name).read_text().splitlines(True), fromfile='v1/' + name, tofile='v2/' + name))
    for name in ['strict_json.py', 'launch.py']:
        patch += ''.join(difflib.unified_diff([], (NEW / name).read_text().splitlines(True), fromfile='/dev/null', tofile='v2/' + name))
    assert patch.encode() == (NEW / 'correction-delta.patch').read_bytes()
    for row in new['scripts']:
        data = (NEW / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
    parser = (NEW / 'diagnostics.py').read_text()
    strict = (NEW / 'strict_json.py').read_text()
    runner = (NEW / 'run.py').read_text()
    launch = (NEW / 'launch.py').read_text()
    assert 'obj = loads(line)' in parser
    assert 'object_pairs_hook=unique_object' in strict and 'if key in result:' in strict and 'raise DuplicateKey(' in strict
    assert 'def stop_signal(number, frame): return launch.handle_signal(number, phase)' in runner
    assert 'process = launch.process' in runner
    assert 'self.process = constructor()' in launch and 'self.pending.append(' in launch
    # Exact source-order evidence for the remaining publication gap.
    guard = runner.index('launch.record_interruption_failure(failures)')
    snapshot = runner.index("'launch': launch.receipt()", guard)
    receipt_write = runner.index("write_once(out / 'receipt.json'", snapshot)
    observation_write = runner.index("write_once(out / 'diagnostic-observation.json'", receipt_write)
    restore = runner.index('for sig, handler in saved.items(): signal.signal(sig, handler)', observation_write)
    assert guard < snapshot < receipt_write < observation_write < restore
    assert runner.count('launch.record_interruption_failure(failures)') == 1
    controls = json.loads((NEW / 'controls-result.json').read_bytes())
    assert len(controls['controls']) == 42 and controls['actual_layout_strategy_qualified'] is False
    assert not (OLD / 'build').exists() and not (OLD / 'command').exists() and not (NEW / 'command').exists()
    preseal = json.loads((HERE / 'preaccess-seal.json').read_bytes())
    for row in preseal['members']:
        data = (HERE / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
    report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
              'status': 'V2_CUSTODY_AND_R01_LAUNCH_CLEANUP_CORRECTIONS_VERIFIED_FINAL_PUBLICATION_GAP_REMAINS',
              'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))], 'python': sys.version,
              'elapsed_seconds': time.monotonic() - start, 'v2_members_verified': 16,
              'v2_seal_sha256': sha((NEW / 'seal.json').read_bytes()), 'v2_plan_sha256': sha((NEW / 'plan.json').read_bytes()),
              'original_173_members_and_seal_membership_unchanged': True,
              'source146_queries_argv_env_toolchain_bounds_unchanged': True, 'complete_code_delta_reconstructed': True,
              'preaccess_oracle_and_all_stage_members_unchanged': True,
              'R01_duplicate_keys_closed': True, 'R02_launch_and_cleanup_entry_closed': True,
              'retained_producer_controls_read': 42, 'producer_controls_replayed': False,
              'remaining_finding': {'id': 'R02-publication', 'file': 'run.py',
                  'detail': 'The one pending-signal failure guard and launch receipt snapshot precede both receipt/observation writes. Record-only handlers remain active until after those writes. A signal during publication can be appended after the acceptance decision and omitted from written evidence.',
                  'control_gap': 'Synthetic receipt-finalization injection occurs before record_interruption_failure, so it does not cover injection during write_once.',
                  'required': 'An explicit finite publication fence/commit boundary that prevents acceptance after observed precommit interruption, with a pure synthetic interruption during publication control.'},
              'release_recommended': False, 'compiler_or_runtime_invocations': 0,
              'actual_diagnostic_strategy_qualified': False, 'all_actual_layout_prices_backing_peak_funding_ownership_GA_pending': True}
    with (HERE / 'prepared-packet-review-02.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ['status', 'v2_members_verified', 'release_recommended', 'compiler_or_runtime_invocations', 'elapsed_seconds']}))


if __name__ == '__main__':
    main()
