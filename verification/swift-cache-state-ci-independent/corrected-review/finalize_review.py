#!/usr/bin/env python3
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
import sys

HERE = Path(__file__).absolute().parent
ROOT = HERE.parents[2]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def members(base):
    result = []
    for p in sorted(base.rglob('*')):
        mode = p.lstat().st_mode
        assert stat.S_ISREG(mode) or stat.S_ISDIR(mode)
        if stat.S_ISREG(mode):
            result.append({'path': p.relative_to(base).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)})
    return result

def verify_rows(base, rows):
    for row in rows:
        path = base / row['path']
        assert path.is_file() and not path.is_symlink() and path.stat().st_size == row['bytes'] and sha(path) == row['sha256']

def main():
    original = HERE.parent
    original_seal = original / 'seal.json'
    assert sha(original_seal) == '2ffd34768ac601695001551cd2382d9a93e49e80d3f3865a86aa201048ba6a1d'
    verify_rows(original, json.loads(original_seal.read_bytes())['members'])
    inputs = [
        ('verification/swift-cache-state-ci-preparation', 'seal.json', 'b22b11db7ce9dda9910117d730eed385793426fb220981fa15de71b9253b39f8'),
        ('verification/swift-cache-state-ci-root-correction', 'source-seal.json', '9704bd9de71610ca480a392a3e30fb3c46dd6136ce6e490218b676262da0a0d6'),
        ('verification/swift-cache-state-ci-root-correction-2', 'source-seal.json', 'bccbdaefca93a190fc74faa7340a3e32848d3d3a35fc05f078a2e3825543600e')]
    custody = []
    for directory, name, expected in inputs:
        base = ROOT / directory
        assert sha(base / name) == expected
        seal = json.loads((base / name).read_bytes())
        verify_rows(base, seal['members'])
        custody.append({'path': directory + '/' + name, 'sha256': expected, 'members_verified': len(seal['members'])})
    audit = json.loads((HERE / 'full-audit.json').read_bytes())
    guards = json.loads((HERE / 'evidence/correction-2-guards-complete/receipt.json').read_bytes())
    assert audit['passed'] and guards['passed']
    runner = HERE / 'correction-2-copy/check_cache_state.py'
    assert sha(runner) == 'e531311facb7b38967d3b904b26e92ff3f6c4dc7444c856cd799b70a1d91373b'
    decision = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'python': sys.version, 'builder_sha256': sha(Path(__file__)),
        'decision': 'Accept exact corrected isolated closed Rust1.99.0 macOS arm64 host fixture component only',
        'corrected_host_component_accepted': True, 'canonical_CI_integration_selected': False,
        'runner_sha256': sha(runner),
        'pack_manifest_sha256': '6c52eb0ed737530d92011ce63e1eda593159c670b262a5f7bcf8b54b5338d857',
        'source_sha256': 'f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b',
        'input_custody': custody, 'original_independent_seal_sha256': sha(original_seal),
        'all_original_and_intermediate_frozen_members_unchanged': True,
        'resolved_findings': ['All children receive bound owned canonical TMPDIR/TMP/TEMP',
            'Parent traversal rejected in both scratch binding and temporary overrides before spawn',
            'Cleanup expiry is terminal and preserves recoverable scratch'],
        'independent_focused_controls': {'actual_default_fixture_children': 2, 'refusals_without_spawn': 9,
            'terminal_expiry_controls': 2},
        'normal_full_invocations': 1, 'commands': audit['commands'],
        'active_elapsed_seconds': audit['active_elapsed_seconds'], 'cleanup_elapsed_seconds': audit['cleanup_elapsed_seconds'],
        'elapsed_seconds': audit['elapsed_seconds'], 'max_child_seconds': audit['max_child_seconds'],
        'source_revision': audit['source_revision'], 'source_tree': audit['source_tree'],
        'compiler': audit['compiler'], 'modes': audit['modes'],
        'full_raw_audit_sha256': sha(HERE / 'full-audit.json'),
        'actual_runner_receipt_sha256': audit['runner_receipt_sha256'],
        'hostile_inherited_environment_scrub_and_foreign_sentinel_unchanged': True,
        'all103commands_owned_TMP': True, 'postflight_checks_passed': 9,
        'derived_source_files_verified': 19, 'retained_files_verified': 901,
        'compiler_products_hashed_removed': 14, 'all_owned_children_reaped': True,
        'normal_and_control_scratch_removed': True, 'no_native_UI_capture_or_other_process_inventory': True,
        'original_full_producer_Debug60s_timeout_remains_failed': True,
        'performance_equivalence_claimed': False,
        'retained_authored_harness_failure': 'evidence/correction-2-guards/authoring-failure.json',
        'pending': ['Rust1.98.1 actual CI qualification', 'Root canonical pack/runner/workflow selection and actual job timing',
            'General public File admission', 'Full runtime/target/native/phone acceptance',
            'Immutable published-package separate-repository FieldLog', 'Signing/store/customer operations/GA'],
        'full_target_native_or_GA_qualified': False}
    (HERE / 'final-decision.json').write_text(json.dumps(decision, sort_keys=True, indent=2) + '\n')
    rows = [r for r in members(HERE) if r['path'] != 'seal.json']
    seal = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'python': sys.version, 'builder_sha256': sha(Path(__file__)), 'member_base': 'corrected-review-relative',
        'excluded': ['seal.json'], 'members': rows, 'member_count': len(rows), 'total_bytes': sum(r['bytes'] for r in rows),
        'tree_sha256': hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'decision_sha256': sha(HERE / 'final-decision.json'), 'corrected_host_component_accepted': True,
        'normal_full_invocations': 1, 'commands': 103, 'Rust1.98.1_pending': True,
        'canonical_CI_runtime_native_or_GA_qualified': False}
    (HERE / 'seal.json').write_text(json.dumps(seal, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'seal_sha256': sha(HERE / 'seal.json'), 'members': len(rows), 'bytes': seal['total_bytes'],
        'decision_sha256': seal['decision_sha256'], 'corrected_host_component_accepted': True}))

if __name__ == '__main__':
    main()
