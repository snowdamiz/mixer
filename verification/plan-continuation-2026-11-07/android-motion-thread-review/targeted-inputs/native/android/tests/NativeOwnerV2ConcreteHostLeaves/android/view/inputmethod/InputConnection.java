package android.view.inputmethod;

/** Controlled host signatures. Unmodeled operations return refusal values. */
public interface InputConnection {
    int HANDWRITING_GESTURE_RESULT_UNSUPPORTED=2;
    boolean commitText(CharSequence text,int position);
    boolean setComposingText(CharSequence text,int position);
    boolean setComposingRegion(int start,int end);
    boolean finishComposingText();
    boolean deleteSurroundingText(int before,int after);
    boolean deleteSurroundingTextInCodePoints(int before,int after);
    boolean setSelection(int start,int end);
    boolean performEditorAction(int action);
    boolean sendKeyEvent(android.view.KeyEvent event);
    boolean performPrivateCommand(String action,android.os.Bundle data);
    boolean commitCompletion(CompletionInfo value);
    boolean commitCorrection(CorrectionInfo value);
    boolean commitContent(InputContentInfo content,int flags,android.os.Bundle options);
    boolean beginBatchEdit();
    boolean endBatchEdit();
    boolean clearMetaKeyStates(int states);
    void closeConnection();

    default boolean performContextMenuAction(int id){return false;}
    default boolean reportFullscreenMode(boolean enabled){return false;}
    default boolean requestCursorUpdates(int mode){return false;}
    default ExtractedText getExtractedText(ExtractedTextRequest request,int flags){return null;}
    default CharSequence getSelectedText(int flags){return null;}
    default CharSequence getTextBeforeCursor(int length,int flags){return null;}
    default CharSequence getTextAfterCursor(int length,int flags){return null;}
    default int getCursorCapsMode(int modes){return 0;}
    default android.os.Handler getHandler(){return null;}

    // The host combines API levels. Defaults leave later methods unavailable to earlier adapters.
    default SurroundingText getSurroundingText(int before,int after,int flags){return null;}
    default boolean performSpellCheck(){return false;}
    default boolean setImeConsumesInput(boolean consumes){return false;}
    default boolean commitText(CharSequence text,int position,TextAttribute attributes){return false;}
    default boolean setComposingText(CharSequence text,int position,TextAttribute attributes){return false;}
    default boolean setComposingRegion(int start,int end,TextAttribute attributes){return false;}
    default boolean requestCursorUpdates(int mode,int filter){return false;}
    default TextSnapshot takeSnapshot(){return null;}
    default boolean replaceText(int start,int end,CharSequence text,int position,TextAttribute attributes){return false;}
    default boolean previewHandwritingGesture(PreviewableHandwritingGesture gesture,android.os.CancellationSignal cancellation){return false;}
    default void performHandwritingGesture(HandwritingGesture gesture,java.util.concurrent.Executor executor,java.util.function.IntConsumer result){}
    default void requestTextBoundsInfo(android.graphics.RectF bounds,java.util.concurrent.Executor executor,java.util.function.Consumer<TextBoundsInfoResult> result){}
}
