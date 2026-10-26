package android.view.inputmethod;
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
