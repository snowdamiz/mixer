package dev.mixer.android;

import android.os.Bundle;
import android.os.Handler;
import android.view.KeyEvent;
import android.view.inputmethod.*;

/** Direct, closed private adapter. No InputConnectionWrapper or inherited forwarding path. */
final class NativeEditorConnectionV2 {
    private NativeEditorConnectionV2() {}
    static Base create(NativeAppearanceViewsV2.NativeField field,NativeAppearanceViewsV2.NativeField.Attempt attempt) {
        // Existing SDK36 admission remains outside this private implementation.
        if(android.os.Build.VERSION.SDK_INT>=34)return new Api34(field,attempt);
        if(android.os.Build.VERSION.SDK_INT>=33)return new Api33(field,attempt);
        if(android.os.Build.VERSION.SDK_INT>=31)return new Api31(field,attempt);
        return new Base(field,attempt);
    }
    static class Base implements InputConnection {
        final NativeAppearanceViewsV2.NativeField field;
        final NativeAppearanceViewsV2.NativeField.Attempt attempt;
        final InputConnection target;
        Base(NativeAppearanceViewsV2.NativeField field,NativeAppearanceViewsV2.NativeField.Attempt attempt) {
            this.field=field;this.attempt=attempt;target=attempt.target;
        }
        final <T> T call(String hook,T refused,java.util.function.Supplier<T> action){return field.dispatch(attempt,hook,refused,action);}
        final boolean no(){NativeEnvironmentV2.requireMain();return false;}
        @Override public final boolean beginBatchEdit(){return call("beginBatch",false,()->target.beginBatchEdit());}
        @Override public final boolean endBatchEdit(){return call("endBatch",false,()->target.endBatchEdit());}
        @Override public final boolean clearMetaKeyStates(int states){return call("meta",false,()->target.clearMetaKeyStates(states));}
        @Override public final void closeConnection(){NativeEnvironmentV2.requireMain();field.close(attempt);}
        @Override public final boolean commitText(CharSequence text,int position){return call("commit",false,()->field.proposal(text,false)&&target.commitText(text,position));}
        @Override public final boolean setComposingText(CharSequence text,int position){return call("compose",false,()->field.proposal(text,true)&&target.setComposingText(text,position));}
        @Override public final boolean setComposingRegion(int start,int end){return call("region",false,()->start>=0&&end>=0&&start<=attempt.editable.length()&&end<=attempt.editable.length()&&target.setComposingRegion(start,end));}
        @Override public final boolean finishComposingText(){return call("finishCompose",false,()->target.finishComposingText());}
        @Override public final boolean deleteSurroundingText(int before,int after){return call("delete",false,()->before>=0&&after>=0&&target.deleteSurroundingText(before,after));}
        @Override public final boolean deleteSurroundingTextInCodePoints(int before,int after){return call("deleteCodePoints",false,()->before>=0&&after>=0&&target.deleteSurroundingTextInCodePoints(before,after));}
        @Override public final boolean setSelection(int start,int end){return call("setSelection",false,()->start>=0&&end>=0&&start<=attempt.editable.length()&&end<=attempt.editable.length()&&target.setSelection(start,end));}
        @Override public final boolean commitCompletion(CompletionInfo value){return call("completion",false,()->value!=null&&field.proposal(value.getText(),false)&&target.commitCompletion(value));}
        @Override public final boolean performContextMenuAction(int id){return call("context",false,()->target.performContextMenuAction(id));}
        @Override public final boolean performEditorAction(int action){NativeEnvironmentV2.requireMain();return action==EditorInfo.IME_ACTION_DONE&&call("action",false,()->target.performEditorAction(action));}
        @Override public final boolean sendKeyEvent(KeyEvent event){return no();}
        @Override public final boolean commitContent(InputContentInfo content,int flags,Bundle options){return no();}
        @Override public final boolean commitCorrection(CorrectionInfo value){return no();}
        @Override public final boolean performPrivateCommand(String action,Bundle data){return no();}
        @Override public final boolean reportFullscreenMode(boolean enabled){NativeEnvironmentV2.requireMain();return !enabled&&call("fullscreenOff",false,()->target.reportFullscreenMode(false));}
        @Override public final boolean requestCursorUpdates(int mode){NativeEnvironmentV2.requireMain();return mode==0&&call("cursorOff",false,()->target.requestCursorUpdates(0));}
        @Override public final ExtractedText getExtractedText(ExtractedTextRequest request,int flags){NativeEnvironmentV2.requireMain();return flags==0?call("extraction",null,()->target.getExtractedText(request,0)):null;}
        @Override public final CharSequence getSelectedText(int flags){NativeEnvironmentV2.requireMain();return flags==0?call("selected",null,()->plain(target.getSelectedText(0))):null;}
        @Override public final CharSequence getTextBeforeCursor(int length,int flags){NativeEnvironmentV2.requireMain();return length>=0&&length<=16384&&flags==0?call("before",null,()->plain(target.getTextBeforeCursor(length,0))):null;}
        @Override public final CharSequence getTextAfterCursor(int length,int flags){NativeEnvironmentV2.requireMain();return length>=0&&length<=16384&&flags==0?call("after",null,()->plain(target.getTextAfterCursor(length,0))):null;}
        @Override public final int getCursorCapsMode(int modes){return call("caps",0,()->target.getCursorCapsMode(modes));}
        private CharSequence plain(CharSequence result){return result==null?null:result.toString();}
        // Android may ask this during bootstrap on any thread. No state read is permitted here.
        @Override public final Handler getHandler(){return null;}
    }
    static class Api31 extends Base {
        Api31(NativeAppearanceViewsV2.NativeField field,NativeAppearanceViewsV2.NativeField.Attempt attempt){super(field,attempt);}
        @Override public final SurroundingText getSurroundingText(int before,int after,int flags){NativeEnvironmentV2.requireMain();return before>=0&&after>=0&&before<=16384&&after<=16384&&flags==0?call("surrounding",null,()->target.getSurroundingText(before,after,0)):null;}
        @Override public final boolean performSpellCheck(){return no();}
        @Override public final boolean setImeConsumesInput(boolean consumes){return call("consumes",false,()->target.setImeConsumesInput(consumes));}
    }
    static class Api33 extends Api31 {
        Api33(NativeAppearanceViewsV2.NativeField field,NativeAppearanceViewsV2.NativeField.Attempt attempt){super(field,attempt);}
        @Override public final boolean commitText(CharSequence text,int position,TextAttribute attributes){return call("commitAttributes",false,()->field.proposal(text,false)&&target.commitText(text,position,attributes));}
        @Override public final boolean setComposingText(CharSequence text,int position,TextAttribute attributes){return call("composeAttributes",false,()->field.proposal(text,true)&&target.setComposingText(text,position,attributes));}
        @Override public final boolean setComposingRegion(int start,int end,TextAttribute attributes){return call("regionAttributes",false,()->start>=0&&end>=0&&start<=attempt.editable.length()&&end<=attempt.editable.length()&&target.setComposingRegion(start,end,attributes));}
        @Override public final boolean requestCursorUpdates(int mode,int filter){NativeEnvironmentV2.requireMain();return mode==0&&filter==0&&call("cursorFilterOff",false,()->target.requestCursorUpdates(0,0));}
        @Override public final TextSnapshot takeSnapshot(){return call("snapshot",null,()->target.takeSnapshot());}
    }
    static final class Api34 extends Api33 {
        Api34(NativeAppearanceViewsV2.NativeField field,NativeAppearanceViewsV2.NativeField.Attempt attempt){super(field,attempt);}
        @Override public boolean replaceText(int start,int end,CharSequence text,int position,TextAttribute attributes){return no();}
        @Override public boolean previewHandwritingGesture(PreviewableHandwritingGesture gesture,android.os.CancellationSignal signal){return no();}
        @Override public void performHandwritingGesture(HandwritingGesture gesture,java.util.concurrent.Executor executor,java.util.function.IntConsumer result) {
            NativeEnvironmentV2.requireMain();if(executor!=null&&result!=null)executor.execute(()->result.accept(InputConnection.HANDWRITING_GESTURE_RESULT_UNSUPPORTED));
        }
        @Override public void requestTextBoundsInfo(android.graphics.RectF bounds,java.util.concurrent.Executor executor,java.util.function.Consumer<TextBoundsInfoResult> result) {
            NativeEnvironmentV2.requireMain();if(executor!=null&&result!=null){TextBoundsInfoResult unsupported=new TextBoundsInfoResult(TextBoundsInfoResult.CODE_UNSUPPORTED);executor.execute(()->result.accept(unsupported));}
        }
    }
}
