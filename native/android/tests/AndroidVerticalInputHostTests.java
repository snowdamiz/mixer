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
public final class AndroidVerticalInputHostTests {
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
        Object button=node("button","button",Json.map("label","Do action"),List.of());
        Object field=node("field","textField",Json.map("label","Entry","value",fieldValue,"axis",reviewAxis),List.of());
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
    private static void acquisition(String axis) {
        reviewAxis=axis;
        try(Fixture f=new Fixture("field")) {
            f.ready(); EditText editor=(EditText)f.renderer().view("field");
            editor.requestFocus();editor.setSelection(editor.getText().length());
            EditorInfo info=new EditorInfo();InputConnection connection=editor.onCreateInputConnection(info);
            System.out.println("ACQUISITION axis="+axis+" inputType="+editor.inputType+" imeOptions="+editor.imeOptions+" connection="+(connection!=null)+" outputScrubbed="+(info.inputType==0)+" targetClosed="+((android.view.inputmethod.BaseInputConnection)editor.lastConnection).closed);
            check(connection!=null,"acquisition must succeed for "+axis);
            if(connection!=null)connection.closeConnection();
        }
        ConcreteHostProbe.reset();
    }
    private static void echo(String suffix,boolean grows) {
        reviewAxis="vertical";
        try(Fixture f=new Fixture("field")) {
            f.ready();EditText editor=(EditText)f.renderer().view("field");editor.requestFocus();editor.setSelection(editor.getText().length());
            int oldHeight=editor.getHeight();int committed=NativeBridge.commitCalls;String next="hello"+suffix;
            NativeBridge.preparedPacket=packet(2,"field",next);
            Throwable escaped=captureFailure(()->editor.hostReplace(editor.getText().length(),editor.getText().length(),suffix));
            Throwable failure=f.owner.cleanupLedger().primary();
            System.out.println("ECHO grows="+grows+" beforeHeight="+oldHeight+" afterHeight="+editor.getHeight()+" nativeText="+editor.getText().toString().replace("\n","<LF>")+" commitsDelta="+(NativeBridge.commitCalls-committed)+" terminal="+f.fence().terminal+" escaped="+escaped+" primary="+failure);
            if(failure!=null)failure.printStackTrace(System.out);
            check(!f.fence().terminal&&NativeBridge.commitCalls==committed+1,"focused echo must commit");check(!grows||editor.getHeight()>oldHeight,"multiline must grow");
        }
        ConcreteHostProbe.reset();
    }

    private static void rejects(Runnable work,String label) {check(captureFailure(work) instanceof IllegalArgumentException,label);}
    private static void packetEdges() {
        reviewAxis="vertical";byte[] bytes=packet(1,"field","é".repeat(8192));
        UiPacket ok=UiPacket.decode(bytes,AndroidUIProfile.MEASURED_MULTILINE_V2);
        check(ok.nodes.get("field").text("value","").getBytes(StandardCharsets.UTF_8).length==16384,"exact UTF8 boundary");
        rejects(()->UiPacket.decode(packet(1,"field","é".repeat(8193)),AndroidUIProfile.MEASURED_MULTILINE_V2),"byte overflow");
        rejects(()->UiPacket.decode(bytes),"legacy vertical decode");
        rejects(()->ok.event("field",ok.nodes.get("field").generation,"submit","unexpected"),"submit payload");
        rejects(()->ok.event("field","999","textChange","x"),"stale generation");
        String raw=new String(packet(1,"field","ok"),StandardCharsets.UTF_8);
        String surrogate=raw.replace("\"ok\"","\""+"\\uD800"+"\"");
        rejects(()->UiPacket.decode(surrogate.getBytes(StandardCharsets.UTF_8),AndroidUIProfile.MEASURED_MULTILINE_V2),"unpaired wire surrogate");
        String disabled=raw.replace("\"properties\":{},","\"properties\":{\"disabled\":true},");
        UiPacket blocked=UiPacket.decode(disabled.getBytes(StandardCharsets.UTF_8),AndroidUIProfile.MEASURED_MULTILINE_V2);
        check(blocked.nodes.get("field").disabled,"ancestor disable propagates");
        rejects(()->blocked.event("field",blocked.nodes.get("field").generation,"textChange","x"),"ancestor disabled event");
        reviewAxis="horizontal";rejects(()->UiPacket.decode(packet(1,"field","ok")),"legacy explicit horizontal decode");
        reviewAxis="diagonal";rejects(()->UiPacket.decode(packet(1,"field","ok"),AndroidUIProfile.MEASURED_MULTILINE_V2),"unknown axis");
        System.out.println("PASS packet boundary checks=10");
    }

    private static void verticalReflow() {
        reviewAxis="vertical";
        try(Fixture f=new Fixture("field")) {
            f.ready();EditText e=(EditText)f.renderer().view("field");e.requestFocus();e.setSelection(e.getText().length());
            InputConnection c=e.onCreateInputConnection(new EditorInfo());check(c!=null,"vertical live connection");
            android.text.Editable buffer=e.getText();Object target=e.lastConnection;View parent=(View)e.getParent();
            int initialHeight=e.getHeight();int initialSibling=f.renderer().view("button").getTop();
            String[] values={"hello\n世界 😀\nthird\nfourth","x".repeat(400),"é😀","hello"};
            long rev=2;
            for(String value:values){
                check(c.finishComposingText(),"finish composition before replacement");check(c.setSelection(0,e.getText().length()),"selection before replacement");
                NativeBridge.preparedPacket=packet(rev++,"field",value);int commits=NativeBridge.commitCalls;
                check(c.commitText(value,1),"vertical commitText accepted");f.queue.drainAll(4);
                check(NativeBridge.commitCalls==commits+1&&!f.fence().terminal,"one committed echo per edit: "+f.owner.cleanupLedger().primary());
                check(e==f.renderer().view("field")&&e.getText()==buffer&&e.lastConnection==target&&e.getParent()==parent&&e.hasFocus(),"retained view buffer connection parent focus");
                check(e.getText().toString().equals(value),"exact Unicode/newline buffer");
                check(f.renderer().view("button").getTop()==initialSibling+e.getHeight()-initialHeight,"sibling tracks height delta");
                if(value.length()>100)check(e.getHeight()>initialHeight,"wrapping grows");
                if(value.equals("hello"))check(e.getHeight()==initialHeight,"shrinks to original height");
                check(c.setComposingRegion(0,Math.min(2,value.length())),"composition region");
                Object[] spans=buffer.getSpans(0,buffer.length(),Object.class);int start=e.getSelectionStart(),end=e.getSelectionEnd();
                NativeBridge.preparedPacket=packet(rev++,"field",value);f.renderer().view("button").performClick();
                check(e.getText()==buffer&&e.getSelectionStart()==start&&e.getSelectionEnd()==end,"selection retained over echo");
                check(java.util.Arrays.equals(spans,buffer.getSpans(0,buffer.length(),Object.class)),"same composition span objects");
            }
            check(c.finishComposingText()&&c.setSelection(0,buffer.length()),"composition replacement selection");
            String composing="مرحبا\n世界 😀\ncomposing";NativeBridge.preparedPacket=packet(rev++,"field",composing);
            check(c.setComposingText(composing,1),"multiline Unicode composing edit");
            check(buffer.toString().equals(composing)&&android.view.inputmethod.BaseInputConnection.getComposingSpanStart(buffer)==0&&android.view.inputmethod.BaseInputConnection.getComposingSpanEnd(buffer)==composing.length(),"exact composing Unicode range");
            Object[] composingSpans=buffer.getSpans(0,buffer.length(),Object.class);int selection=e.getSelectionEnd();
            NativeBridge.preparedPacket=packet(rev++,"field",composing);boolean[] reentry={false};
            ConcreteHostProbe.hook=(method,phase)->{if(!reentry[0]&&method.equals("View.measure")&&phase.equals("entry")&&ConcreteHostProbe.lastEvent().receiver==e){reentry[0]=true;int delegates=ConcreteHostProbe.count("BaseInputConnection.commitText","entry");check(!c.commitText("reentrant",1)&&delegates==ConcreteHostProbe.count("BaseInputConnection.commitText","entry"),"preservation refuses nested IME mutation");}};
            f.renderer().view("button").performClick();ConcreteHostProbe.hook=null;
            check(reentry[0]&&e.getText()==buffer&&e.getSelectionEnd()==selection&&java.util.Arrays.equals(composingSpans,buffer.getSpans(0,buffer.length(),Object.class)),"quiescent live composition preservation");
            c.closeConnection();int calls=ConcreteHostProbe.count("BaseInputConnection.commitText","entry");
            check(!c.commitText("closed",1)&&ConcreteHostProbe.count("BaseInputConnection.commitText","entry")==calls,"closed adapter does not forward");
        }
        ConcreteHostProbe.reset();
    }

    private static void tamperedAcquisition(){
        for(String phase:List.of("EditText.onCreateInputConnection","EditorInfo.setSupportedHandwritingGesturePreviews"))
        for(String property:List.of("type","action","enter")){
            reviewAxis="vertical";
            try(Fixture f=new Fixture("field")){
                f.ready();EditText e=(EditText)f.renderer().view("field");e.requestFocus();EditorInfo info=new EditorInfo();boolean[] hit={false};
                ConcreteHostProbe.hook=(method,when)->{if(!hit[0]&&method.equals(phase)&&when.equals("beforeReturn")){hit[0]=true;
                    if(property.equals("type"))info.inputType=16385;else if(property.equals("action"))info.imeOptions=(info.imeOptions&~EditorInfo.IME_MASK_ACTION)|EditorInfo.IME_ACTION_DONE;else info.imeOptions&=~EditorInfo.IME_FLAG_NO_ENTER_ACTION;}};
                InputConnection c=e.onCreateInputConnection(info);ConcreteHostProbe.hook=null;
                check(hit[0]&&c==null,"tampered "+phase+" / "+property+" refused");
                check(info.inputType==0&&info.initialSelStart==-1&&info.initialSelEnd==-1&&info.hostSurrounding()==null,"refused EditorInfo scrubbed");
                check(((android.view.inputmethod.BaseInputConnection)e.lastConnection).closed,"refused native target closed");
            }finally{ConcreteHostProbe.hook=null;ConcreteHostProbe.reset();}
        }
    }
    private static void refusalAndRollback(){
        for(String mode:List.of("position","disabledSaving","axis","reparent","staleEnvironment","attachRollback","commitRollback","reentrant")){
            reviewAxis="vertical";
            try(Fixture f=new Fixture("field")){
                f.ready();NativeRenderer r=f.renderer();EditText e=(EditText)r.view("field");View sibling=r.view("button");e.requestFocus();
                InputConnection c=e.onCreateInputConnection(new EditorInfo());check(c!=null,"negative fixture connection");
                check(c.setComposingRegion(0,2),"negative fixture composition");check(c.setSelection(1,3),"negative fixture selection");
                var buffer=e.getText();Object[] spans=buffer.getSpans(0,buffer.length(),Object.class);Object oldPacket=r.packet;
                var oldBinding=r.inspectV2().get("field").binding;int height=e.getHeight(),top=sibling.getTop();Object parent=e.getParent();
                String raw=new String(packet(2,"field"),StandardCharsets.UTF_8);
                if(mode.equals("position"))raw=raw.replace("Independent host text","before\\nline\\nline\\nline");
                if(mode.equals("disabledSaving"))raw=raw.replace("\"label\":\"Entry\"","\"label\":\"Entry\",\"disabled\":true");
                if(mode.equals("axis"))raw=raw.replace("\"axis\":\"vertical\"","\"axis\":\"horizontal\"");
                if(mode.equals("reparent"))raw=raw.replace("\"id\":\"reviewRoot\"","\"id\":\"foreignRoot\"");
                NativeBridge.preparedPacket=raw.getBytes(StandardCharsets.UTF_8);int commits=NativeBridge.commitCalls;boolean[] reached={false};
                if(mode.equals("attachRollback"))r.testFaultV2(r.inspectV2().size()*2,false);
                if(mode.equals("commitRollback"))NativeBridge.commitStatus=1;
                if(mode.equals("staleEnvironment")||mode.equals("reentrant"))ConcreteHostProbe.hook=(method,when)->{
                    if(!reached[0]&&method.equals(mode.equals("staleEnvironment")?"NativeBridge.prepareV2":"View.measure")&&when.equals("beforeReturn")){
                        if(mode.equals("reentrant")&&ConcreteHostProbe.lastEvent().receiver!=e)return;
                        reached[0]=true;ConcreteHostProbe.hook=null;
                        if(mode.equals("staleEnvironment"))((NativeEnvironmentV2.Observer)field(f.owner,"observer")).invalidate();else f.owner.close();
                    }};
                Throwable failed=captureFailure(()->r.view("button").performClick());ConcreteHostProbe.hook=null;
                check(f.fence().terminal&&!f.owner.hasCommittedPresentation(),mode+" must fail closed: "+failed);
                check(r.packet==oldPacket&&(mode.equals("reentrant")||r.inspectV2().get("field").binding==oldBinding),mode+" no publication");
                check(e.getText()==buffer&&e.getText().toString().equals("hello")&&e.getSelectionStart()==1&&e.getSelectionEnd()==3,mode+" buffer and selection unchanged");
                check(java.util.Arrays.equals(spans,buffer.getSpans(0,buffer.length(),Object.class)),mode+" spans unchanged");
                check(e.getParent()==parent&&e.getHeight()==height&&sibling.getTop()==top,mode+" geometry/parent restored or untouched");
                if(mode.equals("staleEnvironment")||mode.equals("reentrant"))check(reached[0],mode+" hook reached");
                if(!mode.equals("commitRollback"))check(NativeBridge.commitCalls==commits,mode+" no engine commit");
                int calls=ConcreteHostProbe.count("BaseInputConnection.commitText","entry");check(!c.commitText("late",1)&&ConcreteHostProbe.count("BaseInputConnection.commitText","entry")==calls,mode+" stale adapter fenced");
            }finally{ConcreteHostProbe.hook=null;ConcreteHostProbe.reset();}
        }
    }

    private static void growingRollback(){
        for(boolean commit:List.of(false,true)){
            reviewAxis="vertical";
            try(Fixture f=new Fixture("field")){
                f.ready();NativeRenderer r=f.renderer();EditText e=(EditText)r.view("field");e.requestFocus();
                var buffer=e.getText();Object span=new Object();buffer.setSpan(span,0,2,android.text.Spanned.SPAN_COMPOSING);
                int height=e.getHeight(),sibling=r.view("button").getTop();var binding=r.inspectV2().get("field").binding;Object packet=r.packet;Object parent=e.getParent();
                String next="hello\nsecond\nthird\nfourth";NativeBridge.preparedPacket=packet(2,"field",next);
                if(commit)NativeBridge.commitStatus=1;else r.testFaultV2(r.inspectV2().size()*2,false);
                captureFailure(()->e.hostReplace(5,5,next.substring(5)));
                check(f.fence().terminal&&r.packet==packet&&r.inspectV2().get("field").binding==binding,"growing failed transaction has no publication");
                check(e.getHeight()==height&&r.view("button").getTop()==sibling&&e.getParent()==parent,"growing rollback restores geometry");
                check(e.getText()==buffer&&buffer.toString().equals(next)&&e.getSelectionStart()==next.length()&&e.getSelectionEnd()==next.length(),"rollback retains edited buffer and selection");
                check(buffer.getSpanStart(span)==0&&buffer.getSpanEnd(span)==2&&e.hasFocus(),"rollback retains composition and focus");
            }finally{ConcreteHostProbe.reset();}
        }
    }
    public static void main(String[] args)throws Exception {
        descriptor=Files.readAllBytes(Path.of(args[0]));
        packetEdges();acquisition("horizontal");acquisition("vertical");
        echo("z",false);echo("\nsecond\nthird\nfourth",true);verticalReflow();tamperedAcquisition();refusalAndRollback();growingRollback();
        System.out.println("PASS vertical fix focused checks="+checks+"; controlled leaves only");
    }
}
