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

/** Exact production C-entry packets; controlled Android/JNI leaves, no runtime qualification. */
public final class GeneratedAddTransitionHostTests {
    static byte[] descriptor,opened,typed,added;
    static int checks,cases;
    static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    static Object get(Object object,String name)throws Exception{Field f=object.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(object);}
    static Object call(String name,Object...args)throws Exception{
        for(Method m:NativeRenderer.class.getDeclaredMethods())if(m.getName().equals(name)){m.setAccessible(true);return m.invoke(null,args);}throw new AssertionError(name);
    }
    static final class Fixture implements AutoCloseable {
        boolean quarantined;
        final Activity activity=new Activity(); final FrameLayout root=new FrameLayout(activity);
        final List<byte[]> events=new ArrayList<>(); final NativeOwnerV2 owner; final Handler queue;
        final NativeRenderer renderer; final EditText edit;
        Fixture(byte[] bytes)throws Exception{this(bytes,AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3);}
        Fixture(byte[] bytes,AndroidUIProfile profile)throws Exception{
            ConcreteHostProbe.reset();activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);
            root.layout(0,0,1206,2622);activity.window.getDecorView().layout(0,0,1206,2622);root.hostAttach(new Object());
            if(profile==AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3){owner=NativeOwnerV2.external(activity,root,new ExternalFrameSourceV2(events::add));queue=(Handler)get(owner,"handler");owner.installExternal(bytes,descriptor);}
            else{NativeBridge.reset();NativeBridge.preparedPacket=bytes;owner=NativeOwnerV2.forProfile(activity,root,profile);queue=(Handler)get(owner,"handler");owner.onResume();owner.start();queue.drainAll(8);}
            check(owner.hasCommittedPresentation(),"initial owner "+owner.diagnostic());
            renderer=(NativeRenderer)get(get(owner,"coordinator"),"renderer");edit=(EditText)renderer.view("draft");ConcreteHostProbe.reset();
        }
        InputConnection type()throws Exception{
            check(edit.requestFocus(),"focus draft");InputConnection c=edit.onCreateInputConnection(new EditorInfo());check(c!=null,"native connection");
            check(c.commitText("R68-native-entry",1),"native typing");check(events.size()==1,"one exact typed event");
            check("R68-native-entry".equals(Json.object(Json.parse(events.get(0))).get("value")),"exact native event value");
            check(c.setComposingRegion(0,edit.getText().length()),"composition region");check(events.size()==1,"composition alone no reducer event");
            Editable editable=edit.getText();int cs=BaseInputConnection.getComposingSpanStart(editable),ce=BaseInputConnection.getComposingSpanEnd(editable);int s=edit.getSelectionStart(),e=edit.getSelectionEnd();Object attempt=get(edit,"attempt"),target=edit.lastConnection;
            owner.installExternal(typed,descriptor);check(owner.hasCommittedPresentation(),"exact typed model echo");
            check(renderer.view("draft")==edit&&edit.getText()==editable&&edit.getSelectionStart()==s&&edit.getSelectionEnd()==e&&get(edit,"attempt")==attempt&&edit.lastConnection==target&&BaseInputConnection.getComposingSpanStart(editable)==cs&&BaseInputConnection.getComposingSpanEnd(editable)==ce,"echo View/Editable/selection/composition/connection identity");return c;
        }
        @Override public void close(){
            ConcreteHostProbe.hook=null;owner.close();
            if(quarantined){
                check(!owner.hasCommittedPresentation()&&renderer.editorDisposalBusyV2(),"uncertain prefix retains transition custody");
                int finishes=ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry");
                int closes=ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry");
                Throwable primary=owner.cleanupLedger().primary();
                check(queue.queued()==1&&queue.drainOne()&&queue.queued()==1,"one bounded deferred disposal remains");
                check(ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry")==finishes&&ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==closes,"deferred disposal never repeats native prefix");
                check(owner.cleanupLedger().primary()==primary,"deferred disposal preserves primary error");
                for(Runnable work:queue.snapshot())queue.removeCallbacks(work);
                check(queue.queued()==0,"detach only fixture scheduled work; retain heap until JVM exit");
            }else queue.drainAll(8);
            ConcreteHostProbe.reset();
        }
    }
    static NativeRenderer.Candidate candidate(Fixture base,Fixture shadow,String mutation)throws Exception{
        Map<String,NativeAppearanceViewsV2.Record> targets=new LinkedHashMap<>(base.renderer.inspectV2());
        for(var e:shadow.renderer.inspectV2().entrySet())if(!targets.containsKey(e.getKey()))targets.put(e.getKey(),e.getValue());
        if(mutation.equals("target"))targets.put("draft",shadow.renderer.inspectV2().get("draft"));
        Constructor<?> ctor=NativeRenderer.Candidate.class.getDeclaredConstructors()[0];ctor.setAccessible(true);
        return (NativeRenderer.Candidate)ctor.newInstance(mutation.equals("owner")?shadow.renderer:base.renderer,shadow.renderer.packet,new byte[0],targets,shadow.renderer.inspectV2(),get(shadow.renderer,"v2Plan"),get(base.renderer,"v2Installed"),get(base.renderer,"v2CommittedEnvironment"),get(base.renderer,"v2Gate"));
    }
    static Throwable preflight(Fixture f,NativeRenderer.Candidate c)throws Exception{
        Method m=NativeRenderer.class.getDeclaredMethod("preflightEditorsV2",NativeRenderer.Candidate.class);m.setAccessible(true);
        try{m.invoke(f.renderer,c);return null;}catch(InvocationTargetException e){return e.getCause();}
    }
    static void diagnose(byte[] bytes,String label)throws Exception{
        try(Fixture f=new Fixture(opened);Fixture shadow=new Fixture(bytes)){
            f.type();var c=candidate(f,shadow,"");var old=f.renderer.inspectV2().get("draft");var next=shadow.renderer.inspectV2().get("draft");
            boolean reuse=((Map<?,?>)get(c,"targets")).get("draft")==old;
            boolean binding=(Boolean)call("sameEditorBindingV2",old,next),ancestry=(Boolean)call("sameAncestorsV2",c,"draft");
            boolean frame=(Boolean)call("sameFrameV2",f.edit,shadow.edit,AndroidUIProfile.LEGACY_HORIZONTAL);
            String first=!reuse?"target":!binding?"binding":!ancestry?"ancestors":!frame?"frame":"none";
            Throwable failure=preflight(f,c);System.out.println("DIAG "+label+" target="+reuse+" binding="+binding+" ancestors="+ancestry+" frame="+frame+" firstFalse="+first+" beforeFrame="+f.edit.getLeft()+","+f.edit.getTop()+","+f.edit.getWidth()+","+f.edit.getHeight()+" afterFrame="+shadow.edit.getLeft()+","+shadow.edit.getTop()+","+shadow.edit.getWidth()+","+shadow.edit.getHeight()+" preflight="+failure);
            if(label.equals("exact"))check(first.equals("binding")&&reuse&&ancestry&&frame,"actual packet discriminant");cases++;
        }
    }
    static void write(StringBuilder out,Object value){
        if(value instanceof List<?> list){out.append('[');for(int i=0;i<list.size();i++){if(i>0)out.append(',');write(out,list.get(i));}out.append(']');}
        else if(value instanceof Map<?,?> map){out.append('{');boolean comma=false;for(var e:map.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,e.getKey());out.append(':');write(out,e.getValue());}out.append('}');}else Json.write(out,value);
    }
    @SuppressWarnings("unchecked") static Map<String,Object> node(Object value,String id){
        Map<String,Object> m=(Map<String,Object>)value;if(id.equals(m.get("id")))return m;
        for(Object child:(List<Object>)m.getOrDefault("children",List.of())){Map<String,Object> found=node(child,id);if(found!=null)return found;}return null;
    }
    @SuppressWarnings("unchecked") static byte[] variant(byte[] input,String change){
        Map<String,Object> p=Json.object(Json.parse(input));Map<String,Object> root=Json.object(Json.object(p.get("document")).get("root"));
        Map<String,Object> draft=node(root,"draft"),props=(Map<String,Object>)draft.get("properties");
        switch(change){
            case "valueOnly" -> props.put("value","");
            case "keepValue" -> props.put("value","R68-native-entry");
            case "binding" -> props.put("label","Changed label");
            case "actions" -> draft.put("actions",List.of(Json.map("id","wrong.change","event","textChange")));
            case "arbitraryValue" -> props.put("value","unrelated replacement");
            case "generation" -> {for(Object x:(List<Object>)p.get("identities")){Map<String,Object> identity=(Map<String,Object>)x;if("draft".equals(identity.get("id")))identity.put("generation",new Json.Num("999"));}}
            case "topology" -> {List<Object> children=(List<Object>)node(root,"editor").get("children");Object first=children.remove(0);children.add(first);}
            default -> throw new AssertionError(change);
        }
        StringBuilder out=new StringBuilder();write(out,p);return out.toString().getBytes(StandardCharsets.UTF_8);
    }
    static void install(boolean baseline,String fault)throws Exception{
        try(Fixture f=new Fixture(opened)){
            InputConnection old=f.type();Object oldPacket=f.renderer.packet;int prior=f.events.size();
            RuntimeException injected=new IllegalStateException("R81 injected "+fault);boolean[] hit={false};
            if(fault.equals("close")||fault.equals("finish"))ConcreteHostProbe.hook=(method,phase)->{if(!hit[0]&&method.equals("BaseInputConnection."+(fault.equals("close")?"closeConnection":"finishComposingText"))&&phase.equals("entry")){hit[0]=true;throw injected;}};
            if(fault.equals("attach")||fault.equals("rollback"))f.renderer.testFaultV2(0,fault.equals("rollback"));
            Throwable failure=null;try{f.owner.installExternal(added,descriptor);}catch(RuntimeException e){failure=e;}
            ConcreteHostProbe.hook=null;
            if(baseline||!fault.isEmpty()){
                f.quarantined=fault.equals("finish")||fault.equals("close");
                check(failure!=null&&!f.owner.hasCommittedPresentation(),"refuse baseline/fault "+fault);
                Throwable primary=f.owner.cleanupLedger().primary();check(primary!=null,"original primary kept");
                if(baseline)check(primary instanceof AppearanceDescriptorV2.Failure,"baseline unsupportedNativeOperation");
                if(fault.equals("close")||fault.equals("finish"))check(hit[0]&&primary==injected,"exact injected primary retained");
                if(fault.equals("attach")||fault.equals("rollback"))check(primary.getMessage().equals("test-only V2 attachment fault"),"rollback keeps original attachment primary");
                if(fault.equals("close")){var a=((NativeAppearanceViewsV2.NativeField)f.edit).attempt;check(a.revoked&&a.close==NativeAppearanceViewsV2.NativeField.Close.FAILED_UNCERTAIN,"unknown close remains fenced");check(ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==1,"unknown close never retried");}
                check(f.renderer.packet==oldPacket,"failed candidate not published");check(!old.commitText("late",1),"failed old connection fenced");
                System.out.println("PASS "+(baseline?"baseline exact Add refusal":fault+" failure")+" primary="+primary);cases++;return;
            }
            check(failure==null&&f.owner.hasCommittedPresentation(),"exact Add install "+failure+" / "+f.owner.diagnostic());
            check(f.renderer.view("draft")==f.edit&&f.edit.getText().toString().isEmpty(),"same field cleared");
            check(f.renderer.packet.revision.equals("3")&&f.renderer.inspectV2().values().stream().anyMatch(r->r.kind.equals("toggle")&&r.binding.source().text("label","").equals("R68-native-entry")),"new toggle committed");
            check(f.events.size()==prior,"programmatic clear no reducer echo");
            check(ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry")==1&&ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==1,"one finish/one close");
            check(!old.commitText("late",1),"stale predecessor fenced");check(f.edit.requestFocus(),"refocus settled field");
            InputConnection fresh=f.edit.onCreateInputConnection(new EditorInfo());check(fresh!=null&&fresh!=old&&fresh.commitText("Next",1),"new native connection usable");
            check(f.events.size()==prior+1,"fresh current event");System.out.println("PASS exact Add clears same field, commits new toggle, closes predecessor once, fresh connection types");cases++;
        }
    }
    static void controls()throws Exception{
        for(String change:List.of("target","binding","generation","topology","arbitraryValue","actions","x","width","y","height","owner","unacknowledged","unknown")){
            byte[] input=List.of("binding","generation","topology","arbitraryValue","actions").contains(change)?variant(added,change):added;
            try(Fixture f=new Fixture(opened);Fixture shadow=new Fixture(input)){
                InputConnection oldConnection=f.type();
                if(change.equals("unacknowledged"))check(oldConnection.commitText("newer",1),"unacknowledged edit");
                if(change.equals("unknown")){var a=((NativeAppearanceViewsV2.NativeField)f.edit).attempt;a.revoked=true;a.close=NativeAppearanceViewsV2.NativeField.Close.FAILED_UNCERTAIN;}
                String beforeText=f.edit.getText().toString();int x=shadow.edit.getLeft(),y=shadow.edit.getTop(),w=shadow.edit.getWidth(),h=shadow.edit.getHeight();
                if(change.equals("x"))x++;if(change.equals("y"))y++;if(change.equals("width"))w++;if(change.equals("height"))h++;
                shadow.edit.layout(x,y,x+w,y+h);NativeRenderer.Candidate c=candidate(f,shadow,change);Throwable failure;
                if(change.equals("owner")){try{f.renderer.attachV2(c,f.root);failure=null;}catch(RuntimeException e){failure=e;}}
                else failure=preflight(f,c);
                check(failure!=null,"invalid "+change+" refused");check(f.edit.getText().toString().equals(beforeText),"no mutation "+change);
                System.out.println("PASS refusal "+change+" "+failure);cases++;
            }
        }
    }
    static void earlierProfiles()throws Exception{
        for(AndroidUIProfile profile:List.of(AndroidUIProfile.LEGACY_HORIZONTAL,AndroidUIProfile.MEASURED_MULTILINE_V2)){
            try(Fixture f=new Fixture(typed,profile);Fixture shadow=new Fixture(added,profile)){
                check(f.edit.requestFocus(),"old profile focus");check(f.edit.onCreateInputConnection(new EditorInfo())!=null,"old profile connection");
                Throwable failure=preflight(f,candidate(f,shadow,""));check(failure instanceof AppearanceDescriptorV2.Failure,"old profile clear remains refused "+profile);
                System.out.println("PASS original profile clear refusal "+profile);cases++;
            }
        }
    }
    public static void main(String[] args)throws Exception{
        Path packets=Path.of(args[0]);descriptor=Files.readAllBytes(packets.resolve("descriptor.json"));opened=Files.readAllBytes(packets.resolve("opened.packet.json"));typed=Files.readAllBytes(packets.resolve("typed.packet.json"));added=Files.readAllBytes(packets.resolve("added.packet.json"));
        boolean baseline=args[1].equals("baseline");diagnose(added,"exact");diagnose(variant(typed,"valueOnly"),"synthetic-value-only");diagnose(variant(added,"keepValue"),"synthetic-items-geometry-only");install(baseline,"");
        if(!baseline){controls();earlierProfiles();for(String fault:List.of("finish","close","attach","rollback"))install(false,fault);}
        System.out.println("PASS "+args[1]+" cases="+cases+" checks="+checks+" controlled Android/JNI, production closure and exact C-entry packets; no runtime pass");
    }
}
