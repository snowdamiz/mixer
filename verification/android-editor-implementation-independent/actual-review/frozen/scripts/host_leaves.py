from pathlib import Path
D=Path(__file__).resolve().parents[1]/'host-leaves';im=D/'android/view/inputmethod'
p=im/'InputConnection.java';x=p.read_text();x=x.replace('void performHandwritingGesture', '''int getCursorCapsMode(int modes);
ExtractedText getExtractedText(ExtractedTextRequest request,int flags);
android.os.Handler getHandler();
CharSequence getSelectedText(int flags);
CharSequence getTextAfterCursor(int length,int flags);
CharSequence getTextBeforeCursor(int length,int flags);
boolean performContextMenuAction(int id);
boolean reportFullscreenMode(boolean enabled);
boolean requestCursorUpdates(int mode);
boolean requestCursorUpdates(int mode,int filter);
SurroundingText getSurroundingText(int before,int after,int flags);
boolean performSpellCheck();
TextSnapshot takeSnapshot();
void requestTextBoundsInfo(android.graphics.RectF bounds,java.util.concurrent.Executor executor,java.util.function.Consumer<TextBoundsInfoResult> result);
void performHandwritingGesture''');p.write_text(x)
p=im/'InputConnectionWrapper.java';x=p.read_text().replace('public class InputConnectionWrapper','public abstract class InputConnectionWrapper');p.write_text(x)
(im/'EditorInfo.java').write_text('''package android.view.inputmethod;
import java.util.List;import java.util.Set;import android.os.Bundle;import android.os.LocaleList;import dev.mixer.android.ConcreteHostProbe;
/** Authored leaf reproduces the documented invalid-selection private surrounding clearing rule only. */
public class EditorInfo {
 public static final int IME_ACTION_DONE=6,IME_MASK_ACTION=255,IME_FLAG_NAVIGATE_NEXT=0x08000000,IME_FLAG_NAVIGATE_PREVIOUS=0x04000000,IME_FLAG_NO_EXTRACT_UI=0x10000000,IME_FLAG_NO_FULLSCREEN=0x02000000;
 public int inputType,imeOptions,actionId,initialSelStart=-1,initialSelEnd=-1,initialCapsMode,fieldId;public String packageName,privateImeOptions;public CharSequence actionLabel,label,hintText;public Bundle extras;public String[] contentMimeTypes;public LocaleList hintLocales;
 private CharSequence surrounding;public List<Class<? extends HandwritingGesture>> gestures=List.of(HandwritingGesture.class);public Set<Class<? extends PreviewableHandwritingGesture>> previews=Set.of(PreviewableHandwritingGesture.class);public boolean stylus=true;
 public void setSupportedHandwritingGestures(List<Class<? extends HandwritingGesture>> values){ConcreteHostProbe.hit("EditorInfo.setSupportedHandwritingGestures","entry",this);gestures=values;ConcreteHostProbe.hit("EditorInfo.setSupportedHandwritingGestures","beforeReturn",this);}
 public void setSupportedHandwritingGesturePreviews(Set<Class<? extends PreviewableHandwritingGesture>> values){ConcreteHostProbe.hit("EditorInfo.setSupportedHandwritingGesturePreviews","entry",this);previews=values;ConcreteHostProbe.hit("EditorInfo.setSupportedHandwritingGesturePreviews","beforeReturn",this);}
 public void setInitialSurroundingText(CharSequence value){ConcreteHostProbe.hit("EditorInfo.setInitialSurroundingText","entry",this);surrounding=initialSelStart<0||initialSelEnd<0?null:value;ConcreteHostProbe.hit("EditorInfo.setInitialSurroundingText","beforeReturn",this);}
 public CharSequence hostSurrounding(){return surrounding;}
}
''')
(im/'ExtractedText.java').write_text('package android.view.inputmethod;public class ExtractedText {public CharSequence text;public int startOffset,partialStartOffset=-1,partialEndOffset=-1,selectionStart,selectionEnd,flags;}\n')
(im/'ExtractedTextRequest.java').write_text('package android.view.inputmethod;public class ExtractedTextRequest {public int token,flags,hintMaxChars,hintMaxLines;}\n')
(im/'SurroundingText.java').write_text('package android.view.inputmethod;public final class SurroundingText {private final CharSequence text;private final int start,end,offset;public SurroundingText(CharSequence text,int start,int end,int offset){this.text=text;this.start=start;this.end=end;this.offset=offset;}public CharSequence getText(){return text;}public int getSelectionStart(){return start;}public int getSelectionEnd(){return end;}public int getOffset(){return offset;}}\n')
(im/'TextSnapshot.java').write_text('package android.view.inputmethod;public final class TextSnapshot {private final SurroundingText text;public TextSnapshot(SurroundingText text){this.text=text;}public SurroundingText getSurroundingText(){return text;}}\n')
(im/'TextBoundsInfoResult.java').write_text('package android.view.inputmethod;public final class TextBoundsInfoResult {public static final int CODE_UNSUPPORTED=3;private final int code;public TextBoundsInfoResult(int code){this.code=code;}public int getResultCode(){return code;}public Object getTextBoundsInfo(){return null;}}\n')
p=im/'BaseInputConnection.java';x=p.read_text();idx=x.rfind('}')
x=x[:idx]+'''
 @Override public int getCursorCapsMode(int modes){enter("getCursorCapsMode");done("getCursorCapsMode",true);return modes;}
 @Override public ExtractedText getExtractedText(ExtractedTextRequest request,int flags){enter("getExtractedText");ExtractedText value=new ExtractedText();value.text=editor.getText().toString();value.selectionStart=editor.getSelectionStart();value.selectionEnd=editor.getSelectionEnd();done("getExtractedText",true);return value;}
 @Override public android.os.Handler getHandler(){enter("getHandler");return new android.os.Handler();}
 @Override public CharSequence getSelectedText(int flags){enter("getSelectedText");String value=editor.getText().toString().substring(Math.min(editor.getSelectionStart(),editor.getSelectionEnd()),Math.max(editor.getSelectionStart(),editor.getSelectionEnd()));done("getSelectedText",true);return value;}
 @Override public CharSequence getTextBeforeCursor(int length,int flags){enter("getTextBeforeCursor");String value=editor.getText().toString().substring(Math.max(0,editor.getSelectionStart()-length),editor.getSelectionStart());done("getTextBeforeCursor",true);return value;}
 @Override public CharSequence getTextAfterCursor(int length,int flags){enter("getTextAfterCursor");String value=editor.getText().toString().substring(editor.getSelectionEnd(),Math.min(editor.getText().length(),editor.getSelectionEnd()+length));done("getTextAfterCursor",true);return value;}
 @Override public boolean performContextMenuAction(int id){enter("performContextMenuAction");return done("performContextMenuAction",editor.onTextContextMenuItem(id));}
 @Override public boolean reportFullscreenMode(boolean enabled){enter("reportFullscreenMode");return done("reportFullscreenMode",true);}
 @Override public boolean requestCursorUpdates(int mode){enter("requestCursorUpdates");return done("requestCursorUpdates",true);}
 @Override public boolean requestCursorUpdates(int mode,int filter){enter("requestCursorUpdatesFiltered");return done("requestCursorUpdatesFiltered",true);}
 @Override public SurroundingText getSurroundingText(int before,int after,int flags){enter("getSurroundingText");SurroundingText value=new SurroundingText(editor.getText().toString(),editor.getSelectionStart(),editor.getSelectionEnd(),0);done("getSurroundingText",true);return value;}
 @Override public boolean performSpellCheck(){enter("performSpellCheck");return done("performSpellCheck",true);}
 @Override public TextSnapshot takeSnapshot(){enter("takeSnapshot");TextSnapshot value=new TextSnapshot(new SurroundingText(editor.getText().toString(),editor.getSelectionStart(),editor.getSelectionEnd(),0));done("takeSnapshot",true);return value;}
 @Override public void requestTextBoundsInfo(android.graphics.RectF bounds,java.util.concurrent.Executor executor,java.util.function.Consumer<TextBoundsInfoResult> result){enter("requestTextBoundsInfo");if(executor!=null&&result!=null)executor.execute(()->result.accept(new TextBoundsInfoResult(TextBoundsInfoResult.CODE_UNSUPPORTED)));}
''' + x[idx:];x=x.replace('public int mutations;public boolean closed;','public int mutations,closeCalls;public boolean closed;').replace('closeConnection(){enter("closeConnection");closed=true;', 'closeConnection(){enter("closeConnection");closeCalls++;finishComposingText();closed=true;');p.write_text(x)
p=D/'android/widget/TextView.java';x=p.read_text().replace(' public Editable getText(){return text;}public void setText(CharSequence value){',' public enum BufferType { NORMAL,SPANNABLE,EDITABLE }\n public Editable getText(){hit("TextView.getText");Editable value=text;done("TextView.getText");return value;}public final void setText(CharSequence value){setText(value,BufferType.EDITABLE);}\n public void setText(CharSequence value,BufferType type){');p.write_text(x)
p=D/'android/widget/EditText.java';x=p.read_text();x=x.replace('connectionAcquisitions++;lastConnection=', 'connectionAcquisitions++;if(info!=null){info.inputType=inputType;info.imeOptions=imeOptions;info.initialSelStart=getSelectionStart();info.initialSelEnd=getSelectionEnd();info.setInitialSurroundingText(getText().toString());}lastConnection=');p.write_text(x)
p=D/'android/view/View.java';x=p.read_text().replace('public void onRtlPropertiesChanged(int value){','public void onVisibilityAggregated(boolean visible){hit("View.onVisibilityAggregated");done("View.onVisibilityAggregated");}public void onRtlPropertiesChanged(int value){');p.write_text(x)
