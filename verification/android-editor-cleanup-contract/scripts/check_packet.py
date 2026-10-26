#!/usr/bin/env python3
"""Packet integrity/decision controls only; never product or OTA authorization."""
from pathlib import Path
import copy, hashlib, json

PACK = Path(__file__).resolve().parents[1]
ROOT = PACK.parents[1]

def sha(data): return hashlib.sha256(data).hexdigest()
def validate(contract):
    assert contract['status'] == 'design_for_review_only_no_implementation_selection'
    assert not contract['canonical_changes'] and not contract['owner_core_changes']
    assert not contract['canonical_coordinator_changes']
    assert contract['proposed_coordinator_amendment'] == 'busyForOwnerDisposal consumes editorDisposalBusyV2; disposeOnce guards before disposed/session consumption; owner/core and rendererReportActive unchanged'
    assert contract['no_native_work_in_successful_commit_to_finish']
    assert contract['no_readiness_mint_or_replay'] and contract['no_new_queue_or_handler']
    assert contract['root_selected_design']['creation'] == 'serialized_CREATING_nested_returns_null_before_super_without_stealing_attempt'
    assert contract['root_selected_design']['native_key_transport'] == 'sendKeyEvent_false_before_native_work'
    assert contract['root_selected_design']['editor_action'] == 'configured_IME_ACTION_DONE_only_other_actions_false_before_native_work'
    assert contract['root_selected_design']['getHandler'] == 'constant_null_any_thread_no_delegate_no_field_no_maincheck'
    assert 'temporary_owner_seal' in contract['nontriggers']
    assert contract['scheduler_rejection'] == 'existing_owner_retains_pending_disposal_but_no_autonomous_retry_is_proven'
    assert contract['editor_disposal_busy'] == 'executing_native_call_or_cleanup_only_not_merely_DEFERRED_or_FAILED_UNCERTAIN'

def main():
    collection = json.loads((PACK / 'collection.json').read_text())
    for relative, meta in collection['inputs'].items():
        frozen = PACK / 'inputs' / relative
        assert sha(frozen.read_bytes()) == meta['sha256'], relative
        assert sha((ROOT / relative).read_bytes()) == meta['sha256'], 'live input drift: ' + relative
    for name, meta in collection['official_snapshots'].items():
        assert sha((PACK / 'official' / name).read_bytes()) == meta['sha256'], name
    # Assert the independently fetched snapshots against the recorded official URLs.
    for item in json.loads((PACK / 'official/collection.json').read_text())['sources']:
        name = item['url'].split('/')[-1].split('?')[0]
        assert sha((PACK / 'official' / name).read_bytes()) == item['sha256'], name
    contract = json.loads((PACK / 'contract.json').read_text()); validate(contract)
    negatives = [
        ('creator-race', lambda c: c['root_selected_design'].update(creation='newest_nested_wins')),
        ('unowned-key-queue', lambda c: c['root_selected_design'].update(native_key_transport='delegate')),
        ('arbitrary-action-queue', lambda c: c['root_selected_design'].update(editor_action='all_actions')),
        ('bootstrap-ui-access', lambda c: c['root_selected_design'].update(getHandler='main_then_delegate')),
        ('false-owner-qualification', lambda c: c.update(owner_core_changes=True)),
        ('false-scheduler-completion', lambda c: c.update(scheduler_rejection='guaranteed_complete')),
        ('temporary-seal-close', lambda c: c['nontriggers'].remove('temporary_owner_seal')),
        ('deferred-busy-deadlock', lambda c: c.update(editor_disposal_busy='all_deferred_records')),
        ('commit-finish-native-work', lambda c: c.update(no_native_work_in_successful_commit_to_finish=False)),
        ('predicate-only-incomplete', lambda c: c.update(proposed_coordinator_amendment='busy_predicate_only')),
    ]
    rejected = []
    for name, mutate in negatives:
        mutant = copy.deepcopy(contract); mutate(mutant)
        try: validate(mutant)
        except AssertionError: rejected.append(name)
        else: raise AssertionError('negative control accepted: ' + name)
    specs = [
        ('inputs/native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java','views-mutation','    static final class Mutation {','    record Binding('),
        ('inputs/native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java','views-record-callbacks','                edit.addTextChangedListener','                edit.setOnEditorActionListener'),
        ('inputs/native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java','views-field','    private static final class NativeField','    private static final class NativeSwitch'),
        ('inputs/native/android/app/src/dev/mixer/android/NativeRenderer.java','renderer-input','    private NativeAppearanceViewsV2.Input inputV2()','    InstalledAppearanceV2 captureInstalledV2()'),
        ('inputs/native/android/app/src/dev/mixer/android/NativeRenderer.java','renderer-preflight','    private void preflightEditorsV2','    private void validateV2'),
        ('inputs/native/android/app/src/dev/mixer/android/NativeRenderer.java','renderer-finish','    void finishV2','    void validateAttachedV2'),
        ('inputs/native/android/app/src/dev/mixer/android/NativeRenderer.java','renderer-disposal','    void disposeV2','    private void requireV2Live'),
        ('inputs/native/android/app/src/dev/mixer/android/NativeCoordinatorV2.java','coordinator-disposal','    boolean inputCancellationInProgress','    private static void requireMain'),
        ('inputs/native/android/app/src/dev/mixer/android/NativeOwnerV2.java','owner-work','    private enum WorkKind','    private final Activity'),
        ('inputs/native/android/app/src/dev/mixer/android/NativeOwnerV2.java','owner-post','    private void post(Work work)','    private void cancelQueued'),
        ('inputs/native/android/app/src/dev/mixer/android/NativeOwnerV2.java','owner-disposal','    private void closePending','    private void completeCleanup'),
        ('official/EditableInputConnection.java','native-target-close','    private final TextView mTextView;','    @Override\n    public boolean clearMetaKeyStates'),
        ('official/BaseInputConnection.java','base-close','    public void closeConnection()','    /**\n     * Default implementation uses'),
        ('official/BaseInputConnection.java','base-native-suffix','    private void replaceText(CharSequence','    /**\n     * Default implementation which invokes'),
        ('official/BaseInputConnection.java','base-bootstrap','    public Handler getHandler()','    /**\n     * The default implementation places'),
        ('official/BaseInputConnection.java','base-key-queue','    public boolean sendKeyEvent(KeyEvent event)','    /** Updates InputMethodManager'),
        ('official/TextView.java','native-creator','    public InputConnection onCreateInputConnection(EditorInfo','    /**',),
        ('official/TextView.java','native-editor-action','    public void onEditorAction(int actionCode)','    /**',),
        ('official/TextView.java','native-lifecycle','    protected void onFocusChanged(boolean focused','    public void onVisibilityAggregated(boolean isVisible)'),
        ('official/View.java','native-detach-order','    void dispatchDetachedFromWindow()','    /**',),
        ('official/InputMethodManager.java','bootstrap-thread','    private boolean startInputInner(','            mServedInputConnection = servedInputConnection;'),
        ('official/InputMethodManager.java','key-forward','    public void dispatchKeyEventFromInputMethod(','    // Must be called on the main looper'),
        ('official/ViewRootImpl.java','key-queue','    public void dispatchKeyFromIme(KeyEvent event)','    public void dispatchKeyFromAutofill'),
        ('official/EditorInfo.java','metadata-clearing','    public void setInitialSurroundingSubText','    /**',),
    ]
    anchors = []
    for relative, name, begin, end in specs:
        source = (PACK / relative).read_text(); start = source.index(begin); finish = source.index(end,start+len(begin))
        snippet = source[start:finish]
        anchors.append({'name':name,'path':relative,'line_start':source[:start].count('\n')+1,
                        'line_end':source[:finish].count('\n'),'sha256':sha(snippet.encode()),
                        'begin':begin,'end':end})
    fragments = json.loads((PACK / 'source-fragments.json').read_text())
    for fragment in fragments.values(): assert sha(fragment['source'].encode()) == fragment['sha256']
    for variant in ['actual','candidate']:
        source = (PACK / 'probe-source' / variant / 'DisposalProbe.java').read_text()
        for name in ['Work','post','removeWork','closePending','settle','enter','inputBusy','leave','closeFromOwner','retireScalar']:
            assert fragments[name]['source'] in source, (variant,name)
        if variant == 'actual':
            for name in ['busy','disposeOnce']: assert fragments[name]['source'] in source, name
        else:
            assert 'if (disposed || busyForOwnerDisposal()) return;' in source
            assert '|| renderer.editorDisposalBusyV2();' in source
    (PACK / 'source-map.json').write_text(json.dumps({'schema':1,'anchors':anchors},indent=2)+'\n')
    report = {'scope':'packet consistency only; not product/native/release qualification',
              'source_anchors':len(anchors),'negative_controls_rejected':rejected,
              'frozen_members_verified_by_collection':203,'actual_source_fragments':len(fragments)}
    (PACK / 'controls.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report))

if __name__=='__main__':main()
