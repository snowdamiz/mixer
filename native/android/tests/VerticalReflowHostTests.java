package dev.mixer.android;

import android.app.Activity;
import android.os.Handler;
import android.text.Editable;
import android.view.View;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.EditText;
import android.widget.FrameLayout;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Focused actual-renderer controls; Android and JNI remain controlled host leaves. */
public final class VerticalReflowHostTests {
    private static byte[] descriptor;
    private static int checks, cases;
    private static void check(boolean ok,String message){checks++;if(!ok)throw new AssertionError(message);}
    private static Object get(Object target,String name)throws Exception{Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(target);}
    private static void write(StringBuilder out,Object value){
        if(value instanceof List<?> list){out.append('[');for(int i=0;i<list.size();i++){if(i>0)out.append(',');write(out,list.get(i));}out.append(']');}
        else if(value instanceof Map<?,?> map){out.append('{');boolean comma=false;for(var entry:map.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,entry.getKey());out.append(':');write(out,entry.getValue());}out.append('}');}
        else Json.write(out,value);
    }
    private static Object node(String id,String kind,Map<String,Object> properties,List<Object> children){
        return Json.map("id",id,"kind",kind,"properties",properties,"children",children,"actions",kind.equals("textField")?List.of(Json.map("id","change","event","textChange")):List.of());
    }
    private static byte[] packet(long revision,boolean vertical,String value,String header,String change){
        Map<String,Object> properties=Json.map("label",change.equals("binding")?"Other label":"Entry","value",value);
        if(vertical)properties.put("axis","vertical");
        Object field=node("field","textField",properties,List.of());
        Object text=node("header","text",Json.map("text",header),List.of());
        Object extra=node("extra","text",Json.map("text","Tail"),List.of());
        List<Object> children=change.equals("order")?List.of(extra,field,text):List.of(text,field,extra);
        if(change.equals("ancestor"))children=List.of(text,node("nested","vStack",Map.of(),List.of(field)),extra);
        Object root=node("root","vStack",Json.map("alignment","leading"),children);
        List<Object> identities=new ArrayList<>();
        for(var entry:Map.of("root",1,"header",2,"field",3,"extra",4).entrySet())identities.add(Json.map("id",entry.getKey(),"generation",new Json.Num(entry.getValue().toString())));
        if(change.equals("ancestor"))identities.add(Json.map("id","nested","generation",new Json.Num("5")));
        StringBuilder out=new StringBuilder();write(out,Json.map("schemaVersion",new Json.Num("1"),"document",Json.map("schemaVersion",new Json.Num("1"),"revision",new Json.Num(Long.toString(revision)),"root",root),"identities",identities));
        return out.toString().getBytes(StandardCharsets.UTF_8);
    }
    private static final class Fixture implements AutoCloseable {
        final Activity activity=new Activity();final FrameLayout root=new FrameLayout(activity);
        final NativeOwnerV2 owner;final Handler queue;final List<byte[]> events=new ArrayList<>();
        final NativeRenderer renderer;final EditText edit;
        Fixture(AndroidUIProfile profile,boolean vertical,String value,String header,String change,boolean external)throws Exception{
            ConcreteHostProbe.reset();NativeBridge.reset();activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);
            root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);root.hostAttach(new Object());
            byte[] bytes=packet(1,vertical,value,header,change);
            if(external){owner=NativeOwnerV2.external(activity,root,new ExternalFrameSourceV2(events::add));queue=(Handler)get(owner,"handler");owner.installExternal(bytes,descriptor);}
            else {NativeBridge.preparedPacket=bytes;owner=NativeOwnerV2.forProfile(activity,root,profile);queue=(Handler)get(owner,"handler");owner.onResume();owner.start();queue.drainAll(8);}
            check(owner.hasCommittedPresentation(),"initial owner: "+owner.diagnostic());
            renderer=(NativeRenderer)get(get(owner,"coordinator"),"renderer");edit=(EditText)renderer.view("field");
            ConcreteHostProbe.reset();
        }
        @Override public void close(){ConcreteHostProbe.hook=null;owner.close();queue.drainAll(8);ConcreteHostProbe.reset();}
    }
    private static NativeRenderer.Candidate candidate(Fixture base,Fixture shadow,boolean replaceTarget,boolean foreignOwner)throws Exception{
        Map<String,NativeAppearanceViewsV2.Record> targets=new LinkedHashMap<>(base.renderer.inspectV2());
        if(replaceTarget)targets.put("field",shadow.renderer.inspectV2().get("field"));
        Constructor<?> ctor=NativeRenderer.Candidate.class.getDeclaredConstructors()[0];ctor.setAccessible(true);
        return (NativeRenderer.Candidate)ctor.newInstance(foreignOwner?shadow.renderer:base.renderer,shadow.renderer.packet,new byte[0],targets,shadow.renderer.inspectV2(),get(shadow.renderer,"v2Plan"),get(base.renderer,"v2Installed"),get(base.renderer,"v2CommittedEnvironment"),get(base.renderer,"v2Gate"));
    }
    private static Throwable preflight(Fixture base,NativeRenderer.Candidate candidate)throws Exception{
        Method m=NativeRenderer.class.getDeclaredMethod("preflightEditorsV2",NativeRenderer.Candidate.class);m.setAccessible(true);
        try{m.invoke(base.renderer,candidate);return null;}catch(InvocationTargetException e){return e.getCause();}
    }
    private static void guard(AndroidUIProfile profile,boolean vertical,String change,boolean expected)throws Exception{
        try(Fixture base=new Fixture(profile,vertical,"Inspect","Intro","",false);
            Fixture shadow=new Fixture(profile,vertical,change.equals("echo")?"Wrong echo":"Inspect","Intro",change,false)){
            check(base.edit.requestFocus(),"focus");
            int x=shadow.edit.getLeft(),y=shadow.edit.getTop(),w=shadow.edit.getWidth(),h=shadow.edit.getHeight();
            if(change.equals("y"))y+=29;if(change.equals("x"))x+=1;if(change.equals("width"))w+=1;if(change.equals("height"))h+=29;
            shadow.edit.layout(x,y,x+w,y+h);
            Editable editable=base.edit.getText();base.edit.setSelection(1,3);
            Throwable failure=preflight(base,candidate(base,shadow,change.equals("target"),false));
            check(expected?failure==null:failure instanceof AppearanceDescriptorV2.Failure,"guard "+profile+"/"+vertical+"/"+change+" expected="+expected+" observed="+failure);
            check(base.renderer.view("field")==base.edit&&base.edit.getText()==editable&&base.edit.getSelectionStart()==1&&base.edit.getSelectionEnd()==3,"preflight mutated retained field");
            System.out.println("PASS guard profile="+profile+" vertical="+vertical+" change="+change+" admitted="+expected);cases++;
        }
    }
    private static void echo(boolean baseline,boolean injectFailure)throws Exception{
        try(Fixture f=new Fixture(AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,true,"Inspect","Intro","",true)){
            check(f.edit.requestFocus(),"echo focus");InputConnection connection=f.edit.onCreateInputConnection(new EditorInfo());check(connection!=null,"echo connection");
            check(connection.setSelection(0,f.edit.getText().length()),"echo replace selection");String value="Inspect 雪 🌱\nEast stair";
            check(connection.setComposingText(value,1),"actual InputConnection composition");
            check(f.events.size()==1,"exact single current-owner composition event");
            String envelope=new String(f.events.get(0),StandardCharsets.UTF_8);
            Map<String,Object> event=Json.object(Json.parse(f.events.get(0)));
            check("textChange".equals(event.get("event"))&&value.equals(event.get("value")),"exact emitted value: "+envelope);
            check("field".equals(Json.object(event.get("identity")).get("id")),"event binding identity");
            Editable editable=f.edit.getText();int start=f.edit.getSelectionStart(),end=f.edit.getSelectionEnd();
            int cs=BaseInputConnection.getComposingSpanStart(editable),ce=BaseInputConnection.getComposingSpanEnd(editable);
            check(cs>=0&&ce==value.length(),"native composing spans");
            Object attempt=get(f.edit,"attempt"),target=f.edit.lastConnection;
            int oldY=f.edit.getTop(),oldX=f.edit.getLeft(),oldWidth=f.edit.getWidth();
            if(injectFailure)f.renderer.testFaultV2(0,false);
            RuntimeException failure=null;
            try{f.owner.installExternal(packet(2,true,value,"Intro\nSecond measured header line",""),descriptor);}catch(RuntimeException error){failure=error;}
            if(baseline||injectFailure){
                check(failure!=null&&!f.owner.hasCommittedPresentation(),"baseline/fault must refuse model install");
                check(f.owner.cleanupLedger().primary()!=null,"primary failure not swallowed");
                if(baseline)check(f.owner.cleanupLedger().primary() instanceof AppearanceDescriptorV2.Failure,"baseline failure reason");
                System.out.println("PASS "+(baseline?"baseline-Y-refusal":"injected-failure-preserved")+" primary="+f.owner.cleanupLedger().primary());cases++;return;
            }
            check(failure==null&&f.owner.hasCommittedPresentation(),"V3 model echo rejected: "+failure+" / "+f.owner.diagnostic());
            check(f.renderer.view("field")==f.edit&&f.edit.getText()==editable,"same View/Editable");
            check(f.edit.getSelectionStart()==start&&f.edit.getSelectionEnd()==end,"same selection");
            check(BaseInputConnection.getComposingSpanStart(editable)==cs&&BaseInputConnection.getComposingSpanEnd(editable)==ce,"same composition");
            check(get(f.edit,"attempt")==attempt&&f.edit.lastConnection==target,"same native connection attempt and target");
            check(f.edit.getTop()!=oldY&&f.edit.getLeft()==oldX&&f.edit.getWidth()==oldWidth,"actual measured vertical-only movement");
            check(f.renderer.packet.revision.equals("2")&&f.renderer.inspectV2().get("field").binding.source().text("value","").equals(value),"current model installed");
            check(connection.finishComposingText()&&f.events.size()==1,"retained connection finishing without duplicate business event");
            System.out.println("PASS V3 actual model echo oldY="+oldY+" newY="+f.edit.getTop()+" same View/Editable/selection/composition/connection; exact current model");cases++;
        }
    }
    private static void ownerControl()throws Exception{
        try(Fixture a=new Fixture(AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,true,"Inspect","Intro","",false);
            Fixture b=new Fixture(AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,true,"Inspect","Intro","",false)){
            Throwable failure=null;try{a.renderer.attachV2(candidate(a,b,false,true),a.root);}catch(RuntimeException error){failure=error;}
            check(failure instanceof IllegalArgumentException&&failure.getMessage().contains("stale/foreign/consumed"),"foreign owner candidate refused: "+failure);
            failure=null;try{a.renderer.prepareV2(packet(2,true,"Inspect","Intro",""),(InstalledAppearanceV2)get(a.renderer,"v2Installed"),(NativeEnvironmentV2)get(a.renderer,"v2CommittedEnvironment"));}catch(RuntimeException error){failure=error;}
            check(failure instanceof IllegalArgumentException&&failure.getMessage().contains("transaction authority lost"),"no current owner operation refused: "+failure);
            System.out.println("PASS foreign candidate owner and missing current-operation refusal");cases++;
        }
    }
    public static void main(String[] args)throws Exception{
        descriptor=Files.readAllBytes(Path.of(args[0]));boolean baseline=args[1].equals("baseline");
        echo(baseline,false);if(baseline){System.out.println("PASS baseline cases="+cases+" checks="+checks);return;}
        for(String change:List.of("y","height","x","width","binding","order","ancestor","echo","target"))guard(AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,true,change,change.equals("y")||change.equals("height"));
        guard(AndroidUIProfile.LEGACY_HORIZONTAL,false,"y",false);guard(AndroidUIProfile.LEGACY_HORIZONTAL,false,"height",false);
        guard(AndroidUIProfile.MEASURED_MULTILINE_V2,true,"y",false);guard(AndroidUIProfile.MEASURED_MULTILINE_V2,true,"height",true);
        guard(AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,false,"y",false);guard(AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,false,"height",false);
        ownerControl();echo(false,true);
        try{UiPacket.decode(packet(1,true,"Inspect","Intro",""),AndroidUIProfile.LEGACY_HORIZONTAL);throw new AssertionError("unsupported profile admitted vertical input");}catch(IllegalArgumentException expected){checks++;cases++;System.out.println("PASS unsupported legacy vertical input refused");}
        System.out.println("PASS candidate cases="+cases+" checks="+checks+"; actual renderer/owner/views, controlled Android and JNI leaves; device qualification pending");
    }
}
