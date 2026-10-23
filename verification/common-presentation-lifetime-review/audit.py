#!/usr/bin/env python3
"""Bind the final independent review to frozen implementation and executable logs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
inputs = {}

def load(relative):
    path = ROOT / relative
    data = json.loads(path.read_text())
    inputs[relative] = sha(path)
    for command in data.get('commands', []):
        assert command['exit'] == command.get('expected_exit', 0), command['name']
        assert sha(ROOT / command['log']) == command['sha256'], command['log']
    for mode in data.get('artifacts', {}).values():
        for path, digest in mode.items():
            assert sha(Path(path)) == digest, path
    return data

owner = load('verification/common-presentation-lifetime/final-1/receipt.json')
independent = load('verification/common-presentation-lifetime-review/final-1/receipt.json')
portable = load('verification/common-presentation-lifetime/portable-1/receipt.json')
assert owner['source_tree_sha256'] == independent['owner_source_tree_sha256'] == portable['source_tree_sha256']
assert independent['owner_receipt_sha256'] == portable['reference_receipt_sha256'] == inputs['verification/common-presentation-lifetime/final-1/receipt.json']
assert independent['result'] == 'Independent source-bound probes passed in all selected modes.'
assert portable['result'].startswith('Actual portable branch full-module compilation')
assert owner['result'].startswith('Selected full-module builds')
for relative, digest in owner['source_files'].items():
    assert sha(Path(owner['source']) / relative) == digest == sha(ROOT / relative), relative
for relative, digest in independent['source_files'].items():
    assert sha(Path(independent['source']) / relative) == digest, relative
for relative, digest in portable['extra_inputs'].items():
    assert sha(ROOT / relative) == digest, relative
for path, digest in portable['real_dependency_modules'].items():
    assert sha(Path(path)) == digest, path
assert not (Path(next(iter(portable['real_dependency_modules']))).parent / 'MixerApple.swiftmodule').exists()
acceptance = ROOT / 'verification/android-binding-contract-acceptance.json'
contract = ROOT / 'docs/android-signed-ui-binding-contract.md'
accepted = json.loads(acceptance.read_text())
assert accepted['contract_sha256'] == sha(contract)
assert sha(ROOT / 'capability-activation/Tests/MixerCapabilityActivationTests/CapabilityColdStartRuntimeTests.swift') == '292448a10a86299a55f600ce73b2442b3c84a92543adca4fe8aa7b9b68e4a720'
for mode in ['debug', 'release', 'tsan']:
    own_log = (ROOT / f'verification/common-presentation-lifetime-review/final-1/{mode}-tests.log').read_text()
    owner_log = (ROOT / f'verification/common-presentation-lifetime/final-1/{mode}-xctests.log').read_text()
    model_log = (ROOT / f'verification/common-presentation-lifetime/final-1/{mode}-model-tests.log').read_text()
    portable_log = (ROOT / f'verification/common-presentation-lifetime/portable-1/{mode}-portable-tests.log').read_text()
    assert 'Executed 13 tests, with 0 failures' in own_log
    assert 'Executed 14 tests, with 0 failures' in owner_log
    assert model_log.count(' skipped.') == 1
    assert sum(line.startswith('✔ Test ') and '() passed after ' in line for line in model_log.splitlines()) == 13
    assert 'Executed 1 test, with 0 failures' in portable_log
    assert 'WARNING: ThreadSanitizer' not in own_log + owner_log + model_log + portable_log

review = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'reviewer': '/root/common_presentation_lifetime_review',
    'decision': 'No actionable blocker found. Frozen stage 2 common lifetime/setup implementation is acceptable for root integration within the explicitly tested host scope.',
    'findings': [],
    'inputs': inputs,
    'accepted_contract_sha256': sha(contract),
    'acceptance_sha256': sha(acceptance),
    'owner_source_tree_sha256': owner['source_tree_sha256'],
    'independent_source_tree_sha256': independent['source_tree_sha256'],
    'reviewed_activation_source_files': {relative: digest for relative, digest in owner['source_files'].items() if relative.startswith('capability-activation/Sources/')},
    'test_only_ci_repair_sha256': '292448a10a86299a55f600ce73b2442b3c84a92543adca4fe8aa7b9b68e4a720',
    'independent_verification': {
        'modes': ['Debug', 'Release', 'ThreadSanitizer'],
        'per_mode': 'Complete exact activation module builds; 13 XCTest (5 independent probes and 8 frozen core regressions); normal external API and testable private-constructor compile rejection.',
        'probes': [
            'Hold actual presentation Task return, then hold actual MainActor retirement return: both prevent exact receipt and fallback admission.',
            '64 concurrent join reentries return pending while the one authorized join remains held; the immutable completion repeats with one retirement turn.',
            'Wrong-reservation and already-closed control transfer reject without losing the guard permit; two cleanup calls have one owner and retain a stopped public Apple model.',
            '64 bind/core-close races preserve either local or observation authority and release only after ordinary operation finish, including unused store admission destruction.',
            'A false MainActor retirement result produces lifetime quarantine; fallback rejects and final close pins capacity.',
            'External import cannot name the internal guard/binding/permit/receipt; even testable import cannot call ID/permit/lifetime-receipt/facade-receipt constructors.'
        ],
        'tools': {
            name: (HERE / f'final-1/{name}.log').read_text().strip()
            for name in ['swift-version', 'xcode-version', 'python-version', 'platform']
        },
    },
    'inspected_owner_verification': {
        'per_mode': '14 XCTest, 13 Apple model/hidden-window passes plus 1 explicitly skipped visible-window test; exact logs and built artifacts rehashed.',
        'portable': 'Unchanged full activation source compiled with real MixerApple module unavailable, 32 unsupported-prepare cycles in one test per mode. Each cycle explicitly retires the unused one-shot obligation and returns capacity. This is host #else coverage, not an Android build.'
    },
    'source_review': [
        'Permit issue/move/begin/consume cells and installation moves keep one join authority; mismatched IDs fail and reentries register no additional waiter.',
        'Prepared guard owns pre-bind authority through failed transfer; transfer disarms only after binding/control acceptance. Open protects constructor and opening admission in the cleanup catch.',
        'Presentation obligation is reserved before Apple model allocation; setup catches await their owned cleanup without adding a Task. Abandonment quarantines.',
        'Binding catches stop the exact exchange and finish the moved local installation. Successful install validates current op, exact signals and exact bound exchange before the move.',
        'Observation detach/ending ownership moves once; notification consumer never joins itself. Fallback waits the returned exact retired status and concrete retirement before another selection.',
        'Existing core cleanup latches scalar close, joins moved observation, waits ordinary tail, then takes any remaining pre-bind permit, closes store and begins outer close.',
        'A real bound Task is awaited before the final MainActor retirement and immutable receipt publication. Non-retired final status quarantines the obligation.',
        'Store admission moves from worker into open only once and is cleared by unopened-core close; the reservation retains destruction fences for retained resource owners.',
        'Apple closed public model shells may remain strongly retained. Apple receipts cover view/resource retirement and make no public-model destruction assertion.',
        'Android remains unsupported; this stage allocates no Android C/JNI owner and exposes no Android public execution path.'
    ],
    'limits': [
        'No C facade/endpoint/native return-fence implementation, JNI integration or Android Looper execution acceptance.',
        'ThreadSanitizer instruments rebuilt activation and probe sources; retained dependency objects/archive are exact but not rebuilt or reinstrumented.',
        'No physical iOS/Android run, device discovery or reconnect request; phones remain disconnected.',
        'Positive visible native window, immutable published separate-repository FieldLog package consumer, signing/store/customer/operational and accountable GA gates remain pending.',
        'No production publication or credential/destructive operation is authorized or performed.'
    ],
    'review_inputs': {str(path.relative_to(ROOT)): sha(path) for path in [HERE / 'IndependentLifetimeTests.swift', HERE / 'PrivateReceiptClient.swift', HERE / 'run.py', Path(__file__).resolve()]},
    'audit_command': ['python3', 'verification/common-presentation-lifetime-review/audit.py'],
    'revision_at_audit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
}
(HERE / 'review.json').write_text(json.dumps(review, indent=2) + '\n')
print('All frozen source, owner/reviewer/portable commands, logs and built artifacts rehashed.')
print('No actionable blocker; stage 2 host-scope review complete.')
print('review.json sha256 ' + sha(HERE / 'review.json'))
