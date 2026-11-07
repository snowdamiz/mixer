package dev.mixer.android;

import android.app.Activity;
import android.os.Bundle;
import android.text.Editable;
import android.text.InputFilter;
import android.text.SpannableStringBuilder;
import android.text.Spanned;
import android.text.SpannedString;
import android.text.TextWatcher;
import android.view.View;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.inputmethod.EditorInfo;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Switch;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/** Behavioral checks for the controlled leaves, not Android framework qualification. */
public final class NativeAndroidFixtureHostTests {
    private NativeAndroidFixtureHostTests() {}
    private static int checks;
    private static void check(boolean value,String message) {
        checks++;
        if(!value)throw new AssertionError("controlled Android fixture: "+message);
    }
    private static final class RecordingEditor extends EditText {
        final List<String> callbacks=new ArrayList<>();
        RecordingEditor(){super(new Activity());}
        @Override protected void onSelectionChanged(int start,int end) {
            super.onSelectionChanged(start,end);
            if(callbacks!=null)callbacks.add("selection:"+start+":"+end);
        }
    }
    private static void snapshots() {
        SpannableStringBuilder source=new SpannableStringBuilder("hello");
        Object span=new Object();source.setSpan(span,1,4,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        SpannedString snapshot=new SpannedString(source);
        SpannableStringBuilder copy=new SpannableStringBuilder(snapshot);
        source.clear();
        check(snapshot.toString().equals("hello")&&copy.toString().equals("hello"),"snapshot retained mutable source text");
        for(Spanned value:List.of(snapshot,copy)) {
            check(value.getSpans(0,5,Object.class).length==1&&value.getSpans(0,5,Object.class)[0]==span,"span identity lost");
            check(value.getSpanStart(span)==1&&value.getSpanEnd(span)==4&&value.getSpanFlags(span)==Spanned.SPAN_EXCLUSIVE_EXCLUSIVE,"span range or flags lost");
        }
        copy.clear();check(snapshot.toString().equals("hello")&&snapshot.getSpanStart(span)==1,"copy changed immutable snapshot");
    }
    private static void replacementCallbacks() {
        RecordingEditor editor=new RecordingEditor();editor.setText("old");
        Editable old=editor.getEditableText();editor.callbacks.clear();
        CharSequence proposal=new SpannedString("new");int[] filtered={0};
        editor.setFilters(new InputFilter[]{(src,start,end,dst,dstart,dend)->{
            filtered[0]++;
            check(src==proposal&&start==0&&end==3,"replacement proposal changed before filter");
            check(dst!=old&&dst.length()==0&&dstart==0&&dend==0,"replacement filter did not receive empty destination");
            return null;
        }});
        editor.addTextChangedListener(new TextWatcher(){
            public void beforeTextChanged(CharSequence value,int start,int count,int after){editor.callbacks.add("before:"+value);}
            public void onTextChanged(CharSequence value,int start,int before,int count){editor.callbacks.add("changed:"+value);}
            public void afterTextChanged(Editable value){check(value==editor.getEditableText(),"watcher saw foreign Editable");editor.callbacks.add("after:"+value);}
        });
        editor.setText(proposal);
        check(filtered[0]==1,"replacement filter count");
        check(editor.getEditableText()!=old&&editor.getEditableText().getClass()==SpannableStringBuilder.class,"replacement identity/type");
        check(old.toString().equals("old")&&editor.getText().toString().equals("new"),"old buffer mutated during replacement");
        check(editor.callbacks.equals(List.of("before:old","selection:0:0","changed:new","after:new")),"replacement callback order: "+editor.callbacks);
        Editable current=editor.getEditableText();editor.callbacks.clear();
        editor.setFilters(new InputFilter[]{(src,start,end,dst,dstart,dend)->{
            check(dst==current&&dstart==1&&dend==2,"in-place filter lost destination identity");return null;
        }});
        check(editor.hostReplace(1,2,"X"),"in-place edit refused");
        check(editor.getEditableText()==current&&current.toString().equals("nXw"),"in-place edit replaced identity");
        check(editor.callbacks.equals(List.of("before:new","changed:nXw","selection:2:2","after:nXw")),"in-place callback order: "+editor.callbacks);
        editor.setFilters(new InputFilter[0]);editor.callbacks.clear();editor.hostNotifyEditorCallbacks=false;
        try {
            editor.hostReplace(0,1,"q");editor.setSelection(1,1);
            check(editor.getEditableText()==current&&current.toString().equals("qXw")&&editor.callbacks.isEmpty(),"non-notifying native edit control");
        } finally {editor.hostNotifyEditorCallbacks=true;}
        editor.hostReplace(0,1,"r");
        check(!editor.callbacks.isEmpty()&&current.toString().equals("rXw"),"callback delivery not restored");
    }
    private static void editorOutput() {
        EditText editor=new EditText(new Activity());editor.setText("hello");editor.setSelection(1,3);
        editor.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        editor.setImeOptions(EditorInfo.IME_ACTION_DONE|EditorInfo.IME_FLAG_NAVIGATE_NEXT|EditorInfo.IME_FLAG_NAVIGATE_PREVIOUS);
        EditorInfo info=new EditorInfo();
        check(editor.onCreateInputConnection(info)==editor.lastConnection&&editor.connectionAcquisitions==1,"connection acquisition identity/count");
        check(info.inputType==editor.inputType&&info.imeOptions==editor.imeOptions&&info.initialSelStart==1&&info.initialSelEnd==3,"creator did not populate EditorInfo");
        check(info.getInitialSurroundingText(0,0,0)!=null&&info.hostSurrounding().toString().equals("hello"),"surrounding text was not retained");
        check(!info.getSupportedHandwritingGestures().isEmpty()&&!info.getSupportedHandwritingGesturePreviews().isEmpty(),"hostile gesture defaults missing");
        info.setSupportedHandwritingGestures(List.of());info.setSupportedHandwritingGesturePreviews(Set.of());
        check(info.getSupportedHandwritingGestures().isEmpty()&&info.getSupportedHandwritingGesturePreviews().isEmpty(),"gesture clearing ignored");
        info.initialSelStart=-1;info.initialSelEnd=-1;info.setInitialSurroundingText("");
        check(info.getInitialSurroundingText(0,0,0)==null&&info.hostSurrounding()==null,"invalid-selection scrub retained private payload");
        for(String method:List.of("EditorInfo.setSupportedHandwritingGestures","EditorInfo.setSupportedHandwritingGesturePreviews","EditorInfo.setInitialSurroundingText"))
            check(ConcreteHostProbe.count(method,"entry")>0&&ConcreteHostProbe.count(method,"entry")==ConcreteHostProbe.count(method,"beforeReturn"),"missing callback phase: "+method);
        EditText.creatorNull=true;
        try{check(editor.onCreateInputConnection(new EditorInfo())==null&&editor.connectionAcquisitions==2,"null creator control ignored");}
        finally{EditText.creatorNull=false;}
    }
    private static void configurationAndLifecycle() {
        EditText editor=new EditText(new Activity());
        check(editor.getAutoLinkMask()==0&&editor.getMovementMethod()==android.text.method.ArrowKeyMovementMethod.getInstance()&&editor.getTransformationMethod()==null,"default replacement configuration");
        check(android.text.method.SingleLineTransformationMethod.getInstance()==android.text.method.SingleLineTransformationMethod.getInstance(),"transformation singleton identity");
        check(TextView.BufferType.valueOf("EDITABLE")==TextView.BufferType.EDITABLE,"editable buffer enum");
        View.AccessibilityDelegate delegate=new View.AccessibilityDelegate();
        editor.setAccessibilityDelegate(delegate);check(editor.getAccessibilityDelegate()==delegate,"delegate identity");
        editor.setAccessibilityDelegate(null);check(editor.getAccessibilityDelegate()==null,"delegate reset");
        editor.onVisibilityAggregated(false);editor.onVisibilityAggregated(true);
        check(ConcreteHostProbe.count("View.onVisibilityAggregated","entry")==2&&ConcreteHostProbe.count("View.onVisibilityAggregated","beforeReturn")==2,"aggregate visibility callback phases");
    }
    private static void accessibilityReplacement() {
        EditText editor=new EditText(new Activity());editor.setText("old");
        Bundle arguments=new Bundle();arguments.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,"changed");
        Editable old=editor.getEditableText();
        check(editor.performAccessibilityAction(AccessibilityNodeInfo.ACTION_SET_TEXT,arguments),"accessibility replacement refused");
        check(editor.getEditableText()!=old&&editor.getText().toString().equals("changed")&&editor.getSelectionStart()==7,"accessibility replacement result");
        editor.setEnabled(false);old=editor.getEditableText();
        check(!editor.performAccessibilityAction(AccessibilityNodeInfo.ACTION_SET_TEXT,arguments)&&editor.getEditableText()==old,"disabled replacement mutated buffer");
        editor.setEnabled(true);TextView.accessibilitySetTextBehavior=2;
        try{check(editor.performAccessibilityAction(AccessibilityNodeInfo.ACTION_SET_TEXT,arguments)&&editor.getEditableText()==old,"no-effect control did not preserve identity");}
        finally{TextView.accessibilitySetTextBehavior=0;}
    }
    private static void switchClickContract() {
        Switch toggle=new Switch(new Activity());
        check(!toggle.performClick()&&toggle.isChecked(),"no click listener still toggles but returns false");
        List<String> callbacks=new ArrayList<>();
        toggle.setOnCheckedChangeListener((view,value)->callbacks.add("checked:"+value));
        check(!toggle.performClick()&&!toggle.isChecked(),"checked listener is not a click listener");
        check(callbacks.equals(List.of("checked:false")),"checked listener missing or duplicated");
        toggle.setOnClickListener(view->callbacks.add("click:"+toggle.isChecked()));
        check(toggle.performClick()&&toggle.isChecked(),"assigned click listener returns true");
        check(callbacks.equals(List.of("checked:false","checked:true","click:true")),"click callback must follow checked callback exactly once");
        toggle.setOnClickListener(null);
        check(!toggle.performClick()&&!toggle.isChecked(),"removed click listener returns false while toggling");
        check(callbacks.equals(List.of("checked:false","checked:true","click:true","checked:false")),"checked callback must survive click listener removal");
    }
    static int run() {
        checks=0;
        for(Runnable test:List.<Runnable>of(NativeAndroidFixtureHostTests::snapshots,NativeAndroidFixtureHostTests::replacementCallbacks,
                NativeAndroidFixtureHostTests::editorOutput,NativeAndroidFixtureHostTests::configurationAndLifecycle,
                NativeAndroidFixtureHostTests::accessibilityReplacement,NativeAndroidFixtureHostTests::switchClickContract)) {
            ConcreteHostProbe.reset();try{test.run();}finally{ConcreteHostProbe.reset();}
        }
        return checks;
    }
}
