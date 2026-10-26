package dev.mixer.android;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.Annotation;
import android.text.Editable;
import android.view.KeyEvent;
import android.view.View;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.HandwritingGesture;
import android.view.inputmethod.InputConnection;
import android.view.inputmethod.PreviewableHandwritingGesture;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Preaccess authored controls. Compile only until root releases the exact correction seal. */
public final class ReplacementReviewControls {
    private ReplacementReviewControls() {}
    private static byte[] descriptor;
    // Pinned SDK37 Spanned.SPAN_INCLUSIVE_INCLUSIVE=18; baseline host omitted this field.
    private static final int ANNOTATION_FLAGS=18;
    private static void check(boolean yes,String message){if(!yes)throw new AssertionError(message);}
    private static Object get(Object object,String name){try{Field f=object.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(object);}catch(ReflectiveOperationException e){throw new AssertionError(e);}}
    private static void write(StringBuilder out,Object value){
        if(value instanceof List<?> values){out.append('[');for(int i=0;i<values.size();i++){if(i>0)out.append(',');write(out,values.get(i));}out.append(']');}
        else if(value instanceof Map<?,?> values){out.append('{');boolean comma=false;for(var entry:values.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,entry.getKey());out.append(':');write(out,entry.getValue());}out.append('}');}
        else Json.write(out,value);
    }
    private static Object node(String id,String value){return Json.map("id",id,"kind","textField","properties",Json.map("label",id,"value",value),"children",List.of(),"actions",List.of(Json.map("id",id+"Changed","event","textChange")));}
    private static byte[] packet(long revision,String a,String b){
        Object root=Json.map("id","root","kind","vStack","properties",Json.map(),"children",List.of(node("a",a),node("b",b)),"actions",List.of());
        StringBuilder out=new StringBuilder();write(out,Json.map("schemaVersion",new Json.Num("1"),"document",Json.map("schemaVersion",new Json.Num("1"),"revision",new Json.Num(Long.toString(revision)),"root",root),"identities",List.of(Json.map("id","root","generation",new Json.Num("1")),Json.map("id","a","generation",new Json.Num("2")),Json.map("id","b","generation",new Json.Num("3")))));return out.toString().getBytes(StandardCharsets.UTF_8);
    }
    private static final class Fixture implements AutoCloseable {
        final NativeOwnerV2 owner;final Handler queue;final NativeRenderer renderer;
        final NativeAppearanceViewsV2.NativeField a,b;
        Fixture(){
            ConcreteHostProbe.reset();Activity activity=new Activity();FrameLayout root=new FrameLayout(activity);
            activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);root.hostAttach(new Object());NativeBridge.reset();NativeBridge.preparedPacket=packet(1,"hello","other");
            owner=new NativeOwnerV2(activity,root);queue=(Handler)get(owner,"handler");owner.onResume();owner.start();queue.drainAll(6);check(owner.hasCommittedPresentation(),"two-field fixture publication: "+owner.cleanupLedger().primary());
            renderer=(NativeRenderer)get(get(owner,"coordinator"),"renderer");a=(NativeAppearanceViewsV2.NativeField)renderer.view("a");b=(NativeAppearanceViewsV2.NativeField)renderer.view("b");ConcreteHostProbe.reset();
        }
        NativeOwnerV2.Fence fence(){return (NativeOwnerV2.Fence)get(owner,"fence");}
        InputConnection connect(NativeAppearanceViewsV2.NativeField field){field.requestFocus();InputConnection c=field.onCreateInputConnection(new EditorInfo());check(c!=null,"ordinary connection");return c;}
        BaseInputConnection target(NativeAppearanceViewsV2.NativeField field){return (BaseInputConnection)field.lastConnection;}
        @Override public void close(){ConcreteHostProbe.hook=null;try{owner.close();queue.drainAll(8);}catch(RuntimeException|Error expected){/* every case checks its actual disposition before fixture cleanup */}ConcreteHostProbe.reset();}
    }
    private static Bundle arguments(CharSequence value){Bundle b=new Bundle();b.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,value);return b;}
    private static boolean setText(NativeAppearanceViewsV2.NativeField field,Bundle args){return field.performAccessibilityAction(AccessibilityNodeInfo.ACTION_SET_TEXT,args);}
    private static final class HostileInfo extends EditorInfo {
        int effects;
        HostileInfo(){inputType=123;hintText="unchanged caller output";}
        @Override public void setInitialSurroundingText(CharSequence text){effects++;throw new AssertionError("subclass surrounding setter touched");}
        @Override public void setSupportedHandwritingGestures(List<Class<? extends HandwritingGesture>> value){effects++;throw new AssertionError("subclass gesture setter touched");}
        @Override public void setSupportedHandwritingGesturePreviews(Set<Class<? extends PreviewableHandwritingGesture>> value){effects++;throw new AssertionError("subclass preview setter touched");}
        // Signatures are public SDK methods; baseline authored leaf omitted these getters.
        public CharSequence getInitialTextBeforeCursor(int count,int flags){effects++;throw new AssertionError("subclass surrounding getter touched");}
        public List<Class<? extends HandwritingGesture>> getSupportedHandwritingGestures(){effects++;throw new AssertionError("subclass gesture getter touched");}
        public Set<Class<? extends PreviewableHandwritingGesture>> getSupportedHandwritingGesturePreviews(){effects++;throw new AssertionError("subclass preview getter touched");}
    }
    private static void admissionOrder(){try(Fixture f=new Fixture()){
        InputConnection current=f.connect(f.a);BaseInputConnection old=f.target(f.a);Object editable=f.a.getText();
        for(boolean nullOutput:new boolean[]{true,false}){
            HostileInfo info=nullOutput?null:new HostileInfo();int before=ConcreteHostProbe.events().size(),creators=f.a.connectionAcquisitions;
            check(f.a.onCreateInputConnection(info)==null,"null/subclass clean refusal");
            check(ConcreteHostProbe.events().size()==before,"admission refusal reached native/live getter or output method");
            check(f.a.connectionAcquisitions==creators&&old.closeCalls==0,"admission refusal revoked healthy predecessor or called creator");
            if(info!=null)check(info.effects==0&&info.inputType==123&&"unchanged caller output".contentEquals(info.hintText),"caller subclass/output changed");
            check(f.a.getText()==editable&&!f.fence().terminal&&current.setSelection(0,0),"healthy connection survives refusal");
        }
        HostileInfo offmain=new HostileInfo();int before=ConcreteHostProbe.events().size();Looper.hostSetMain(false);
        try{f.a.onCreateInputConnection(offmain);throw new AssertionError("offmain creator allowed");}catch(IllegalStateException expected){check(true,"main first");}finally{Looper.hostReset();}
        check(before==ConcreteHostProbe.events().size()&&offmain.effects==0,"offmain refusal effects");
    }}
    private static void positiveValues(){for(int previous:new int[]{0,1,2})for(String value:new String[]{"updated","hello",""})try(Fixture f=new Fixture()){
        InputConnection old=previous==0?null:f.connect(f.a);BaseInputConnection target=previous==0?null:f.target(f.a);if(previous==2)old.closeConnection();Object eold=f.a.getText();
        int prepares=NativeBridge.prepareCalls,commits=NativeBridge.commitCalls;boolean[] setter={false};
        ConcreteHostProbe.hook=(method,phase)->{var event=ConcreteHostProbe.lastEvent();if(!setter[0]&&event.receiver==f.a&&method.equals("TextView.setText")&&phase.equals("entry")){setter[0]=true;check(f.renderer.editorDisposalBusyV2(),"setter lacks counted replacement custody");if(target!=null)check(target.closeCalls==1,"old target not closed before native setter");check(f.a.onCreateInputConnection(new EditorInfo())==null,"creation inside replacement");}};
        NativeBridge.preparedPacket=packet(2,value,"other");check(setText(f.a,arguments(value)),"ordinary SET_TEXT including same/empty");ConcreteHostProbe.hook=null;
        check(setter[0]&&f.a.getText()!=eold&&f.a.getText().toString().equals(value),"native setter/one new buffer/value");
        check(f.a.getSelectionStart()==value.length()&&f.a.getSelectionEnd()==value.length(),"pinned movement/nonempty-end selection");
        check(NativeBridge.prepareCalls==prepares+1&&NativeBridge.commitCalls==commits+1,"exactly one synchronous textChange transaction");
        check(!f.renderer.editorDisposalBusyV2()&&!f.fence().terminal,"healthy replacement custody clears");
        if(old!=null){check(!old.setSelection(0,0)&&target.closeCalls==1,"old adapter revived or closed twice");}
        f.a.requestFocus();InputConnection fresh=f.a.onCreateInputConnection(new EditorInfo());check(fresh!=null&&fresh.setSelection(0,0),"fresh later connection on Enew");
    }}
    private static void foreignDispatch(){try(Fixture f=new Fixture()){
        // Source-faithful eligibility: A is unfocused; B alone has the healthy focused connection.
        InputConnection foreign=f.connect(f.b);BaseInputConnection old=f.target(f.b);Object editable=f.b.getText();
        boolean[] fired={false};Bundle second=arguments("foreign");
        ConcreteHostProbe.hook=(method,phase)->{var event=ConcreteHostProbe.lastEvent();if(!fired[0]&&event.receiver==f.a&&method.equals("TextView.setText")&&phase.equals("entry")){
            fired[0]=true;EditorInfo untouched=new EditorInfo();untouched.inputType=456;KeyEvent key=new KeyEvent(KeyEvent.ACTION_DOWN,0);int before=ConcreteHostProbe.events().size();
            check(!foreign.beginBatchEdit()&&foreign.getSelectedText(0)==null,"foreign adapter new entry while replacement reserved");
            check(f.b.onCreateInputConnection(untouched)==null&&untouched.inputType==456,"foreign creator touched output");
            check(!f.b.onKeyDown(0,key),"foreign key entry");
            check(!f.b.onTextContextMenuItem(0)&&!setText(f.b,second),"foreign menu/second replacement");
            check(foreign.getHandler()==null,"constant handler exception");
            check(ConcreteHostProbe.events().size()==before,"foreign refusal performed native getter/effect");
            check(old.closeCalls==0&&!f.fence().terminal,"foreign clean refusal retired healthy field");
        }};
        NativeBridge.preparedPacket=packet(2,"A changed","other");check(setText(f.a,arguments("A changed")),"unfocused ordinary accessibility replacement");ConcreteHostProbe.hook=null;
        check(fired[0]&&!f.a.hasFocus()&&f.b.getText()==editable&&old.closeCalls==0,"cross-field focus/buffer continuity");
        check(foreign.beginBatchEdit()&&foreign.endBatchEdit(),"foreign adapter not usable after guard release");
    }}
    private static void selectionAndPostEvent(){try(Fixture f=new Fixture()){
        f.a.requestFocus();boolean[] setter={false},setterReturned={false},early={false},late={false},event={false};Object[] enew={null};int[] forbidden={0};
        ConcreteHostProbe.hook=(method,phase)->{var hit=ConcreteHostProbe.lastEvent();
            if(method.equals("NativeBridge.prepareV2")&&phase.equals("entry")){event[0]=true;check(!f.renderer.editorDisposalBusyV2(),"feature event still owns replacement-native busy");}
            if(event[0]&&hit.receiver==f.a&&!hit.productionFrames.stream().anyMatch(frame->frame.className().equals("dev.mixer.android.NativeOwnerV2")&&frame.methodName().equals("nativeInput")))forbidden[0]++;
            if(hit.receiver==f.a&&method.equals("TextView.setText")){if(phase.equals("entry"))setter[0]=true;else if(phase.equals("beforeReturn"))setterReturned[0]=true;}
            if(hit.receiver==f.a&&method.equals("TextView.onSelectionChanged")&&phase.equals("entry")&&setter[0]){Object value=f.a.getText();if(enew[0]==null)enew[0]=value;check(enew[0]==value,"more than one observed Enew");if(setterReturned[0])late[0]=true;else early[0]=true;}
        };
        NativeBridge.preparedPacket=packet(2,"selection","other");check(setText(f.a,arguments("selection")),"selection path");ConcreteHostProbe.hook=null;
        check(early[0]&&late[0]&&event[0],"movement-before-watcher and action selection-after-setter not exercised");
        check(forbidden[0]==0,"native A work after feature dispatch outside its new synchronous owner transaction");
    }}
    private static void annotationsAndMutableBundle(){try(Fixture f=new Fixture()){
        f.a.requestFocus();Editable proposal=new Editable("annotated");Annotation annotation=new Annotation("review","kept");proposal.setSpan(annotation,1,5,ANNOTATION_FLAGS);
        Bundle original=arguments(proposal);boolean[] changed={false};
        ConcreteHostProbe.hook=(method,phase)->{var event=ConcreteHostProbe.lastEvent();if(!changed[0]&&event.receiver==f.a&&method.equals("TextView.performAccessibilityAction")&&phase.equals("entry")){changed[0]=true;original.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,"other payload");proposal.replace(0,proposal.length(),"mutated");}};
        NativeBridge.preparedPacket=packet(2,"annotated","other");check(setText(f.a,original),"stable owned replacement payload");ConcreteHostProbe.hook=null;
        check(changed[0]&&f.a.getText().toString().equals("annotated"),"validated one payload but passed mutable original");
        Annotation[] kept=f.a.getText().getSpans(0,f.a.getText().length(),Annotation.class);check(kept.length==1,"Annotation admission dropped");
        check(kept[0].getKey().equals("review")&&kept[0].getValue().equals("kept")&&f.a.getText().getSpanStart(kept[0])==1&&f.a.getText().getSpanEnd(kept[0])==5&&f.a.getText().getSpanFlags(kept[0])==ANNOTATION_FLAGS,"Annotation snapshot semantics changed");
    }}
    private static void snapshotReservation(){try(Fixture f=new Fixture()){
        InputConnection foreign=f.connect(f.b);BaseInputConnection old=f.target(f.b);boolean[] fired={false};
        Runnable reenter=()->{if(!fired[0]){fired[0]=true;int before=ConcreteHostProbe.events().size();
            check(!foreign.beginBatchEdit(),"payload evaluation preceded renderer-wide reservation");
            check(f.a.onCreateInputConnection(new EditorInfo())==null,"payload callback admitted creator");
            check(!setText(f.a,arguments("nested")),"payload callback admitted nested replacement");
            check(ConcreteHostProbe.events().size()==before&&old.closeCalls==0&&!f.fence().terminal,"snapshot callback refusal had native/retirement effects");
        }};
        CharSequence opaque=new CharSequence(){public int length(){reenter.run();return 7;}public char charAt(int index){reenter.run();return "capture".charAt(index);}public CharSequence subSequence(int start,int end){reenter.run();return "capture".subSequence(start,end);}@Override public String toString(){reenter.run();return "capture";}};
        NativeBridge.preparedPacket=packet(2,"capture","other");check(setText(f.a,arguments(opaque)),"snapshot reservation replacement");
        check(fired[0]&&f.a.getText().toString().equals("capture")&&old.closeCalls==0&&foreign.beginBatchEdit(),"reservation not released or payload changed");check(foreign.endBatchEdit(),"foreign batch balance");
    }}
    public static void main(String[] args) throws Exception {
        descriptor=Files.readAllBytes(Path.of(args[1]));
        switch(args[0]){case "admission-order"->admissionOrder();case "positive-values"->positiveValues();case "foreign-dispatch"->foreignDispatch();case "selection-postevent"->selectionAndPostEvent();case "annotation-mutable-bundle"->annotationsAndMutableBundle();case "snapshot-reservation"->snapshotReservation();default->throw new IllegalArgumentException(args[0]);}
        System.out.println("PASS independent replacement actual-source control "+args[0]);
    }
}
