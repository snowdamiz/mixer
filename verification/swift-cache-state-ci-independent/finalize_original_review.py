#!/usr/bin/env python3
"""Seal the completed original-candidate review; later correction scope is separate."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
import sys

HERE = Path(__file__).absolute().parent
ROOT = HERE.parent.parent
PRODUCER = ROOT / 'verification/swift-cache-state-ci-preparation'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(base, exclude):
    result = []
    for p in sorted(base.rglob('*')):
        relative = p.relative_to(base).as_posix()
        if exclude(relative):
            continue
        mode = p.lstat().st_mode
        assert stat.S_ISREG(mode) or stat.S_ISDIR(mode)
        if stat.S_ISREG(mode):
            result.append({'path': relative, 'bytes': p.stat().st_size, 'sha256': sha(p)})
    return result

def main():
    producer_seal = PRODUCER / 'seal.json'
    assert sha(producer_seal) == 'b22b11db7ce9dda9910117d730eed385793426fb220981fa15de71b9253b39f8'
    frozen = json.loads(producer_seal.read_bytes())
    assert rows(PRODUCER, lambda p: p == 'seal.json') == frozen['members']
    custody = json.loads((HERE / 'candidate-custody.json').read_bytes())
    controls = json.loads((HERE / 'evidence/candidate-negative-controls/receipt.json').read_bytes())
    temporary = json.loads((HERE / 'evidence/candidate-temporary-environment-gap/receipt.json').read_bytes())
    deadline = json.loads((HERE / 'evidence/candidate-cleanup-deadline-gap.json').read_bytes())
    actual = json.loads((HERE / 'evidence/preaccess-api-complete/receipt.json').read_bytes())
    assert controls['passed'] and controls['controls_rejected'] == 919
    assert not temporary['owned_TMP_contract_passed'] and not deadline['deadline_enforcement_contract_passed']
    assert temporary['child_reaped'] and temporary['owned_group_gone']
    assert deadline['scratch_removed'] and controls['scratch_removed']
    assert actual['passed'] and actual['scratch_removed']
    decision = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'python': sys.version, 'builder_sha256': sha(Path(__file__)),
        'decision': 'Revision required before independent full closed-host qualification',
        'original_candidate_accepted': False, 'normal_independent_runner_invocation_started': False,
        'root_authorized_skipping_known_failing_full_invocation': True,
        'producer_seal_sha256': sha(producer_seal),
        'runner_sha256': custody['runner_sha256'], 'pack_manifest_sha256': custody['pack_manifest_sha256'],
        'source_sha256': 'f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b',
        'producer_members_verified': len(frozen['members']), 'producer_bytes_verified': frozen['total_bytes'],
        'findings': [
            {'id': 'all-child-owned-temporary-directory', 'file': 'check_cache_state.py', 'lines': [72, 77, 101],
             'receipt': 'evidence/candidate-temporary-environment-gap/receipt.json',
             'actual_child_TMPDIR_TMP_TEMP': [None, None, None],
             'required_repair': 'Bind every Commands child to owned scratch TMPDIR/TMP/TEMP; reject escape overrides and preserve valid per-fixture owned overrides'},
            {'id': 'terminal-cleanup-deadline', 'file': 'check_cache_state.py', 'lines': [285, 288, 306],
             'receipt': 'evidence/candidate-cleanup-deadline-gap.json',
             'test_allowance_seconds': deadline['test_only_cleanup_allowance_seconds'],
             'post_expiry_observed_work_seconds': deadline['state']['post_expiry_cleanup_delay_observed_seconds'],
             'required_repair': 'Propagate a terminal cleanup-deadline exception, enforce absolute remaining allowance and preserve recoverable scratch on expiry'}],
        'additional_actionable_findings_in_reviewed_closed_scope': [],
        'independent_preaccess_actual_API': {'modes': ['debug', 'optimized'], 'dispositions': 50, 'positive_executions': 4, 'primary_spans': 76},
        'candidate_negative_controls_rejected': 919, 'baseline_scope': controls['baselines'],
        'source_API_methods_cases_layouts_independently_match': True,
        'no_fresh_normal_suite_credit_from_historical_parser_baselines': True,
        'producer_frozen_unchanged': True, 'all_review_children_reaped': True,
        'control_scratch_removed': True, 'native_UI_capture_process_inventory_started': False,
        'read_only_Git_commands_executed_by_this_review': 0,
        'pending': ['Corrected frozen runner review and full fresh host invocation', 'Rust1.98.1 actual qualification',
            'Canonical CI/workflow selection', 'General public File/runtime/target/native/FieldLog/signing/store/operations/GA'],
        'original_full_producer_Debug60s_timeout_remains_failed': True,
        'canonical_runtime_native_or_GA_accepted': False}
    (HERE / 'original-decision.json').write_text(json.dumps(decision, sort_keys=True, indent=2) + '\n')
    selected = rows(HERE, lambda p: p == 'seal.json' or p == 'corrected-review' or p.startswith('corrected-review/'))
    tree = hashlib.sha256(json.dumps(selected, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    seal = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'python': sys.version, 'builder_sha256': sha(Path(__file__)),
        'member_base': 'lane-relative', 'excluded': ['seal.json', 'corrected-review/**'],
        'later_scope': 'Any later correction review is separately sealed only under corrected-review; all listed original members remain immutable',
        'members': selected, 'member_count': len(selected), 'total_bytes': sum(r['bytes'] for r in selected),
        'tree_sha256': tree, 'decision_sha256': sha(HERE / 'original-decision.json'),
        'decision': decision['decision'], 'original_candidate_accepted': False,
        'producer_seal_sha256': sha(producer_seal), 'producer_packet_unchanged': True,
        'independent_fresh_normal_run_performed': False, 'native_or_GA_qualified': False}
    (HERE / 'seal.json').write_text(json.dumps(seal, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'seal_sha256': sha(HERE / 'seal.json'), 'member_count': len(selected),
                      'bytes': seal['total_bytes'], 'decision_sha256': seal['decision_sha256']}))

if __name__ == '__main__':
    main()
