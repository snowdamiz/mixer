#!/usr/bin/env python3
"""Index named frozen evidence spans; selectors do not authorize compatibility."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
PRODUCT = 'inputs/native/android/app/src/dev/mixer/android/'
FINDINGS = [
    ('direct_mutation_result_rule', PRODUCT + 'NativeAppearanceViewsV2.java', '        boolean result(boolean result) {', 12),
    ('record_editor_filter_watcher', PRODUCT + 'NativeAppearanceViewsV2.java', '                edit.setFilters(', 16),
    ('field_api29_setters', PRODUCT + 'NativeAppearanceViewsV2.java', '                        field.setTextCursorDrawable', 7),
    ('selectable_text_bind', PRODUCT + 'NativeAppearanceViewsV2.java', '                        TextView text=(TextView)view;', 4),
    ('state_description_skip', PRODUCT + 'NativeAppearanceViewsV2.java', '                    if(android.os.Build.VERSION.SDK_INT>=30)view.setStateDescription', 2),
    ('proposal_validation', PRODUCT + 'NativeAppearanceViewsV2.java', '    private static boolean plainProposal(', 9),
    ('native_field_and_connections', PRODUCT + 'NativeAppearanceViewsV2.java', '    private static final class NativeField extends EditText {', 72),
    ('renderer_input_open', PRODUCT + 'NativeRenderer.java', '        public boolean open(NativeAppearanceViewsV2.Record record){', 13),
    ('renderer_prepare_before_records', PRODUCT + 'NativeRenderer.java', '        AppearanceResolverV2.Plan plan=AppearanceResolverV2.prepare(', 13),
    ('renderer_active_editor_preflight', PRODUCT + 'NativeRenderer.java', '    private void preflightEditorsV2(', 36),
    ('renderer_toggle_only_roster', PRODUCT + 'NativeRenderer.java', '    private void cancelRosterV2(', 10),
    ('renderer_guard', PRODUCT + 'NativeRenderer.java', '    private void requireV2Live(){', 6),
    ('observer_guard', PRODUCT + 'NativeEnvironmentV2.java', '            if (Build.VERSION.SDK_INT < 36', 3),
    ('owner_fence', PRODUCT + 'NativeOwnerV2.java', '    static final class Fence {', 5),
    ('owner_native_input_seal', PRODUCT + 'NativeOwnerV2.java', '    private void nativeInput(', 19),
    ('owner_seal_and_cancel', PRODUCT + 'NativeOwnerV2.java', '    private void seal(boolean terminal)', 28),
    ('native_get_editable_no_close_check', 'official/aosp/36/EditableInputConnection.java', '    public Editable getEditable() {', 9),
    ('native_batch_close_scope', 'official/aosp/36/EditableInputConnection.java', '    public boolean beginBatchEdit() {', 52),
    ('native_context_extraction_spell', 'official/aosp/36/EditableInputConnection.java', '    public boolean performContextMenuAction(', 35),
    ('native_cursor_query_callback', 'official/aosp/36/EditableInputConnection.java', '    public boolean requestCursorUpdates(\n', 81),
    ('native_base_close', 'official/aosp/36/BaseInputConnection.java', '    public void closeConnection() {', 5),
    ('native_commit_no_global_closed', 'official/aosp/36/BaseInputConnection.java', '    public boolean commitText(', 7),
    ('native_editorinfo_creation', 'official/aosp/36/TextView.java', '    public InputConnection onCreateInputConnection(', 103),
    ('native_cursor_request_schedules_layout', 'official/aosp/36/TextView.java', '    public void onRequestCursorUpdatesInternal(', 24),
    ('immutable_set_target_already', 'official/aosp/36/InputConnectionWrapper.java', '    public void setTarget(', 7),
    ('api33_snapshot_default', 'official/aosp/33/InputConnection.java', '    default TextSnapshot takeSnapshot() {', 5),
    ('api34_wrapper_snapshot', 'official/aosp/34/InputConnectionWrapper.java', '    public TextSnapshot takeSnapshot() {', 4),
    ('replace_default_composes_mutations', 'official/aosp/34/InputConnection.java', '    default boolean replaceText(', 16),
]


def main():
    findings = []
    for name, relative, anchor, count in FINDINGS:
        path = HERE / relative
        text = path.read_text()
        start = text.index(anchor)
        line = text.count('\n', 0, start) + 1
        lines = text.splitlines()
        findings.append({'id': name, 'path': relative, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'start_line': line, 'end_line': min(len(lines), line + count - 1),
                         'snippet': '\n'.join(lines[line - 1:line - 1 + count])})
    (HERE / 'source-findings.json').write_text(json.dumps({'scope': 'Named source evidence only; no native execution',
                                                        'findings': findings}, indent=2) + '\n')
    print(f'Indexed {len(findings)} exact frozen source spans.')


if __name__ == '__main__':
    main()
