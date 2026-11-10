package dev.mixer.android;

import android.app.Activity;
import android.os.Handler;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/** Derived negative controls from actual C-entry packets; controlled host geometry. */
public final class CompleteHandoffHostTests {
    static byte[] descriptor,opened,titleEcho,echo,busy,saved,reset,queue;
    static int checks,cases;
    static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    static Object get(Object o,String name)throws Exception{Field f=o.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(o);}
    static void set(Object o,String name,Object value)throws Exception{Field f=o.getClass().getDeclaredField(name);f.setAccessible(true);f.set(o,value);}
    static Map<String,Object> packet(byte[] bytes){return Json.object(Json.parse(bytes));}
    static Map<String,Object> node(Map<String,Object> p,String id){return GeneratedAddTransitionHostTests.node(Json.object(p.get("document")).get("root"),id);}
    static byte[] encode(Object p){StringBuilder s=new StringBuilder();GeneratedAddTransitionHostTests.write(s,p);return s.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8);}
    static String value(byte[] bytes,String id){return (String)Json.object(node(packet(bytes),id).get("properties")).get("value");}
    static final class Fixture implements AutoCloseable {
        final Activity activity=new Activity();final FrameLayout root=new FrameLayout(activity);
        final List<byte[]> events=new ArrayList<>();final NativeOwnerV2 owner;final NativeRenderer renderer;final Handler handler;
        final EditText title,responsible;InputConnection titleConnection,responsibleConnection;
        boolean quarantined;
        Fixture()throws Exception{
            ConcreteHostProbe.reset();activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);
            root.layout(0,0,1206,2622);activity.window.getDecorView().layout(0,0,1206,2622);root.hostAttach(new Object());
            owner=NativeOwnerV2.external(activity,root,new ExternalFrameSourceV2(events::add));handler=(Handler)get(owner,"handler");
            owner.installExternal(opened,descriptor);renderer=(NativeRenderer)get(get(owner,"coordinator"),"renderer");
            title=(EditText)renderer.view("task.title");responsible=(EditText)renderer.view("task.responsible");
            check(title.requestFocus(),"title focus");titleConnection=title.onCreateInputConnection(new EditorInfo());
            check(titleConnection!=null&&titleConnection.commitText(value(titleEcho,"task.title"),1),"native title edit");owner.installExternal(titleEcho,descriptor);
            check(responsible.requestFocus(),"responsible focus");responsibleConnection=responsible.onCreateInputConnection(new EditorInfo());
            check(responsibleConnection!=null&&responsibleConnection.commitText(value(echo,"task.responsible"),1),"native responsible edit");owner.installExternal(echo,descriptor);
            check(owner.hasCommittedPresentation(),"acknowledged source");ConcreteHostProbe.reset();
        }
        void settled(){owner.installExternal(busy,descriptor);owner.installExternal(saved,descriptor);check(owner.hasCommittedPresentation(),"saved source");ConcreteHostProbe.reset();}
        void refused(byte[] frame,String label){
            var prior=renderer.packet;int count=events.size();Throwable failure=null;
            try{owner.installExternal(frame,descriptor);}catch(RuntimeException error){failure=error;}
            ConcreteHostProbe.hook=null;
            check(failure!=null&&!owner.hasCommittedPresentation(),"refused "+label);
            check(renderer.packet==prior,"no candidate publication "+label);
            check(!responsibleConnection.commitText("late",1)&&events.size()==count,"stale callback fenced "+label);
        }
        public void close(){
            ConcreteHostProbe.hook=null;owner.close();
            if(quarantined){
                // Deliberately destroyed membership cannot authorize scope release.
                // One queued disposal delivery must remain deferred without a native retry.
                check(!owner.hasCommittedPresentation()&&renderer.editorDisposalBusyV2(),"corrupt membership stays quarantined");
                int finishes=ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry");
                int closes=ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry");
                check(handler.queued()==1&&handler.drainOne()&&handler.queued()==1,"one bounded deferred disposal");
                check(ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry")==finishes&&
                    ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==closes,"deferred cleanup never retries native prefix");
                // Cancel only this fixture's scheduled host work; retain the corrupt
                // heap state until this directly owned JVM exits. No scalar release.
                for(Runnable work:handler.snapshot())handler.removeCallbacks(work);
                check(handler.queued()==0,"fixture scheduler detached");
                System.out.println("EXPECTED quarantined heap retained until JVM exit; native cleanup unproven");
            }else handler.drainAll(8);
            ConcreteHostProbe.reset();
        }
    }
    static byte[] resetVariant(String change){
        var p=packet(reset);var r=node(p,"task.responsible");var props=Json.object(r.get("properties"));
        switch(change){
        case "style" -> props.put("accessibilityIdentifier","foreign-style");
        case "actions" -> r.put("actions",List.of(Json.map("event","textChange","id","foreign.change")));
        case "generation" -> {for(var i:Json.array(p.get("identities"))){var identity=Json.object(i);if("task.responsible".equals(identity.get("id")))identity.put("generation",new Json.Num("999"));}}
        case "ancestor-style" -> Json.object(node(p,"task.fields").get("properties")).put("title","Other");
        case "prefix-order" -> {var c=Json.array(node(p,"task.fields").get("children"));Collections.swap(c,0,1);}
        case "lineage" -> {node(p,"task.fields").put("id","foreign.fields");for(var i:Json.array(p.get("identities"))){var identity=Json.object(i);if("task.fields".equals(identity.get("id")))identity.put("id","foreign.fields");}}
        case "replacement" -> props.put("value","unrelated new value");
        default -> throw new AssertionError(change);
        }
        return encode(p);
    }
    static void resetRefusals()throws Exception{
        for(String change:List.of("style","actions","generation","ancestor-style","prefix-order","lineage","replacement")){
            try(Fixture f=new Fixture()){f.settled();f.refused(resetVariant(change),change);check(ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==0,"consumed predecessor not retried");}
            cases++;System.out.println("PASS derived reset refusal "+change);
        }
    }
    static void removalRefusals()throws Exception{
        for(String change:List.of("unacknowledged","unknown-close")){
            try(Fixture f=new Fixture()){
                if(change.equals("unacknowledged"))check(f.responsibleConnection.commitText(" newer",1),"unacknowledged native edit");
                else {var field=(NativeAppearanceViewsV2.NativeField)f.responsible;field.attempt.revoked=true;field.attempt.close=NativeAppearanceViewsV2.NativeField.Close.FAILED_UNCERTAIN;}
                f.refused(queue,change);check(ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==0,"invalid removal never closes predecessor");
            }
            cases++;System.out.println("PASS derived removal refusal "+change);
        }
    }
    static void removalFaults()throws Exception{
        for(String fault:List.of("finish","close","attach","rollback")){
            try(Fixture f=new Fixture()){
                RuntimeException injected=new IllegalStateException("R120 removal "+fault);boolean[] hit={false};
                if(fault.equals("finish")||fault.equals("close"))ConcreteHostProbe.hook=(m,phase)->{
                    if(!hit[0]&&m.equals("BaseInputConnection."+(fault.equals("finish")?"finishComposingText":"closeConnection"))&&phase.equals("entry")){
                        var event=ConcreteHostProbe.lastEvent();
                        if(event.receiver==f.responsible.lastConnection){hit[0]=true;throw injected;}
                    }
                };
                else f.renderer.testFaultV2(0,fault.equals("rollback"));
                f.quarantined=fault.equals("finish")||fault.equals("close");
                f.refused(queue,fault);var primary=f.owner.cleanupLedger().primary();
                if(fault.equals("finish")||fault.equals("close"))check(hit[0]&&primary==injected,"original native error retained");
                else check(primary!=null&&primary.getMessage().equals("test-only V2 attachment fault"),"original attachment error retained");
                if(fault.equals("close")){var a=((NativeAppearanceViewsV2.NativeField)f.responsible).attempt;check(a.revoked&&a.close==NativeAppearanceViewsV2.NativeField.Close.FAILED_UNCERTAIN,"unknown close retained");}
            }
            cases++;System.out.println("PASS horizontal removal fault "+fault);
        }
    }
    static void membership()throws Exception{
        for(String change:List.of("record-slot","roster-slot","predecessor","before-binding","candidate-owner")){
            try(Fixture f=new Fixture()){
                boolean[] hit={false};ConcreteHostProbe.hook=(m,phase)->{
                    if(hit[0]||!m.equals("BaseInputConnection.finishComposingText")||!phase.equals("entry")||ConcreteHostProbe.lastEvent().receiver!=f.responsible.lastConnection)return;
                    hit[0]=true;
                    try{
                        var record=f.renderer.inspectV2().get("task.responsible");var scope=record.fieldTransition;check(scope!=null,"horizontal removal transition captured");
                        switch(change){
                        case "record-slot" -> record.fieldTransition=null;
                        case "roster-slot" -> {Object[] roster=(Object[])get(scope.journal,"transitionRoster");for(int i=0;i<roster.length;i++)if(roster[i]!=null&&get(roster[i],"scope")==scope)roster[i]=null;}
                        case "predecessor" -> ((NativeAppearanceViewsV2.NativeField)f.responsible).attempt=null;
                        case "before-binding" -> set(scope,"before",null);
                        case "candidate-owner" -> set(scope.candidate,"owner",null);
                        default -> throw new AssertionError(change);
                        }
                    }catch(ReflectiveOperationException error){throw new AssertionError(error);}catch(Exception error){throw new IllegalStateException(error);}
                };
                f.quarantined=true;
                f.refused(queue,change);check(hit[0],"membership stimulus reached");
                var effects=ConcreteHostProbe.events();
                long responsibleFinish=effects.stream().filter(e->e.method.equals("BaseInputConnection.finishComposingText")&&e.phase.equals("entry")&&e.receiver==f.responsible.lastConnection).count();
                long responsibleClose=effects.stream().filter(e->e.method.equals("BaseInputConnection.closeConnection")&&e.phase.equals("entry")&&e.receiver==f.responsible.lastConnection).count();
                long titleFinish=effects.stream().filter(e->e.method.equals("BaseInputConnection.finishComposingText")&&e.phase.equals("entry")&&e.receiver==f.title.lastConnection).count();
                long titleClose=effects.stream().filter(e->e.method.equals("BaseInputConnection.closeConnection")&&e.phase.equals("entry")&&e.receiver==f.title.lastConnection).count();
                System.out.println("MEMBERSHIP "+change+" responsibleFinish="+responsibleFinish+" responsibleClose="+responsibleClose+" titleFinish="+titleFinish+" titleClose="+titleClose);
                check(responsibleFinish==1&&responsibleClose==0,"corrupt horizontal member cannot close or repeat finish");
                check(titleFinish<=1&&titleClose<=1,"earlier title predecessor consumed at most once");
            }
            cases++;System.out.println("PASS horizontal removal membership refusal "+change);
        }
    }
    public static void main(String[] args)throws Exception{
        Path p=Path.of(args[0]);descriptor=Files.readAllBytes(p.resolve("descriptor.json"));
        Path flow=p.resolve("before-public-reset");opened=Files.readAllBytes(flow.resolve("00.json"));titleEcho=Files.readAllBytes(flow.resolve("01.json"));
        echo=Files.readAllBytes(flow.resolve("02.json"));busy=Files.readAllBytes(flow.resolve("03.json"));saved=Files.readAllBytes(flow.resolve("04.json"));reset=Files.readAllBytes(flow.resolve("05.json"));
        queue=Files.readAllBytes(p.resolve("before-public-queue/03.json"));
        resetRefusals();removalRefusals();removalFaults();membership();
        System.out.println("PASS CompleteHandoffHostTests cases="+cases+" checks="+checks+" nativeRuntime=false");
    }
}
