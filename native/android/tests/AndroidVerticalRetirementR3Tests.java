package dev.mixer.android;

import android.app.Activity;
import android.graphics.Canvas;
import android.os.Handler;
import android.widget.FrameLayout;
import android.view.View;
import android.view.MotionEvent;
import android.view.KeyEvent;
import android.widget.EditText;
import android.widget.Switch;
import android.view.inputmethod.InputConnection;
import android.view.inputmethod.EditorInfo;
import android.os.Bundle;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Set;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Focused vertical-profile host regression; controlled platform leaves, not Android runtime. */
public final class AndroidVerticalRetirementR3Tests {
    private static byte[] descriptor;
    private static int checks;
    private static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    private static Object field(Object value,String name){try{Field f=value.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(value);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static Map<String,Object> node(String id,String kind,Map<String,Object> props,List<Object> children){
        List<Object> actions=switch(kind){case "button"->List.of(Json.map("id",id+"Action","event","activate"));case "toggle"->List.of(Json.map("id",id+"Change","event","valueChange"));case "textField"->List.of(Json.map("id",id+"Change","event","textChange"),Json.map("id",id+"Submit","event","submit"));default->List.of();};
        return Json.map("id",id,"kind",kind,"properties",props,"children",children,"actions",actions);
    }
    private static void write(StringBuilder out,Object value){if(value instanceof List<?> values){out.append('[');for(int i=0;i<values.size();i++){if(i>0)out.append(',');write(out,values.get(i));}out.append(']');}else if(value instanceof Map<?,?> values){out.append('{');boolean comma=false;for(var e:values.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,e.getKey());out.append(':');write(out,e.getValue());}out.append('}');}else Json.write(out,value);}
    private static void identities(Object raw,List<Object> out){Map<String,Object> n=Json.object(raw);out.add(Json.map("id",n.get("id"),"generation",new Json.Num(Integer.toString(out.size()+1))));for(Object child:Json.array(n.get("children")))identities(child,out);}
    private static byte[] packet(long revision){return packet(revision,"controls");}
    private static byte[] packet(long revision,String scene){return packet(revision,scene,"hello");}
    private static byte[] packet(long revision,String scene,String fieldValue){
        Object text=node("text","text",Json.map("text","Independent host text","style","body"),List.of());
        Object button=node("button","button",Json.map("label","Add"),List.of());
        Object field=node("field","textField",Json.map("label","New task","value",fieldValue,"axis",reviewAxis),List.of());
        Object toggle=node("toggle","toggle",Json.map("label","Enable","value",false),List.of());
        Object h=node("horizontal","hStack",Json.map("alignment","center"),List.of(node("short","text",Json.map("text","Short"),List.of()),node("long","text",Json.map("text","Long text"),List.of())));
        Object z=node("overlay","zStack",Json.map("alignment","bottomTrailing"),List.of(node("back","text",Json.map("text","Back"),List.of()),node("front","text",Json.map("text","Front"),List.of())));
        Object section=node("section","section",Json.map("title","Details"),List.of(text,h,z,button,field,toggle));
        Object root=node("root","vStack",Json.map("alignment","leading"),List.of(section));
        if(scene.equals("navigation")){
            List<Object> rows=new ArrayList<>();rows.add(node("group","section",Json.map("title","Group"),List.of(text,h,z)));
            for(int i=0;i<30;i++)rows.add(node("row"+i,"text",Json.map("text","Scrolling text row "+i),List.of()));
            root=node("nav","navigation",Json.map("title","Navigation"),List.of(node("list","list",Map.of(),rows)));
        } else if(scene.equals("toggles"))root=node("root","vStack",Map.of(),List.of(node("first","toggle",Json.map("label","First","value",false),List.of()),node("middle","toggle",Json.map("label","Middle","value",false),List.of()),node("last","toggle",Json.map("label","Last","value",false),List.of())));
        else if(scene.equals("field"))root=node("reviewRoot","vStack",Map.of(),List.of(text,field,button));
        else if(scene.equals("replace"))root=node("replacement","zStack",Map.of(),List.of(section));
        List<Object> ids=new ArrayList<>();identities(root,ids);
        StringBuilder out=new StringBuilder();write(out,Json.map("schemaVersion",new Json.Num("1"),"document",Json.map("schemaVersion",new Json.Num("1"),"revision",new Json.Num(Long.toString(revision)),"root",root),"identities",ids));return out.toString().getBytes(StandardCharsets.UTF_8);
    }
    private static final class Fixture implements AutoCloseable {
        final Activity activity=new Activity();final FrameLayout root=new FrameLayout(activity);final NativeOwnerV2 owner;
        final Handler queue;
        Fixture(){this("controls");}
        Fixture(String scene){this(scene,null);}
        Fixture(String scene,Runnable completionFault){
            activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);
            root.hostAttach(new Object());NativeBridge.reset();NativeBridge.preparedPacket=packet(1,scene);
            owner=new NativeOwnerV2(activity,root,completionFault);queue=(Handler)field(owner,"handler");owner.onResume();if(owner.cleanupLedger().primary()!=null)throw new AssertionError("fixture resume failed",owner.cleanupLedger().primary());owner.start();
        }
        void ready(){queue.drainAll(4);check(owner.hasCommittedPresentation(),"owner did not publish: "+owner.cleanupLedger().cause()+" / "+owner.cleanupLedger().primary());}
        NativeRenderer renderer(){return (NativeRenderer)field(field(owner,"coordinator"),"renderer");}
        NativeOwnerV2.Fence fence(){return (NativeOwnerV2.Fence)field(owner,"fence");}
        @Override public void close(){owner.close();queue.drainAll(4);}
    }
    private static Throwable captureFailure(Runnable call){try{call.run();return null;}catch(RuntimeException|Error failure){return failure;}}
    private static String reviewAxis="vertical";

    private static byte[] frame(long revision,String value,boolean disabled,boolean removed) {
        Map<String,Object> packet=Json.object(Json.parse(packet(revision,"field",value)));
        Map<String,Object> document=Json.object(packet.get("document"));Map<String,Object> root=Json.object(document.get("root"));
        List<Object> children=new ArrayList<>(Json.array(root.get("children")));
        if(removed){children.remove(1);packet.put("identities",Json.array(packet.get("identities")).stream().filter(x->!Json.object(x).get("id").equals("field")).toList());}
        else {Map<String,Object> field=Json.object(children.get(1));if(disabled)Json.object(field.get("properties")).put("disabled",true);else Json.object(field.get("properties")).remove("disabled");}
        Map<String,Object> button=Json.object(children.get(children.size()-1));
        if(disabled||removed){button.put("actions",List.of(Json.map("id",removed?"reopenModelFrame":"completeModelFrame","event","activate")));Json.object(button.get("properties")).put("label","Model completion driver");Json.object(Json.object(children.get(0)).get("properties")).put("text",removed?"Saved: "+value:"Saving…");}
        root.put("children",children);StringBuilder out=new StringBuilder();write(out,packet);return out.toString().getBytes(StandardCharsets.UTF_8);
    }
    private static void publish(Fixture f,byte[] next){NativeBridge.preparedPacket=next;f.renderer().view("button").performClick();f.queue.drainAll(4);}
    private static void live(Fixture f,String message){check(!f.fence().terminal&&f.owner.hasCommittedPresentation(),message+": "+f.owner.cleanupLedger().primary());}
    private static void inactive(){
        for(String mode:List.of("value","disable","remove"))try(Fixture f=new Fixture("field")){
            f.ready();int commits=NativeBridge.commitCalls;EditText e=(EditText)f.renderer().view("field");
            publish(f,frame(2,mode.equals("value")?"new\n世界 😀":"hello",mode.equals("disable"),mode.equals("remove")));
            live(f,"inactive "+mode);check(NativeBridge.commitCalls==commits+1&&NativeBridge.createCalls==1,"inactive commits once without reset");
            if(mode.equals("remove"))check(!f.renderer().inspectV2().containsKey("field"),"inactive removal");
            else {check(e==f.renderer().view("field"),"same field identity");check(e.isEnabled()!=mode.equals("disable"),"disabled binding");check(e.getText().toString().equals(mode.equals("value")?"new\n世界 😀":"hello"),"new model text");}
            check(ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==0,"no nonexistent editor close");
            System.out.println("PASS inactive "+mode);
        }finally{ConcreteHostProbe.reset();}
    }
    private static void saving(){
        try(Fixture f=new Fixture("field")){
            f.ready();NativeRenderer r=f.renderer();EditText e=(EditText)r.view("field");e.requestFocus();e.setSelection(0,5);
            InputConnection c=e.onCreateInputConnection(new EditorInfo());check(c!=null,"new profile acquisition");
            String draft="New task\n世界 😀 مرحبا";NativeBridge.preparedPacket=frame(2,draft,false,false);
            check(c.setComposingText(draft,1),"multiline composing draft");live(f,"composing echo");
            var buffer=e.getText();check(android.view.inputmethod.BaseInputConnection.getComposingSpanStart(buffer)>=0,"composition present");
            int prepares=NativeBridge.prepareCalls,commits=NativeBridge.commitCalls;
            publish(f,frame(3,draft,true,false));live(f,"Add to Saving");
            check(NativeBridge.prepareCalls==prepares+1&&NativeBridge.commitCalls==commits+1,"one Add prepare and commit");
            check(((Json.Num)Json.object(Json.parse(NativeBridge.lastInput)).get("revision")).raw.equals("2"),"original Add envelope consumed");
            check(e==r.view("field")&&e.getText()==buffer&&buffer.toString().equals(draft)&&!e.isEnabled()&&!e.hasFocus(),"Saving keeps exact field/draft and retires focus");
            check(ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==1,"one exact close");
            int delegates=ConcreteHostProbe.count("BaseInputConnection.commitText","entry");check(!c.commitText("late",1)&&delegates==ConcreteHostProbe.count("BaseInputConnection.commitText","entry"),"late adapter refuses without forwarding");
            // Model completion is an independently supplied committed frame; this is not disk or JNI-executor evidence.
            publish(f,frame(4,draft,true,true));live(f,"completion list frame");check(((Json.Num)Json.object(Json.parse(NativeBridge.lastInput)).get("revision")).raw.equals("3"),"completion does not replay Add");check(!r.inspectV2().containsKey("field"),"list removes field");
            publish(f,frame(5,draft,false,false));live(f,"reopen frame");
            EditText reopened=(EditText)r.view("field");reopened.requestFocus();reopened.setSelection(draft.length());
            InputConnection fresh=reopened.onCreateInputConnection(new EditorInfo());check(fresh!=null&&fresh!=c,"reopened fresh editor");
            check(reopened.getText().toString().equals(draft)&&NativeBridge.createCalls==1&&NativeBridge.destroyCalls==0,"saved model draft and owner survive");
            check(!c.commitText("later",1),"no resurrection after reopen");
            check(ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==1,"no duplicate old close");
            System.out.println("PASS composing Add Saving modeled-completion list reopen; one owner and one retired target");
        }finally{ConcreteHostProbe.reset();}
    }
    private static void disableAndReenable(){
        for(boolean removal:List.of(false,true))try(Fixture f=new Fixture("field")){
            f.ready();EditText e=(EditText)f.renderer().view("field");e.requestFocus();InputConnection old=e.onCreateInputConnection(new EditorInfo());
            check(old!=null&&old.setComposingRegion(0,2),"async fixture composing");
            publish(f,frame(2,"hello",!removal,removal));live(f,"independent model disable/removal");
            check(!old.commitText("late",1),"async retired adapter");
            publish(f,frame(3,"model value",false,false));live(f,"independent enabled snapshot");
            EditText next=(EditText)f.renderer().view("field");if(!removal)check(next==e,"reenable exact record");next.requestFocus();next.setSelection(next.getText().length());
            check(next.onCreateInputConnection(new EditorInfo())!=null,"enabled frame can create fresh attempt");
            System.out.println("PASS independent snapshot retirement removal="+removal);
        }finally{ConcreteHostProbe.reset();}
    }
    private static void rollback(){
        for(String mode:List.of("preparation","attachment","commit","enabledValue"))try(Fixture f=new Fixture("field")){
            f.ready();NativeRenderer r=f.renderer();EditText e=(EditText)r.view("field");e.requestFocus();InputConnection c=e.onCreateInputConnection(new EditorInfo());check(c!=null,"rollback connection");
            check(c.setComposingRegion(0,2)&&c.setSelection(1,3),"rollback composition/selection");var buffer=e.getText();Object[] spans=buffer.getSpans(0,buffer.length(),Object.class);Object binding=r.inspectV2().get("field").binding;Object packet=r.packet;
            if(mode.equals("preparation"))NativeBridge.prepareFailure=new IllegalStateException("injected preparation failure");
            if(mode.equals("attachment"))r.testFaultV2(r.inspectV2().size()*2,false);
            if(mode.equals("commit"))NativeBridge.commitStatus=1;
            publish(f,frame(2,mode.equals("enabledValue")?"external value":"hello",!mode.equals("enabledValue"),false));
            check(f.fence().terminal&&!f.owner.hasCommittedPresentation(),"failure stays gated "+mode);
            check(r.packet==packet&&r.inspectV2().get("field").binding==binding,"no failed publication "+mode);
            check(e.getText().toString().equals("hello")&&e.getSelectionStart()==1&&e.getSelectionEnd()==3,"visible draft rollback "+mode);
            check(java.util.Arrays.equals(spans,e.getText().getSpans(0,e.getText().length(),Object.class)),"composition span identity rollback "+mode);
            if(mode.equals("attachment")||mode.equals("commit"))check(r.gatedNativeInstallFailureV3(),"post-close failure classified "+mode);
            check(!c.commitText("late",1),"failed operation cannot resurrect adapter "+mode);
            System.out.println("PASS rollback "+mode+" close="+ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")+" installFailure="+r.gatedNativeInstallFailureV3());
        }finally{ConcreteHostProbe.reset();}
    }
    private static void quiescentFaults(){
        for(String mode:List.of("close","span","selection","nested","foreign"))for(String phase:List.of("entry","beforeReturn")){
            reviewAxis="vertical";
            try(Fixture f=new Fixture("field")){
                f.ready();NativeRenderer r=f.renderer();EditText e=(EditText)r.view("field");e.requestFocus();
                InputConnection c=e.onCreateInputConnection(new EditorInfo());check(c!=null,"probe acquisition");
                check(c.setComposingRegion(0,2)&&c.setSelection(1,3),"probe composition");
                var buffer=e.getText();Object[] spans=buffer.getSpans(0,buffer.length(),Object.class);int commits=NativeBridge.commitCalls;
                Object packet=r.packet;var record=r.inspectV2().get("field");boolean[] hit={false};
                NativeBridge.preparedPacket=packet(2,"field");
                ConcreteHostProbe.hook=(method,when)->{
                    if(hit[0]||!method.equals("View.measure")||!when.equals(phase)||ConcreteHostProbe.lastEvent().receiver!=e||record.fieldPreservation==null)return;
                    hit[0]=true;ConcreteHostProbe.hook=null;
                    if(mode.equals("close"))c.closeConnection();
                    if(mode.equals("span"))buffer.setSpan(new Object(),1,3,android.text.Spanned.SPAN_COMPOSING);
                    if(mode.equals("selection"))e.setSelection(0,0);
                    if(mode.equals("nested")){
                        int calls=ConcreteHostProbe.count("BaseInputConnection.commitText","entry");
                        check(!c.commitText("bad",1)&&ConcreteHostProbe.count("BaseInputConnection.commitText","entry")==calls,"nested dispatch refused");
                        check(e.onCreateInputConnection(new EditorInfo())==null,"nested creator refused");
                    }
                    if(mode.equals("foreign")){
                        var hold=record.fieldPreservation;
                        check(!r.fieldPreservationCurrent(hold.candidate,hold.journal,r.inspectV2().get("button"),hold),"wrong record rejected");
                        check(!r.fieldPreservationCurrent(hold.candidate,null,record,hold),"wrong journal rejected");
                    }
                };
                Throwable escaped=captureFailure(()->r.view("button").performClick());ConcreteHostProbe.hook=null;
                check(hit[0],"preservation hook reached "+mode+phase);
                boolean safe=mode.equals("nested")||mode.equals("foreign");
                if(safe){check(!f.fence().terminal&&NativeBridge.commitCalls==commits+1,"safe refusals preserve transaction");check(e.getText()==buffer&&java.util.Arrays.equals(spans,buffer.getSpans(0,buffer.length(),Object.class))&&e.getSelectionStart()==1&&e.getSelectionEnd()==3,"preservation identity");}
                else {check(f.fence().terminal&&NativeBridge.commitCalls==commits&&r.packet==packet,"mutated preservation fails closed "+mode+" "+escaped);int calls=ConcreteHostProbe.count("BaseInputConnection.commitText","entry");check(!c.commitText("late",1)&&calls==ConcreteHostProbe.count("BaseInputConnection.commitText","entry"),"old connection fenced");}
                System.out.println("REVIEW preservation "+mode+" "+phase+" terminal="+f.fence().terminal);
            }finally{ConcreteHostProbe.hook=null;ConcreteHostProbe.reset();}
        }
    }
    private static void retirementFaults(){
        for(String mode:List.of("nested","foreign","windowLoss","closeFailure"))try(Fixture f=new Fixture("field")){
            f.ready();NativeRenderer r=f.renderer();EditText e=(EditText)r.view("field");e.requestFocus();InputConnection c=e.onCreateInputConnection(new EditorInfo());check(c!=null&&c.setComposingRegion(0,2),"retirement fault composition");
            int commits=NativeBridge.commitCalls;boolean[] hit={false};
            ConcreteHostProbe.hook=(method,phase)->{
                if(hit[0]||!method.equals(mode.equals("closeFailure")?"BaseInputConnection.closeConnection":"BaseInputConnection.finishComposingText")||!phase.equals("beforeReturn"))return;
                hit[0]=true;ConcreteHostProbe.hook=null;
                if(mode.equals("nested")){int before=ConcreteHostProbe.count("BaseInputConnection.commitText","entry");check(!c.commitText("late",1)&&before==ConcreteHostProbe.count("BaseInputConnection.commitText","entry"),"retirement denies reentrant IME");check(e.onCreateInputConnection(new EditorInfo())==null,"retirement denies creator");}
                if(mode.equals("foreign")){var s=r.inspectV2().get("field").fieldTransition;check(!r.fieldTransitionCurrent(s.candidate,null,s.record,s),"foreign journal refused");check(!r.fieldTransitionCurrent(s.candidate,s.journal,r.inspectV2().get("button"),s),"foreign record refused");}
                if(mode.equals("windowLoss"))e.onWindowFocusChanged(false);
                if(mode.equals("closeFailure"))throw new IllegalStateException("injected close return failure");
            };
            publish(f,frame(2,"hello",true,false));ConcreteHostProbe.hook=null;check(hit[0],"retirement fault reached "+mode);
            if(mode.equals("nested")||mode.equals("foreign")){live(f,"safe retirement refusal "+mode);check(NativeBridge.commitCalls==commits+1,"one safe retirement commit");}
            else{check(f.fence().terminal&&NativeBridge.commitCalls==commits,"uncertain native installation remains gated");check(r.gatedNativeInstallFailureV3(),"uncertain close is classified");}
            check(!c.commitText("later",1),"faulted old adapter cannot resurrect");System.out.println("PASS retirement fault "+mode);
        }finally{ConcreteHostProbe.hook=null;ConcreteHostProbe.reset();}
    }
    public static void main(String[] args)throws Exception {
        descriptor=Files.readAllBytes(Path.of(args[0]));NativeBridge.testProfile=AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3;
        int failures=0;for(Runnable part:List.<Runnable>of(AndroidVerticalRetirementR3Tests::inactive,AndroidVerticalRetirementR3Tests::saving,AndroidVerticalRetirementR3Tests::disableAndReenable,AndroidVerticalRetirementR3Tests::rollback,AndroidVerticalRetirementR3Tests::quiescentFaults,AndroidVerticalRetirementR3Tests::retirementFaults)){try{part.run();}catch(RuntimeException|Error failure){failures++;failure.printStackTrace(System.out);}}
        check(failures==0,"R3 failing sections="+failures);
        System.out.println("PASS R3 frame retirement checks="+checks+"; controlled native/JNI leaves; completion is modeled");
    }
}
