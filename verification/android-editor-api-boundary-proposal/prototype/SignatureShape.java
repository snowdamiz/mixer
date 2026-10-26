package dev.mixer.editor.proposal;

import android.os.Bundle;
import android.os.Handler;
import android.view.KeyEvent;
import android.view.inputmethod.CompletionInfo;
import android.view.inputmethod.CorrectionInfo;
import android.view.inputmethod.ExtractedText;
import android.view.inputmethod.ExtractedTextRequest;
import android.view.inputmethod.InputConnection;
import android.view.inputmethod.InputContentInfo;

/**
 * UNSELECTED SIGNATURE EXPERIMENT. Never execute this proxy or package it as Mixer.
 * It intentionally has NO owner, input or mutation authority. Compilation checks
 * method/type isolation only. Product implementation must add the separate
 * contract's entry/return fence and native selection/composition controls.
 */
public final class SignatureShape {
    private SignatureShape() {}

    // A shape-only input. The proposed production selector must read real SDK_INT;
    // it cannot expose a caller override or manufacture a rendering context.
    public static InputConnection createShape(int sdk, InputConnection target) {
        if (sdk < 28) throw new UnsupportedOperationException("below shape floor");
        if (sdk >= 34) return new Api34(target);
        if (sdk >= 33) return new Api33(target);
        if (sdk >= 31) return new Api31(target);
        return new Connection28(target);
    }

    static class Connection28 implements InputConnection {
        final InputConnection target;
        Connection28(InputConnection target) { this.target = target; }
        @Override public final boolean beginBatchEdit() { return target.beginBatchEdit(); }
        @Override public final boolean clearMetaKeyStates(int states) { return target.clearMetaKeyStates(states); }
        @Override public final void closeConnection() { target.closeConnection(); }
        @Override public final boolean commitCompletion(CompletionInfo value) { return target.commitCompletion(value); }
        @Override public final boolean commitContent(InputContentInfo value, int flags, Bundle options) { return false; }
        @Override public final boolean commitCorrection(CorrectionInfo value) { return false; }
        @Override public final boolean commitText(CharSequence text, int position) { return target.commitText(text, position); }
        @Override public final boolean deleteSurroundingText(int before, int after) { return target.deleteSurroundingText(before, after); }
        @Override public final boolean deleteSurroundingTextInCodePoints(int before, int after) { return target.deleteSurroundingTextInCodePoints(before, after); }
        @Override public final boolean endBatchEdit() { return target.endBatchEdit(); }
        @Override public final boolean finishComposingText() { return target.finishComposingText(); }
        @Override public final int getCursorCapsMode(int modes) { return target.getCursorCapsMode(modes); }
        @Override public final ExtractedText getExtractedText(ExtractedTextRequest request, int flags) {
            return flags == 0 ? target.getExtractedText(request, flags) : null;
        }
        @Override public final Handler getHandler() { return null; }
        @Override public final CharSequence getSelectedText(int flags) { return target.getSelectedText(flags); }
        @Override public final CharSequence getTextAfterCursor(int length, int flags) { return target.getTextAfterCursor(length, flags); }
        @Override public final CharSequence getTextBeforeCursor(int length, int flags) { return target.getTextBeforeCursor(length, flags); }
        @Override public final boolean performContextMenuAction(int id) { return target.performContextMenuAction(id); }
        @Override public final boolean performEditorAction(int action) { return target.performEditorAction(action); }
        @Override public final boolean performPrivateCommand(String action, Bundle data) { return false; }
        @Override public final boolean reportFullscreenMode(boolean enabled) { return target.reportFullscreenMode(enabled); }
        @Override public final boolean requestCursorUpdates(int mode) { return mode == 0 && target.requestCursorUpdates(0); }
        @Override public final boolean sendKeyEvent(KeyEvent event) { return target.sendKeyEvent(event); }
        @Override public final boolean setComposingRegion(int start, int end) { return target.setComposingRegion(start, end); }
        @Override public final boolean setComposingText(CharSequence text, int position) { return target.setComposingText(text, position); }
        @Override public final boolean setSelection(int start, int end) { return target.setSelection(start, end); }
    }

    static class Api31 extends Connection28 {
        Api31(InputConnection target) { super(target); }
        @Override public final android.view.inputmethod.SurroundingText getSurroundingText(int before, int after, int flags) {
            return target.getSurroundingText(before, after, flags);
        }
        @Override public final boolean performSpellCheck() { return false; }
        @Override public final boolean setImeConsumesInput(boolean consumes) { return target.setImeConsumesInput(consumes); }
    }

    static class Api33 extends Api31 {
        Api33(InputConnection target) { super(target); }
        @Override public final boolean commitText(CharSequence text, int position, android.view.inputmethod.TextAttribute attributes) {
            return target.commitText(text, position, attributes);
        }
        @Override public final boolean requestCursorUpdates(int mode, int filter) {
            return mode == 0 && filter == 0 && target.requestCursorUpdates(0, 0);
        }
        @Override public final boolean setComposingRegion(int start, int end, android.view.inputmethod.TextAttribute attributes) {
            return target.setComposingRegion(start, end, attributes);
        }
        @Override public final boolean setComposingText(CharSequence text, int position, android.view.inputmethod.TextAttribute attributes) {
            return target.setComposingText(text, position, attributes);
        }
        // Direct interface dispatch exists on API33. No wrapper super method is used.
        @Override public final android.view.inputmethod.TextSnapshot takeSnapshot() { return target.takeSnapshot(); }
    }

    static final class Api34 extends Api33 {
        Api34(InputConnection target) { super(target); }
        @Override public void performHandwritingGesture(android.view.inputmethod.HandwritingGesture gesture,
                java.util.concurrent.Executor executor, java.util.function.IntConsumer consumer) {
            if (executor != null && consumer != null) executor.execute(() -> consumer.accept(HANDWRITING_GESTURE_RESULT_UNSUPPORTED));
        }
        @Override public boolean previewHandwritingGesture(android.view.inputmethod.PreviewableHandwritingGesture gesture,
                android.os.CancellationSignal cancellation) { return false; }
        @Override public boolean replaceText(int start, int end, CharSequence text, int position,
                android.view.inputmethod.TextAttribute attributes) { return false; }
        @Override public void requestTextBoundsInfo(android.graphics.RectF bounds,
                java.util.concurrent.Executor executor,
                java.util.function.Consumer<android.view.inputmethod.TextBoundsInfoResult> consumer) {
            if (executor != null && consumer != null) {
                android.view.inputmethod.TextBoundsInfoResult result = new android.view.inputmethod.TextBoundsInfoResult(
                    android.view.inputmethod.TextBoundsInfoResult.CODE_UNSUPPORTED);
                executor.execute(() -> consumer.accept(result));
            }
        }
    }
}
