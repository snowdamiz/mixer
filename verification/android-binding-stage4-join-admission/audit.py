#!/usr/bin/env python3
"""Root audit of the candidate3 join guard and its precise ordering amendment."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REVIEW = ROOT / 'verification/android-binding-stage4-review'
sha = lambda data: hashlib.sha256(data).hexdigest()
bindings = {}
def bind(path, expected=None):
    path = ROOT / path
    data = path.read_bytes()
    digest = sha(data)
    assert expected is None or digest == expected, path
    bindings[str(path.relative_to(ROOT))] = digest
    return data
def read(path, expected=None):
    return json.loads(bind(path, expected))

decision_path = REVIEW / 'candidate-3/review.json'
review = read(decision_path, 'a0a1c31e5b7e19f377c02dbfc97cc082a3e450b59afac41296636cd6c03e8c4a')
bind(review['addendum']['source'], review['addendum']['sha256'])
bind(REVIEW / review['addendum']['frozen_copy'], review['addendum']['sha256'])
bind(HERE / 'proposal-1.md', '85287b597f00b5d91c0fb69be9e10d93b53898591b5828c047b218dd15229916')
freeze = read(REVIEW / review['candidate']['source_manifest'])
assert freeze['source_tree_sha256'] == review['candidate']['source_tree_sha256']
assert sha(json.dumps(freeze['source_files'], sort_keys=True).encode()) == freeze['source_tree_sha256']
producer = read(review['candidate']['producer_receipt'], review['candidate']['producer_receipt_sha256'])
assert producer['source_tree_sha256'] == freeze['source_tree_sha256']
for relative, digest in freeze['source_files'].items():
    bind(REVIEW / 'candidate-3/source' / relative, digest)
    if relative.startswith(('capability-activation/Sources/', 'native/android/signed-guest-ui/')):
        bind(relative, digest)
assert len(review['candidate']['exact_product_delta_since_final2']) == 1
for relative, delta in review['candidate']['exact_product_delta_since_final2'].items():
    bind(relative, delta['after'])

executions = []
for relative, digest in review['receipt_bindings'].items():
    path = REVIEW / relative
    receipt = read(path, digest)
    assert receipt['source_tree_sha256'] == freeze['source_tree_sha256']
    for command in receipt['commands']:
        assert command['exit'] == 0, (relative, command['name'])
        bind(command['output'], command['output_sha256'])
    for artifact, checksum in receipt['artifacts'].items():
        bind(artifact, checksum)
    if 'source_files' in receipt:
        assert receipt['source_files'] == freeze['source_files']
        dependency = read(receipt['dependency_receipt'], receipt['dependency_receipt_sha256'])
        dependency_root = Path(dependency['dylib']).parents[1]
        assert receipt['dependency_artifacts'] == dependency['artifacts']
        for artifact, checksum in receipt['dependency_artifacts'].items():
            bind(dependency_root / artifact, checksum)
        inputs = path.parent / 'inputs'
        probe = 'ReclaimRaceProbe.swift' if 'instrumented' in relative else 'ReviewProbes.swift'
        bind(inputs / probe, receipt['review_probe_sha256'])
        bind(inputs / 'run_review.py', receipt['review_runner_sha256'])
    else:
        read(receipt['full_rebuild_receipt'], receipt['full_rebuild_receipt_sha256'])
        # These receipts run exactly one scenario; their stale prose is amended
        # by a separate immutable clarification, never counted as extra tests.
        assert [c['name'] for c in receipt['commands']] == ['delta-link', 'late-progress-join']
    executions.append({'receipt': str(path.relative_to(ROOT)), 'mode': receipt['mode'],
                       'actual_commands': [c['name'] for c in receipt['commands']]})
instrument = read(REVIEW / review['post_C_success_instrument']['audit'])
for path, digest in instrument['review_input_files'].items():
    bind(path, digest)
clarification = read(REVIEW / review['summary_wording_clarification'])
assert clarification['actual_scenarios_executed'] == ['late-progress-join']
result = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 verification/android-binding-stage4-join-admission/audit.py',
    'python': platform.python_version(), 'auditor_sha256': sha(Path(__file__).read_bytes()),
    'decision': 'Accept the candidate3 control-local join guard and precise two-point ordering amendment within the independently exercised host scope only.',
    'review': str(decision_path.relative_to(ROOT)), 'review_sha256': bindings[str(decision_path.relative_to(ROOT))],
    'source_tree_sha256': freeze['source_tree_sha256'], 'bindings': bindings,
    'verified_bindings': len(bindings), 'executions': executions,
    'scope': 'Real terminal RETIRE followed by latched local fault rejects consumer_joined in Debug/Release/TSan. Separate instrumented Release proves actual C endpoint retirement serialized before registry fault may publish its historical fact while facade/resources/capacity stay pinned. Initial overbroad proposal and all failed attempts remain historical.',
    'full_stage4_implementation_accepted': False,
    'pending': ['Full32-case host matrix with exact executed-versus-source-only limits',
                'Remaining publication/cleanup boundary probes and root source integration',
                'Fresh repeatable CI linkage',
                'JNI/Java/Looper/real UI, devices, immutable consumer and all specified external gates'],
    'ga_gate_state_changes': False,
}
(HERE / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'accepted_join_delta_only': True, 'bindings': len(bindings), 'full_stage4_accepted': False}))
