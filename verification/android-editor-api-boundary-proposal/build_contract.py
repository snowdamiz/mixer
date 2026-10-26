#!/usr/bin/env python3
"""Independently enumerated proposed routes; platform metadata validates them later."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
# Exact JVM descriptors are deliberate declarations, not discovered product policy.
ROUTES = [
    (28, 'beginBatchEdit()Z', 'mutate'),
    (28, 'clearMetaKeyStates(I)Z', 'mutate'),
    (28, 'closeConnection()V', 'close_once'),
    (28, 'commitCompletion(Landroid/view/inputmethod/CompletionInfo;)Z', 'proposal_completion'),
    (28, 'commitContent(Landroid/view/inputmethod/InputContentInfo;ILandroid/os/Bundle;)Z', 'existing_refusal'),
    (28, 'commitCorrection(Landroid/view/inputmethod/CorrectionInfo;)Z', 'existing_refusal'),
    (28, 'commitText(Ljava/lang/CharSequence;I)Z', 'proposal_plain'),
    (28, 'deleteSurroundingText(II)Z', 'mutate'),
    (28, 'deleteSurroundingTextInCodePoints(II)Z', 'mutate'),
    (28, 'endBatchEdit()Z', 'mutate'),
    (28, 'finishComposingText()Z', 'mutate'),
    (28, 'getCursorCapsMode(I)I', 'read'),
    (28, 'getExtractedText(Landroid/view/inputmethod/ExtractedTextRequest;I)Landroid/view/inputmethod/ExtractedText;', 'extract_nonmonitor'),
    (28, 'getHandler()Landroid/os/Handler;', 'null_handler'),
    (28, 'getSelectedText(I)Ljava/lang/CharSequence;', 'read'),
    (28, 'getTextAfterCursor(II)Ljava/lang/CharSequence;', 'read'),
    (28, 'getTextBeforeCursor(II)Ljava/lang/CharSequence;', 'read'),
    (28, 'performContextMenuAction(I)Z', 'context_action'),
    (28, 'performEditorAction(I)Z', 'mutate'),
    (28, 'performPrivateCommand(Ljava/lang/String;Landroid/os/Bundle;)Z', 'existing_refusal'),
    (28, 'reportFullscreenMode(Z)Z', 'mutate'),
    (28, 'requestCursorUpdates(I)Z', 'cursor_disable_only'),
    (28, 'sendKeyEvent(Landroid/view/KeyEvent;)Z', 'proposal_key'),
    (28, 'setComposingRegion(II)Z', 'mutate'),
    (28, 'setComposingText(Ljava/lang/CharSequence;I)Z', 'proposal_composing'),
    (28, 'setSelection(II)Z', 'mutate'),
    (31, 'getSurroundingText(III)Landroid/view/inputmethod/SurroundingText;', 'read'),
    (31, 'performSpellCheck()Z', 'proposed_async_refusal'),
    (31, 'setImeConsumesInput(Z)Z', 'mutate'),
    (33, 'commitText(Ljava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z', 'proposal_plain'),
    (33, 'requestCursorUpdates(II)Z', 'cursor_disable_only'),
    (33, 'setComposingRegion(IILandroid/view/inputmethod/TextAttribute;)Z', 'mutate'),
    (33, 'setComposingText(Ljava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z', 'proposal_composing'),
    (33, 'takeSnapshot()Landroid/view/inputmethod/TextSnapshot;', 'read'),
    (34, 'performHandwritingGesture(Landroid/view/inputmethod/HandwritingGesture;Ljava/util/concurrent/Executor;Ljava/util/function/IntConsumer;)V', 'existing_handwriting_refusal'),
    (34, 'previewHandwritingGesture(Landroid/view/inputmethod/PreviewableHandwritingGesture;Landroid/os/CancellationSignal;)Z', 'existing_refusal'),
    (34, 'replaceText(IILjava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z', 'existing_refusal'),
    (34, 'requestTextBoundsInfo(Landroid/graphics/RectF;Ljava/util/concurrent/Executor;Ljava/util/function/Consumer;)V', 'proposed_bounds_refusal'),
]


def main():
    classes = {28: 'Connection28', 31: 'Api31', 33: 'Api33', 34: 'Api34'}
    contract = {
        'schema': 1,
        'status': 'Proposal only; root contract selection, independent implementation review and source profile are pending',
        'context_revision': '5583fb2c61e2c12acb5f0120a9a072e05cdb5ac1',
        'guards': {'observer_sdk_below_36_refuses': True, 'renderer_sdk_below_36_refuses': True},
        'rendering_contexts_added': False, 'public_v2_selected': False, 'source_profile_selected': False,
        'platform_implementation_superclass': 'java/lang/Object',
        'base_implements': 'android/view/inputmethod/InputConnection',
        'platform_wrapper_setTarget_exposed': False,
        'delegate_dispatch': 'captured immutable target via invokeinterface; no platform super methods',
        'owner_core_or_capture_mint_added': False,
        'auxiliary_async_policy_requires_explicit_selection': True,
        'native_close_policy_requires_explicit_root_amendment': True,
        'implementation_selection_blocked_by_native_close_safety': True,
        'incarnation_only_patch_is_usable_editor_component': False,
        'close_contract': ['retain_exact_target_and_Editable', 'consume_before_native_close',
                           'field_CLOSING_blocks_nested_creation_and_rebinding',
                           'scoped_live_or_sealed_cleanup_callbacks_without_feature_events',
                           'never_close_old_target_on_successor_composition',
                           'unavailable_scope_or_throw_means_quarantine_and_owner_retire',
                           'original_ordinary_and_first_fatal_precedence',
                           'never_close_every_connection_on_temporary_owner_seal',
                           'active_edit_unwind_policy_must_be_selected_before_implementation'],
        'metadata_helpers': [
            {'floor': 34, 'methods': ['setSupportedHandwritingGestures(Ljava/util/List;)V',
                                     'setSupportedHandwritingGesturePreviews(Ljava/util/Set;)V'],
             'policy': 'clear advertisement of existing refused gestures after same-attempt checks'},
            {'floor': 35, 'methods': ['setStylusHandwritingEnabled(Z)V'],
             'policy': 'separately unselected; ordinary stylus text input is not editing gestures'},
            {'floor': 36, 'methods': ['setWritingToolsEnabled(Z)V'],
             'policy': 'separately unselected; never claim unsupported replace from advertisement'}],
        'preflight': {'api28_fields': 'reject_before_native_prepare',
                      'api28_selectable_text': 'reject_before_native_prepare',
                      'pre30_required_accessibilityValue': 'reject_before_native_prepare',
                      'accessibility_label_substitution': False,
                      'api29_authored_setters': 'separately_emitted_Api29_guarded_drawable_installer',
                      'api30_state_description': 'separately_emitted_Api30_guarded_setter'},
        'matrix': [{'sdk': sdk, 'connection_class': classes[max(x for x in classes if x <= sdk)],
                    'private_v2_admitted_by_this_proposal': False,
                    'api28_field_and_selectable_refusal_required': sdk == 28,
                    'required_value_refusal_required': sdk < 30}
                   for sdk in range(28, 38)],
        'methods': [{'descriptor': descriptor, 'declared_class_floor': floor,
                     'declared_class': classes[floor], 'route': route,
                     'main_check_first': True,
                     'captured_entry_and_delegate_return_fence': route not in {
                         'existing_refusal', 'existing_handwriting_refusal', 'null_handler',
                         'proposed_async_refusal', 'proposed_bounds_refusal'}}
                    for floor, descriptor, route in ROUTES],
        'per_call_authority': ['main_looper_first', 'same_field_record_and_generation',
                               'actual_input_open_and_field_focus', 'current_connection_identity',
                               'same_Editable_identity', 'snapshot_selection_and_composing_spans',
                               'recheck_snapshot_after_proposal_before_delegate',
                               'retain_original_Mutation_on_return',
                               'read_return_requires_unchanged_editor_snapshot',
                               'mutation_return_requires_current_same_editor_valid_native_result',
                               'accepted_successor_boolean_rule_does_not_authorize_more_work',
                               'no_replay_or_reacquired_Mutation_or_readiness'],
        'exception_policy': ['delegate_Error_is_never_false', 'preserve_original_RuntimeException',
                             'first_fatal_wins_over_ordinary_failure',
                             'no_retry_or_native_work_after_authority_loss',
                             'existing_owner_cleanup_and_terminal_precedence_unchanged'],
        'pending': ['actual_product_implementation', 'independent_actual_source_host_leaf_review',
                    'source_pair_successor_selection', 'Android_API28_to_37_ART_linkage_and_runtime',
                    'native_IMEs_batch_cleanup_and_subscription_lifecycle',
                    'TalkBack_design_parity_physical_matrix', 'public_routing_and_GA'],
    }
    (HERE / 'contract.json').write_text(json.dumps(contract, indent=2) + '\n')


if __name__ == '__main__':
    main()
