#!/usr/bin/env python3
"""Emit reviewable test-design data, not observed candidate results."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent

def main():
    families = [
        ('beginBatchEdit', 'beginBatchEdit', 'transport', 'enters counted leaf; returns !closed; no buffer/listener operation'),
        ('endBatchEdit', 'endBatchEdit', 'transport', 'enters counted leaf; returns !closed; no buffer/listener operation'),
        ('clearMetaKeyStates', 'clearMetaKeyStates', 'transport', 'enters counted leaf; returns !closed; no buffer/listener operation'),
        ('commitText', 'commitText', 'text', 'insert -> hostReplace -> InputFilter -> same Editable replace -> selection callback -> all TextWatcher stages'),
        ('commitTextWithAttributes', 'commitTextWithAttributes', 'text', 'attribute overload enters its own counted leaf then real insert/watchers'),
        ('setComposingText', 'setComposingText', 'text-composition', 'real insert/watchers then composing spans replaced on same Editable'),
        ('setComposingTextWithAttributes', 'setComposingTextWithAttributes', 'text-composition', 'attribute overload real insert/watchers then composing spans'),
        ('setComposingRegion', 'setComposingRegion', 'composition', 'remove/set composing spans; no hostReplace or TextWatcher delivery'),
        ('setComposingRegionWithAttributes', 'setComposingRegion', 'composition', 'host attribute overload delegates to same setComposingRegion leaf'),
        ('finishComposingText', 'finishComposingText', 'composition', 'remove composing spans; no hostReplace or TextWatcher delivery'),
        ('deleteSurroundingText', 'deleteSurroundingText', 'text', 'nonempty explicit append cursor deletion -> real hostReplace/filter/watchers'),
        ('deleteSurroundingTextInCodePoints', 'deleteSurroundingTextInCodePoints', 'text', 'explicit cursor codepoint deletion -> real hostReplace/filter/watchers; include non-BMP fixture'),
        ('setSelection', 'setSelection', 'selection', 'TextView.setSelection -> real onSelectionChanged; no TextWatcher text event'),
        ('performEditorAction', 'performEditorAction', 'submit', 'real hostEditorAction -> installed IME_ACTION_DONE listener -> submit event'),
        ('setImeConsumesInput', 'setImeConsumesInput', 'transport', 'enters counted leaf; returns !closed; no buffer/listener operation'),
        ('commitCompletion', 'commitCompletion', 'text', 'CompletionInfo.getText -> real insert/filter/watchers'),
    ]
    rows = []
    for name, leaf, category, effect in families:
        natural = category in ('text', 'text-composition', 'submit')
        current = ('true, exactly one genuine textChange/submit transaction and compatible committed successor; old original authority retired; no terminal'
                   if natural else 'true, exact leaf effect/callback and unchanged presentation token; no feature textChange/submit event; no terminal')
        successor = ('natural genuine textChange/submit publication during this target method; preserve same Editable and compatible Binding'
                     if natural else 'explicit beforeReturn hook performs one separately identified same-buffer hostReplace with real filters/watchers; compatible successor required; not native method behavior')
        cases = {
            'current': {'setup': 'healthy original field; changing=false; listener retained; explicit valid selection and compatible app reply', 'expected': current},
            'successor': {'setup': successor, 'expected': 'true original completed result; actual new committed token; exact buffer preserved; old Mutation.require refuses; no new operation or callable readiness after scalar completion'},
            'terminal': {'setup': 'owner.close before attempted call; no changing/listener suppression', 'expected': 'false; zero new method target entries; no feature event or successor'},
            'dirty': {'setup': 'owner.onPause before attempted call; preserve original captured connection', 'expected': 'false; zero new method target entries; no feature event or successor; pending owner drain does not imply success'},
            'stale': {'setup': 'alter observed config tuple without notifying observer before attempted call', 'expected': 'false; zero new method target entries; no feature event or successor; distinguish concrete stale capture from lifecycle dirty'},
            'fatal': {'setup': 'throw exact authored Fatal at this method target beforeReturn; real buffer/listener effects stay enabled', 'expected': 'same fatal escapes and is retained; gates close; no late target/event authority; any earlier genuine feature transaction is recorded rather than suppressed; cleanup rethrows only same retained fatal'},
        }
        rows.append({'family': name, 'counted_leaf': 'BaseInputConnection.' + leaf, 'category': category,
            'actual_frozen_leaf_effect': effect, 'watchers_suppressed': False, 'listener_removed': False,
            'ordinary_can_publish_successor': natural, 'successor_is_injected_feature_event': not natural,
            'new_transport_leaf_mode': None, 'cases': cases})
    result = {'schema': 1, 'status': 'test migration design; no corrected-source results',
        'source': 'inputs/historical-preparation/closure-B-directprobe/inputs/leaves/android/view/inputmethod/BaseInputConnection.java',
        'old_state_setup': 'record.changing=!state.equals("successor"); non-successor editor.editorListener=null',
        'selected_proposal': 'remove blanket suppression; use actual normal leaves and per-family case split',
        'families': rows, 'designed_state_rows': 96,
        'separate_invalid_entry': {'changing': True, 'expected': 'clean false before any new native target call; no terminal; no borrowing construction/bind scope'},
        'append_contract': {'initial_selection': [0, 0], 'explicit_append_selection': 'text.length(),text.length()', 'plain_hello_append_z': 'helloz', 'buffer_identity_preserved': True},
        'sendKeyEvent': {'accepted': False, 'all_states': ['current', 'successor', 'terminal', 'dirty', 'stale', 'fatal'],
            'expected': 'clean false/no BaseInputConnection or wrapper entry; a fatal injection at native target cannot fire because there is no native target call'},
        'no_native_equivalence_claim': True, 'requires_selected_source_fresh_execution': True}
    (HERE / 'family-migration.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('PASS emitted design only: 16 named families x 6 states; no new leaf suppression mode')
if __name__ == '__main__': main()
