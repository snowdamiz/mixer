#!/usr/bin/env python3
"""Root exact-input audit for the reviewed data encoder and frontier repair."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRODUCER = ROOT / 'verification/ui-native-packet-v1/candidate-3'
REVIEW = ROOT / 'verification/ui-native-packet-review'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, label):
    if not condition:
        raise RuntimeError(label)


def main():
    decision = json.loads((REVIEW / 'decision-receipt.json').read_text())
    producer = json.loads((PRODUCER / 'receipt.json').read_text())
    lock = json.loads((PRODUCER / 'input-lock.json').read_text())
    audit = json.loads((REVIEW / 'audit-receipt.json').read_text())
    count = 0
    require(producer['status'] == 'passed', 'producer status')
    require(audit['result'] == 'pass_repaired_data_encoder_and_validation_frontier_scope_only', 'review disposition')
    require(audit['producer_receipt_sha256'] == sha(PRODUCER / 'receipt.json'), 'review producer seal')
    require(audit['input_lock_sha256'] == sha(PRODUCER / 'input-lock.json'), 'review input seal')
    require(audit['scope_clarification_sha256'] == sha(ROOT / 'verification/ui-native-packet-v1/scope.md'), 'clarification seal')
    for path, digest in lock['files'].items():
        for prefix in [ROOT, PRODUCER / '.build/source']:
            require(sha(prefix / path) == digest, 'source ' + path)
            count += 1
    for command in producer['commands']:
        require(command['exit_code'] == 0 and sha(ROOT / command['log']) == command['log_sha256'], 'producer command')
        count += 1
    for path, identity in producer['artifacts'].items():
        require(sha(ROOT / path) == identity['sha256'] and (ROOT / path).stat().st_size == identity['bytes'], 'producer artifact')
        count += 1
    for candidate in ['candidate2', 'candidate3']:
        folder = REVIEW / candidate
        receipt = json.loads((folder / 'receipt.json').read_text())
        for command in receipt['commands']:
            require(command['exit_code'] == 0 and sha(folder / command['output']) == command['output_sha256'], 'review command')
            count += 1
        require(sha(folder / 'ReviewPacketTests.swift') == receipt['probe_sha256'], 'review probe')
        require(sha(folder / '.build/source/sdk/Sources/MixerUI/Validation.swift') == receipt['validator_derived_sha256'], 'derived validator')
        count += 2
    for path, digest in decision['bound_review_artifacts'].items():
        require(sha(ROOT / path) == digest, 'review seal ' + path)
        count += 1
    inputs = {str(p.relative_to(ROOT)): sha(p) for p in [
        Path(__file__), PRODUCER / 'receipt.json', PRODUCER / 'input-lock.json', REVIEW / 'decision-receipt.json',
        REVIEW / 'audit-receipt.json', REVIEW / 'review.md', ROOT / 'verification/ui-native-packet-v1/scope.md',
        ROOT / 'sdk/Sources/MixerUI/NativePacketV1.swift', ROOT / 'sdk/Sources/MixerUI/Validation.swift',
        ROOT / 'sdk/Tests/MixerUITests/NativePacketV1Tests.swift']}
    result = {
        'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reviewer': 'root integrator', 'decision': 'accepted_data_encoder_and_frontier_repair_only',
        'source_tree_sha256': lock['tree_sha256'], 'binding_checks': count, 'files': inputs,
        'evidence': {'SDK_tests_per_debug_release': 51, 'new_focused_tests': 9,
            'independent_probe_functions_per_candidate_mode': 2, 'java_checks': 16,
            'public_swift_java_return_events': 3, 'producer_commands': 17,
            'ios_android': 'Core UI Guest module compilation only',
            'comb': '9001-node custom tree: old standard pending8992, repaired3997; custom limit legitimately retains8992'},
        'limits': 'Data and host/module checks only. Existing ordinary Android engine integration remains separate. No widget, native JNI, signed execution/health, physical design parity, published consumer, release or GA acceptance.',
    }
    (HERE / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['decision'], 'bindings': count}))


if __name__ == '__main__':
    main()
