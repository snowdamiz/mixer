package dev.mixer.android;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

public final class AdditionalFocusAuditControls {
    private AdditionalFocusAuditControls() {}
    private static byte[] descriptor;private static int checks;
    private static void check(boolean yes,String message){checks++;if(!yes)throw new AssertionError(message);}
    private static Object get(Object target,String name){try{Field field=target.getClass().getDeclaredField(name);field.setAccessible(true);return field.get(target);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static void write(StringBuilder out,Object value){if(value instanceof List<?> values){out.append('[');for(int i=0;i<values.size();i++){if(i>0)out.append(',');write(out,values.get(i));}out.append(']');}else if(value instanceof Map<?,?> values){out.append('{');boolean comma=false;for(var item:values.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,item.getKey());out.append(':');write(out,item.getValue());}out.append('}');}else Json.write(out,value);}
    private static Object field(String id,String text){return Json.map("id",id,"kind","textField","properties",Json.map("label",id,"value",text),"children",List.of(),"actions",List.of(Json.map("id",id+"Changed","event","textChange")));}
    private static byte[] packet(long revision,String a,String b,String c){Object root=Json.map("id","root","kind","vStack","properties",Json.map(),"children",List.of(field("a",a),field("b",b),field("c",c)),"actions",List.of());StringBuilder out=new StringBuilder();write(out,Json.map("schemaVersion",new Json.Num("1"),"document",Json.map("schemaVersion",new Json.Num("1"),"revision",new Json.Num(Long.toString(revision)),"root",root),"identities",List.of(Json.map("id","root","generation",new Json.Num("1")),Json.map("id","a","generation",new Json.Num("2")),Json.map("id","b","generation",new Json.Num("3")),Json.map("id","c","generation",new Json.Num("4")))));return out.toString().getBytes(StandardCharsets.UTF_8);}
    private static final class Fixture implements AutoCloseable {
        final NativeOwnerV2 owner;final Handler queue;final NativeRenderer renderer;final NativeAppearanceViewsV2.NativeField a,b,c;final InputConnection oldA,oldC,liveB;final BaseInputConnection targetA,targetC,targetB;
        Fixture(){ConcreteHostProbe.reset();Activity activity=new Activity();FrameLayout root=new FrameLayout(activity);activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);root.hostAttach(new Object());NativeBridge.reset();NativeBridge.preparedPacket=packet(1,"hello","other","third");owner=new NativeOwnerV2(activity,root);queue=(Handler)get(owner,"handler");owner.onResume();owner.start();queue.drainAll(6);check(owner.hasCommittedPresentation(),"three-field publication");renderer=(NativeRenderer)get(get(owner,"coordinator"),"renderer");a=(NativeAppearanceViewsV2.NativeField)renderer.view("a");b=(NativeAppearanceViewsV2.NativeField)renderer.view("b");c=(NativeAppearanceViewsV2.NativeField)renderer.view("c");a.requestFocus();oldA=a.onCreateInputConnection(new EditorInfo());check(oldA!=null,"A connection");targetA=(BaseInputConnection)a.lastConnection;a.clearFocus();c.requestFocus();oldC=c.onCreateInputConnection(new EditorInfo());check(oldC!=null,"C connection");targetC=(BaseInputConnection)c.lastConnection;c.clearFocus();b.requestFocus();liveB=b.onCreateInputConnection(new EditorInfo());check(liveB!=null,"B focused connection");targetB=(BaseInputConnection)b.lastConnection;check(targetA.closeCalls==1&&targetC.closeCalls==1,"two exact predecessors closed");ConcreteHostProbe.reset();}
        NativeOwnerV2.Fence fence(){return (NativeOwnerV2.Fence)get(owner,"fence");}
        @Override public void close(){ConcreteHostProbe.hook=null;try{owner.close();queue.drainAll(8);}catch(RuntimeException|Error expected){/* actual disposition checked before fixture close */}ConcreteHostProbe.reset();}
    }
    private static void multipleWithActiveB(){try(Fixture fixture=new Fixture()){
        Object ea=fixture.a.getText(),ec=fixture.c.getText();NativeAppearanceViewsV2.FieldPreservation[] scopes=new NativeAppearanceViewsV2.FieldPreservation[2];boolean[] hit={false},commit={false};
        ConcreteHostProbe.hook=(method,phase)->{var event=ConcreteHostProbe.lastEvent();if(!hit[0]&&event.receiver==fixture.a&&method.equals("View.invalidate")&&phase.equals("entry")&&fixture.a.record.fieldPreservation!=null){hit[0]=true;scopes[0]=fixture.a.record.fieldPreservation;scopes[1]=fixture.c.record.fieldPreservation;check(scopes[0]!=null&&scopes[1]!=null&&scopes[0]!=scopes[1],"two separate inactive scopes");check(fixture.b.record.editorCallbackLease!=null&&(Integer)get(fixture.renderer,"outstandingEditorNativeCalls")==3,"two inactive counts plus existing B lease");check(scopes[0].candidate==scopes[1].candidate&&scopes[0].original.token==fixture.fence().operation&&scopes[1].original.token==fixture.fence().operation,"same exact candidate original transaction, separate field ownership");int count=(Integer)get(fixture.renderer,"outstandingEditorNativeCalls");int effects=ConcreteHostProbe.events().size();
                try{fixture.a.record.input.fieldPreservationBegin(fixture.a.record,scopes[0]);throw new AssertionError("duplicate begin accepted");}catch(IllegalArgumentException|IllegalStateException expected){check((Integer)get(fixture.renderer,"outstandingEditorNativeCalls")==count,"duplicate begin cannot steal count");}
                try{fixture.a.record.input.fieldPreservationEnd(fixture.c.record,scopes[0]);throw new AssertionError("wrong record end accepted");}catch(IllegalArgumentException|IllegalStateException expected){check((Integer)get(fixture.renderer,"outstandingEditorNativeCalls")==count&&scopes[0].counted&&scopes[1].counted,"wrong record cannot consume another held identity");}
                check(ConcreteHostProbe.events().size()==effects,"scalar custody refusals invoke no native work");fixture.a.drawableStateChanged();fixture.c.onSelectionChanged(fixture.c.getSelectionStart(),fixture.c.getSelectionEnd());
            }
            if(method.equals("NativeBridge.commitV2")&&phase.equals("entry")){commit[0]=true;check(scopes[0].ended&&scopes[1].ended&&!scopes[0].counted&&!scopes[1].counted&&fixture.b.record.editorCallbackLease!=null&&(Integer)get(fixture.renderer,"outstandingEditorNativeCalls")==1,"field release never clears B's active editor count");}
        };
        fixture.liveB.setSelection(5,5);NativeBridge.preparedPacket=packet(2,"hello","otherz","third");check(fixture.liveB.commitText("z",1),"ordinary B transaction with two inactive fields");ConcreteHostProbe.hook=null;check(hit[0]&&commit[0]&&fixture.a.getText()==ea&&fixture.c.getText()==ec&&!fixture.fence().terminal&&(Integer)get(fixture.renderer,"outstandingEditorNativeCalls")==0,"all three exact scopes balance and both native buffers preserved");check(fixture.targetA.closeCalls==1&&fixture.targetC.closeCalls==1&&fixture.targetB.closeCalls==0&&!fixture.oldA.beginBatchEdit()&&!fixture.oldC.beginBatchEdit(),"two old targets stay closed and revoked");
    }}
    private static void eventProvenance(){try(Fixture fixture=new Fixture()){
        NativeAppearanceViewsV2.Replacement[] operation={null};ConcreteHostProbe.hook=(method,phase)->{if(fixture.a.record.replacementCallback!=null)operation[0]=fixture.a.record.replacementCallback;};Bundle args=new Bundle();args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,"updated");NativeBridge.preparedPacket=packet(2,"updated","other","third");check(fixture.a.performAccessibilityAction(AccessibilityNodeInfo.ACTION_SET_TEXT,args),"capture completed ordinary operation");ConcreteHostProbe.hook=null;check(operation[0]!=null&&operation[0].completed&&operation[0].eventClaimed&&!operation[0].eventEvaluating,"completed exact provenance captured");int effects=ConcreteHostProbe.events().size(),events=NativeBridge.prepareCalls;
        try{fixture.b.record.input.replacementEvent(fixture.b.record,operation[0]);throw new AssertionError("wrong record borrowed claim exclusion");}catch(IllegalArgumentException|IllegalStateException expected){check(ConcreteHostProbe.events().size()==effects,"wrong record rejected before getters");}
        NativeAppearanceViewsV2.Replacement fake=new NativeAppearanceViewsV2.Replacement(fixture.b,operation[0].original,fixture.b.getText(),operation[0].lossObservation);fake.eventEvaluating=true;fake.eventClaimed=true;effects=ConcreteHostProbe.events().size();
        try{fixture.b.record.input.replacementEvent(fixture.b.record,fake);throw new AssertionError("uncompleted operation borrowed claimed exclusion");}catch(IllegalArgumentException|IllegalStateException expected){check(ConcreteHostProbe.events().size()==effects,"incomplete provenance rejected before getters");}
        fixture.a.record.input.replacementEvent(fixture.a.record,operation[0]);check(ConcreteHostProbe.events().size()==effects&&NativeBridge.prepareCalls==events&&!fixture.fence().terminal,"only exact completed operation can use clean replay exclusion");
    }}
    public static void main(String[] args)throws Exception{descriptor=Files.readAllBytes(Path.of(args[1]));switch(args[0]){case "multiple-with-active-B"->multipleWithActiveB();case "event-provenance"->eventProvenance();default->throw new IllegalArgumentException(args[0]);}System.out.println("PASS additional focus actual-source "+args[0]+" / "+checks+" assertions");}
}
