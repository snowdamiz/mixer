#!/usr/bin/env python3
"""Select and verify one complete unchanged-source producer; never run product code."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(attempt):
    receipt_path = attempt / 'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    assert receipt['success'] and receipt['regressions_requested'] and receipt['selected_case'] is None
    assert all(receipt['cleanup'].values())
    assert not receipt['source_changes'] and not receipt['dependency_changes']
    for key, count in [('checks', 35), ('preauth_regression_checks', 30), ('begin_regression_checks', 30)]:
        assert len(receipt[key]) == count and all(case['passed'] for case in receipt[key])
    for path, expected in receipt['sources'].items():
        assert sha(ROOT / path) == expected == receipt['sources_after'][path]
        assert sha(attempt / 'inputs' / path) == expected
    for key in ['dependencies', 'dependency_sources']:
        for path, expected in receipt[key].items():
            assert sha(ROOT / path) == expected == receipt[key + '_after'][path]
            assert sha(attempt / 'dependencies' / path) == expected
    for path, expected in receipt['outputs'].items():
        assert sha(attempt / path) == expected
    for name in ['beam-cleanup.json', 'preauth-regression-beam-cleanup.json', 'begin-regression-beam-cleanup.json']:
        assert all(json.loads((attempt / name).read_text()).values())
    for name, expected_count in [('source-leaf-controls.json', 87), ('claim-output-leaf-controls.json', 58), ('reject-output-leaf-controls.json', 58)]:
        assert json.loads((attempt / name).read_text())['leaf_count'] == expected_count
    fence = json.loads((attempt / 'concurrent-share-fence.json').read_text())
    assert fence['actual_owned_checkouts'] == 2 and fence['both_current_source_decodes_held']
    losses = json.loads((attempt / 'known-commit-owner-loss.json').read_text())
    assert {entry['operation'] for entry in losses} == {'discovery', 'claim', 'reject'}
    assert all(entry.get('returned_failure') and entry['phase'] == 'commit' and entry['outcome'] == 'committed' for entry in losses)
    return receipt


def main():
    attempts = sorted((BASE / 'attempts').glob('*/receipt.json'))
    candidates = []
    preserved = []
    for path in attempts:
        receipt = json.loads(path.read_text())
        preserved.append({'receipt': str(path.relative_to(ROOT)), 'sha256': sha(path), 'success': receipt['success'],
            'regressions_requested': receipt.get('regressions_requested', True), 'selected_case': receipt.get('selected_case'),
            'failure': receipt.get('failure'), 'cleanup': receipt['cleanup']})
        if receipt.get('success') and receipt.get('regressions_requested') and receipt.get('selected_case') is None:
            candidates.append(path.parent)
    assert candidates, 'no full successful producer to seal'
    selected = candidates[-1]
    receipt = verify(selected)
    members = [BASE / name for name in ['run.py', 'seal.py', 'live.exs', 'controls.exs']]
    members += [ROOT / 'docs/hosted-browser-callback-storage.md', ROOT / 'hosted/lib/mixer_hosted/browser_auth/callback_draft.ex', ROOT / 'hosted/lib/mixer_hosted/browser_auth/store.ex']
    handoff = {'schema': 1, 'scope': 'Unit A producer only; independent review and root acceptance pending; no Unit B or GA qualification',
        'agent': receipt['agent'], 'selected_receipt': str((selected / 'receipt.json').relative_to(ROOT)),
        'selected_receipt_sha256': sha(selected / 'receipt.json'), 'revision': receipt['revision'], 'git_tree': receipt['git_tree'],
        'source_tree_sha256': receipt['source_tree_sha256'], 'callback_methods': 35, 'preauth_regression_methods': 30,
        'begin_regression_methods': 30, 'source_leaf_controls': 87, 'claim_output_leaf_controls': 58, 'reject_output_leaf_controls': 58,
        'members': {str(path.relative_to(ROOT)): sha(path) for path in members}, 'preserved_attempts': preserved,
        'sealed_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'seal_python': sys.version,
        'command': ['python3', '-B', str((BASE / 'seal.py').relative_to(ROOT))]}
    target = BASE / 'handoff.json'
    target.write_text(json.dumps(handoff, indent=2, sort_keys=True) + '\n')
    (BASE / 'handoff.sha256').write_text(sha(target) + '  verification/hosted-browser-callback-storage/handoff.json\n')
    print(json.dumps({'selected_receipt': handoff['selected_receipt'], 'handoff_sha256': sha(target), 'full_producer_verified': True}))


if __name__ == '__main__':
    main()
