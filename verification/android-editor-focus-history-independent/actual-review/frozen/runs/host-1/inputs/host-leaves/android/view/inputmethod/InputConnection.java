package android.view.inputmethod;
/** Official SDK descriptor shape; all default bodies are hostile authored tripwires. */
public interface InputConnection { int HANDWRITING_GESTURE_RESULT_UNSUPPORTED=2;
boolean beginBatchEdit();
boolean clearMetaKeyStates(int a0);
void closeConnection();
boolean commitCompletion(android.view.inputmethod.CompletionInfo a0);
boolean commitContent(android.view.inputmethod.InputContentInfo a0, int a1, android.os.Bundle a2);
boolean commitCorrection(android.view.inputmethod.CorrectionInfo a0);
boolean commitText(java.lang.CharSequence a0, int a1);
default boolean commitText(java.lang.CharSequence a0, int a1, android.view.inputmethod.TextAttribute a2) {throw new AssertionError("InputConnection default bypass: commitText");}
boolean deleteSurroundingText(int a0, int a1);
boolean deleteSurroundingTextInCodePoints(int a0, int a1);
boolean endBatchEdit();
boolean finishComposingText();
int getCursorCapsMode(int a0);
android.view.inputmethod.ExtractedText getExtractedText(android.view.inputmethod.ExtractedTextRequest a0, int a1);
android.os.Handler getHandler();
java.lang.CharSequence getSelectedText(int a0);
default android.view.inputmethod.SurroundingText getSurroundingText(int a0, int a1, int a2) {throw new AssertionError("InputConnection default bypass: getSurroundingText");}
java.lang.CharSequence getTextAfterCursor(int a0, int a1);
java.lang.CharSequence getTextBeforeCursor(int a0, int a1);
boolean performContextMenuAction(int a0);
boolean performEditorAction(int a0);
default void performHandwritingGesture(android.view.inputmethod.HandwritingGesture a0, java.util.concurrent.Executor a1, java.util.function.IntConsumer a2) {throw new AssertionError("InputConnection default bypass: performHandwritingGesture");}
boolean performPrivateCommand(java.lang.String a0, android.os.Bundle a1);
default boolean performSpellCheck() {throw new AssertionError("InputConnection default bypass: performSpellCheck");}
default boolean previewHandwritingGesture(android.view.inputmethod.PreviewableHandwritingGesture a0, android.os.CancellationSignal a1) {throw new AssertionError("InputConnection default bypass: previewHandwritingGesture");}
default boolean replaceText(int a0, int a1, java.lang.CharSequence a2, int a3, android.view.inputmethod.TextAttribute a4) {throw new AssertionError("InputConnection default bypass: replaceText");}
boolean reportFullscreenMode(boolean a0);
boolean requestCursorUpdates(int a0);
default boolean requestCursorUpdates(int a0, int a1) {throw new AssertionError("InputConnection default bypass: requestCursorUpdates");}
default void requestTextBoundsInfo(android.graphics.RectF a0, java.util.concurrent.Executor a1, java.util.function.Consumer<android.view.inputmethod.TextBoundsInfoResult> a2) {throw new AssertionError("InputConnection default bypass: requestTextBoundsInfo");}
boolean sendKeyEvent(android.view.KeyEvent a0);
boolean setComposingRegion(int a0, int a1);
default boolean setComposingRegion(int a0, int a1, android.view.inputmethod.TextAttribute a2) {throw new AssertionError("InputConnection default bypass: setComposingRegion");}
boolean setComposingText(java.lang.CharSequence a0, int a1);
default boolean setComposingText(java.lang.CharSequence a0, int a1, android.view.inputmethod.TextAttribute a2) {throw new AssertionError("InputConnection default bypass: setComposingText");}
default boolean setImeConsumesInput(boolean a0) {throw new AssertionError("InputConnection default bypass: setImeConsumesInput");}
boolean setSelection(int a0, int a1);
default android.view.inputmethod.TextSnapshot takeSnapshot() {throw new AssertionError("InputConnection default bypass: takeSnapshot");}
}
