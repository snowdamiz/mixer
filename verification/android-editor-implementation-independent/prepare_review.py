#!/usr/bin/env python3
"""Pre-access custody and closed-descriptor expectations. Never opens a candidate."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SELECTION = 'verification/android-editor-boundary-root-review/cleanup-contract-selection.json'
SELECTION_SHA = '89fa92964745eaa306e3e2578aeae822a0cd0224c987f06c7b62edecdf8a292e'
SEALS = {
    'verification/android-editor-cleanup-contract/seal.json':
        '060347101b96ecb7a5ee180828cf3437d47179fbb82e8c8ba8457a96859023b7',
    'verification/android-editor-cleanup-contract-independent/seal.json':
        'ecdc6bd94e2c49b501c2d1dbf69323b8abb3d830c78c689acc39435a31d273c0',
}
INPUTS = [
    'AGENTS.md', 'mixer-product-plan.md', SELECTION, *SEALS,
    'verification/android-editor-cleanup-contract/proposal.md',
    'verification/android-editor-cleanup-contract/contract.json',
    'verification/android-editor-cleanup-contract-independent/required-addendum.md',
    'verification/android-editor-cleanup-contract-independent/review.md',
    'verification/android-editor-api-boundary-proposal/api-inventory.json',
    'verification/android-editor-api-boundary-proposal/official-inputs.json',
    'verification/android-editor-api-boundary-proposal/official-defaults.json',
    'verification/android-editor-api-boundary-proposal/official/javap-sdk36.txt',
    'verification/android-inputconnection-authority-audit/method-inventory.json',
    'verification/android-editor-cleanup-contract/official/collection.json',
    *['native/android/app/src/dev/mixer/android/' + x + '.java' for x in (
        'NativeAppearanceViewsV2', 'NativeRenderer', 'NativeCoordinatorV2',
        'NativeOwnerV2', 'OwnerLifecycleV2', 'NativeEnvironmentV2')],
    *['native/android/tests/NativeOwnerV2ConcreteHostLeaves/' + x for x in (
        'android/view/inputmethod/InputConnection.java',
        'android/view/inputmethod/EditorInfo.java',
        'android/widget/EditText.java', 'android/view/View.java')],
]
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(name: str, value: object) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def read_input(relative: str) -> bytes:
    # No directory discovery or broad glob: exactly the authored preaccess allowlist.
    assert relative in INPUTS, relative
    assert not relative.startswith('verification/android-editor-implementation/'), relative
    return (ROOT / relative).read_bytes()


def main() -> None:
    observed = {}
    for relative in INPUTS:
        data = read_input(relative)
        observed[relative] = {'path': relative, 'bytes': len(data), 'sha256': digest(data)}
        target = OUT / 'inputs' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    assert observed[SELECTION]['sha256'] == SELECTION_SHA
    selection = json.loads(read_input(SELECTION))
    assert selection['native_or_GA_accepted'] is False
    verified = []
    for relative, expected in SEALS.items():
        assert observed[relative]['sha256'] == expected
        seal = json.loads(read_input(relative))
        parent = (ROOT / relative).parent
        size = 0
        for member in seal['members']:
            name = Path(member['path'])
            assert not name.is_absolute() and '..' not in name.parts
            # These are frozen accepted contract packet members, never an active implementation.
            data = (parent / name).read_bytes()
            assert len(data) == member['bytes'] and digest(data) == member['sha256'], str(name)
            size += len(data)
        verified.append({'path': relative, 'sha256': expected,
                         'members': len(seal['members']), 'bytes': size})
    addendum = selection['required_addendum']
    assert observed[addendum['path']]['sha256'] == addendum['sha256']
    proposal = json.loads(read_input('verification/android-editor-api-boundary-proposal/api-inventory.json'))
    official = [m for m in proposal['android/view/inputmethod/InputConnection']['members']
                if m['kind'] == 'method']
    audit = json.loads(read_input('verification/android-inputconnection-authority-audit/method-inventory.json'))
    a = {m['name']: int(m.get('since', 3)) for m in official}
    b = {m['name'] + m['descriptor']: m['api_since'] for m in audit['methods']}
    assert len(a) == len(b) == 38 and a == b
    reads = {'getCursorCapsMode', 'getSelectedText', 'getTextAfterCursor',
             'getTextBeforeCursor', 'getSurroundingText', 'takeSnapshot'}
    refusals = {'commitContent', 'commitCorrection', 'performPrivateCommand',
                'previewHandwritingGesture', 'replaceText', 'sendKeyEvent', 'performSpellCheck'}
    rows = []
    for signature, since in sorted(a.items()):
        name = signature.split('(', 1)[0]
        route = ('captured_bounded_read' if name in reads else
                 'false_before_target' if name in refusals else 'captured_mutation')
        special = {
            'getHandler': 'constant_null_any_thread_no_state_no_main_check',
            'closeConnection': 'local_revoke_then_exact_target_close_once_or_precise_defer',
            'getExtractedText': 'nonmonitor_only_captured_read_no_subscription',
            'requestCursorUpdates': 'zero_mode_and_zero_filter_only_captured_native_disable',
            'performHandwritingGesture': 'constant_unsupported_on_caller_executor_no_native_payload',
            'requestTextBoundsInfo': 'constant_unsupported_on_caller_executor_no_native_payload',
            'performEditorAction': 'configured_done_only_captured_native_continuation',
            'commitCompletion': 'plain_bounded_validated_completion_snapshot',
            'commitText': 'plain_bounded_validated_proposal_snapshot',
            'setComposingText': 'plain_bounded_validated_composing_proposal_snapshot',
            'performContextMenuAction': 'lease_before_native_batch_prefix_not_only_widget_callback',
            'reportFullscreenMode': 'captured_synchronous_report_both_boolean_arguments_no_new_true_refusal',
        }
        route = special.get(name, route)
        floor = 28 if since <= 28 else since
        rows.append({'descriptor': signature, 'official_since': since,
                     'declared_tier_floor': floor, 'selected_route': route,
                     'main_first': name != 'getHandler',
                     'required_states': ['live', 'temporary_seal', 'revoked', 'stale_adapter',
                                         'creating', 'closing', 'off_main'],
                     'not_yet_executed': True})
    counts = {str(floor): sum(r['declared_tier_floor'] == floor for r in rows)
              for floor in (28, 31, 33, 34)}
    assert counts == {'28': 26, '31': 3, '33': 5, '34': 4}
    write_json('descriptor-expectations.json', {
        'schema': 1, 'scope': 'Closed official descriptor and root-selected private policy oracle only',
        'selection_sha256': SELECTION_SHA, 'descriptor_count': 38, 'tier_counts': counts,
        'declaration_rule': 'All descriptors implemented in authored class chain; no inherited platform default, wrapper, BaseInputConnection or setTarget exposure',
        'methods': rows, 'candidate_reads': 0, 'candidate_executions': 0,
        'public_or_pre36_support_accepted': False,
    })
    commands = []
    for tool in ('java', 'javac', 'javap'):
        argv = [str(JDK / 'bin' / tool), '-version']
        result = subprocess.run(argv, capture_output=True, text=True, timeout=20, check=False)
        assert result.returncode == 0
        commands.append({'argv': argv, 'exit': result.returncode,
                         'stdout': result.stdout, 'stderr': result.stderr})
    canonical = [observed[p] for p in INPUTS if p.startswith('native/android/app/src/')]
    tree_bytes = ''.join(row['path'] + '\0' + row['sha256'] + '\n'
                         for row in sorted(canonical, key=lambda row: row['path'])).encode()
    write_json('preaccess-receipt.json', {
        'schema': 1, 'at': datetime.datetime.now(datetime.UTC).isoformat(),
        'argv': sys.argv, 'python': sys.version, 'platform': platform.platform(),
        'context_revision_supplied_by_root': '8ac624160a2cfff10d201d8063f69cf05f005edb',
        'revision_is_context_only_hashes_authoritative': True,
        'script_sha256': digest(Path(__file__).read_bytes()),
        'inputs': list(observed.values()), 'canonical_subset_digest': digest(tree_bytes),
        'frozen_contract_packets_verified': verified, 'commands': commands,
        'descriptor_inventory_agreement': {'methods': 38, 'tier_counts': counts},
        'active_implementation_candidate_reads': 0,
        'active_implementation_candidate_executions': 0,
        'frozen_contract_code_executions': 0,
        'computer_use_capture_ui_native_runtime_or_process_inventory': False,
        'git_mutation_or_delivery': False, 'canonical_or_root_metadata_edits': False,
        'cleanup': 'Only finite version subprocesses; no native/capture instance started; no process inventory or process cleanup attempted',
        'decision': 'Preaccess preparation only; await root-bound frozen implementation before any candidate access',
        'pending': ['complete-source actual implementation audit and hostile host execution',
                    'pinned SDK full closure cross-compilation',
                    'native runtime after user resumes', 'physical final matrix',
                    'TalkBack', 'immutable separately published FieldLog', 'store/signing/OTA/GA'],
    })
    print(json.dumps({'stage': 'preaccess', 'inventory': 38, 'tier_counts': counts,
                      'contract_members_verified': sum(x['members'] for x in verified),
                      'candidate_reads': 0, 'candidate_executions': 0}))


if __name__ == '__main__':
    main()
