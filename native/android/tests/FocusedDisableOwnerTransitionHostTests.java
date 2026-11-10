package dev.mixer.android;

import android.app.Activity;
import android.os.Handler;
import android.text.Editable;
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

/** Production owner, renderer, field and editor connection; controlled Android/JNI leaves. */
public final class FocusedDisableOwnerTransitionHostTests {
    static byte[] descriptor,opened,echo,busy,saved; static int checks,cases;
    static void check(boolean ok,String message){checks++;if(!ok)throw new AssertionError(message);}
    static Object get(Object o,String name)throws Exception{Field f=o.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(o);}
    static byte[] encode(Object v){StringBuilder b=new StringBuilder();GeneratedAddTransitionHostTests.write(b,v);return b.toString().getBytes(StandardCharsets.UTF_8);}
    static Map<String,Object> packet(byte[] bytes){return Json.object(Json.parse(bytes));}
    static Map<String,Object> node(Map<String,Object> p,String id){return GeneratedAddTransitionHostTests.node(Json.object(p.get("document")).get("root"),id);}
    static String value(byte[] bytes,String id){return (String)Json.object(node(packet(bytes),id).get("properties")).get("value");}
    static byte[] variant(byte[] bytes,String change){
        Map<String,Object> p=packet(bytes),n=node(p,"task.responsible"),props=Json.object(n.get("properties"));
        switch(change){
            case "enabled" -> props.put("disabled",false);
            case "binding" -> props.put("label","Other label");
            case "style" -> props.put("accessibilityIdentifier","different-style-contract");
            case "actions" -> n.put("actions",List.of(Json.map("event","textChange","id","other.change")));
            case "value" -> props.put("value","unrelated replacement");
            case "generation" -> {for(Object i:Json.array(p.get("identities"))){Map<String,Object> identity=Json.object(i);if("task.responsible".equals(identity.get("id")))identity.put("generation",new Json.Num("999"));}}
            case "topology" -> {List<Object> children=Json.array(node(p,"task.fields").get("children"));Object first=children.remove(0);children.add(first);}
            case "disableOnly" -> {props.put("disabled",true);Json.object(p.get("document")).put("revision",new Json.Num("3"));}
            default -> throw new AssertionError(change);
        }
        return encode(p);
    }
    static final class Fixture implements AutoCloseable {
        boolean quarantined;
        final Activity activity=new Activity();final FrameLayout root=new FrameLayout(activity);
        final List<byte[]> events=new ArrayList<>();final NativeOwnerV2 owner;final Handler queue;final NativeRenderer renderer;final EditText edit;
        Fixture(byte[] frame)throws Exception{this(frame,AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3);}
        Fixture(byte[] frame,AndroidUIProfile profile)throws Exception{
            ConcreteHostProbe.reset();activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);
            root.layout(0,0,1206,2622);activity.window.getDecorView().layout(0,0,1206,2622);root.hostAttach(new Object());
            if(profile==AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3){owner=NativeOwnerV2.external(activity,root,new ExternalFrameSourceV2(events::add));queue=(Handler)get(owner,"handler");owner.installExternal(frame,descriptor);}
            else {NativeBridge.reset();NativeBridge.preparedPacket=frame;owner=NativeOwnerV2.forProfile(activity,root,profile);queue=(Handler)get(owner,"handler");owner.onResume();owner.start();queue.drainAll(8);}
            check(owner.hasCommittedPresentation(),"initial presentation "+owner.diagnostic());renderer=(NativeRenderer)get(get(owner,"coordinator"),"renderer");edit=(EditText)renderer.view("task.responsible");ConcreteHostProbe.reset();
        }
        InputConnection acknowledged()throws Exception{
            check(edit.requestFocus(),"focus responsible");InputConnection c=edit.onCreateInputConnection(new EditorInfo());check(c!=null,"actual NativeEditorConnection");
            check(c.commitText(value(echo,"task.responsible"),1),"native responsible input");check(events.size()==1,"single native event");
            check(value(echo,"task.responsible").equals(Json.object(Json.parse(events.get(0))).get("value")),"native unicode event exact");
            Editable buffer=edit.getText();Object attempt=get(edit,"attempt"),target=edit.lastConnection;
            owner.installExternal(echo,descriptor);check(owner.hasCommittedPresentation(),"accepted model echo");
            check(renderer.view("task.responsible")==edit&&edit.getText()==buffer&&get(edit,"attempt")==attempt&&edit.lastConnection==target,"acknowledged echo preserves native identities");
            check(c.setComposingRegion(0,buffer.length()),"live composing region");return c;
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
    static NativeRenderer.Candidate candidate(Fixture base,Fixture shadow,String change)throws Exception{
        Map<String,NativeAppearanceViewsV2.Record> targets=new LinkedHashMap<>(base.renderer.inspectV2());
        for(var e:shadow.renderer.inspectV2().entrySet())if(!targets.containsKey(e.getKey()))targets.put(e.getKey(),e.getValue());
        if(change.equals("target"))targets.put("task.responsible",shadow.renderer.inspectV2().get("task.responsible"));
        Constructor<?> ctor=NativeRenderer.Candidate.class.getDeclaredConstructors()[0];ctor.setAccessible(true);
        return (NativeRenderer.Candidate)ctor.newInstance(change.equals("owner")?shadow.renderer:base.renderer,shadow.renderer.packet,new byte[0],targets,shadow.renderer.inspectV2(),get(shadow.renderer,"v2Plan"),get(base.renderer,"v2Installed"),get(base.renderer,"v2CommittedEnvironment"),get(base.renderer,"v2Gate"));
    }
    static Throwable preflight(Fixture f,NativeRenderer.Candidate c)throws Exception{
        Method m=NativeRenderer.class.getDeclaredMethod("preflightEditorsV2",NativeRenderer.Candidate.class);m.setAccessible(true);
        try{m.invoke(f.renderer,c);return null;}catch(InvocationTargetException e){return e.getCause();}
    }
    static void diagnose(boolean baseline)throws Exception{
        for(String label:List.of("captured-busy","synthesized-disabled-only","synthesized-busy-responsible-enabled")){
            byte[] next=label.equals("captured-busy")?busy:label.equals("synthesized-disabled-only")?variant(echo,"disableOnly"):variant(busy,"enabled");
            try(Fixture f=new Fixture(opened);Fixture shadow=new Fixture(next)){
                f.acknowledged();
                // A detached candidate shares its renderer's input and editor fence.
                // Borrow that context only for this read-only private preflight.
                Field input=NativeAppearanceViewsV2.Record.class.getDeclaredField("input");input.setAccessible(true);
                Field fence=NativeAppearanceViewsV2.Record.class.getDeclaredField("editorFence");fence.setAccessible(true);
                List<Object[]> prior=new ArrayList<>();Throwable failure;
                try{
                    for(var record:shadow.renderer.inspectV2().values()){
                        prior.add(new Object[]{record,input.get(record),fence.get(record)});
                        input.set(record,get(f.renderer,"v2Input"));fence.set(record,get(f.renderer,"v2Fence"));
                    }
                    failure=preflight(f,candidate(f,shadow,""));
                }finally{for(Object[] record:prior){input.set(record[0],record[1]);fence.set(record[0],record[2]);}}
                var old=f.renderer.inspectV2().get("task.responsible");var proposed=shadow.renderer.inspectV2().get("task.responsible");
                Map<String,Object> left=new LinkedHashMap<>(old.binding.source().properties),right=new LinkedHashMap<>(proposed.binding.source().properties);
                left.remove("value");right.remove("value");left.remove("disabled");right.remove("disabled");
                check(left.equals(right)&&old.binding.source().actions.equals(proposed.binding.source().actions),"configuration excluding disabled identical");
                check(old.binding.nativeFieldValue().equals(proposed.binding.nativeFieldValue())&&old.binding.nativeFieldValue().equals(f.edit.getText().toString()),"accepted current-buffer echo");
                check(f.edit.getLeft()==shadow.edit.getLeft()&&f.edit.getTop()==shadow.edit.getTop()&&f.edit.getWidth()==shadow.edit.getWidth()&&f.edit.getHeight()==shadow.edit.getHeight(),"exact unchanged horizontal frame");
                check((failure!=null)==(baseline&&!label.endsWith("enabled")),"disabled-only discriminant "+label+" "+failure);
                System.out.println("PASS DIAG "+label+" oldDisabled="+old.binding.node().disabled()+" nextDisabled="+proposed.binding.node().disabled()+" sameValue/binding/actions/frame=true failure="+failure);cases++;
            }
        }
    }
    static void save(boolean baseline,String fault)throws Exception{
        try(Fixture f=new Fixture(opened)){
            InputConnection old=f.acknowledged();Editable buffer=f.edit.getText();Object before=f.renderer.packet;int events=f.events.size();
            RuntimeException injected=new IllegalStateException("R98 "+fault);boolean[] hit={false};
            if(fault.equals("finish")||fault.equals("close"))ConcreteHostProbe.hook=(m,p)->{if(!hit[0]&&m.equals("BaseInputConnection."+(fault.equals("finish")?"finishComposingText":"closeConnection"))&&p.equals("entry")){hit[0]=true;throw injected;}};
            if(fault.equals("attach")||fault.equals("rollback"))f.renderer.testFaultV2(0,fault.equals("rollback"));
            Throwable error=null;try{f.owner.installExternal(busy,descriptor);}catch(RuntimeException e){error=e;}ConcreteHostProbe.hook=null;
            if(baseline||!fault.isEmpty()){
                f.quarantined=fault.equals("finish")||fault.equals("close");
                check(error!=null&&!f.owner.hasCommittedPresentation(),"baseline or fault refused");Throwable primary=f.owner.cleanupLedger().primary();check(primary!=null,"primary retained");
                if(baseline)check(primary instanceof AppearanceDescriptorV2.Failure&&primary.getStackTrace()[0].getMethodName().equals("preflightEditorPlanV2"),"exact R96 causal stack");
                if(fault.equals("finish")||fault.equals("close"))check(hit[0]&&primary==injected,"exact original primary");
                if(fault.equals("attach")||fault.equals("rollback"))check(primary.getMessage().equals("test-only V2 attachment fault"),"original attachment error");
                if(fault.equals("close"))check(((NativeAppearanceViewsV2.NativeField)f.edit).attempt.close==NativeAppearanceViewsV2.NativeField.Close.FAILED_UNCERTAIN,"uncertain close remains uncertain");
                check(f.renderer.packet==before,"candidate unpublished");check(!old.commitText("late",1),"old connection fenced after failure");
                check(ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry")<=1&&ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")<=1,"no repeat finish/close after failure");
                System.out.println("PASS "+(baseline?"baseline actual busy refusal":"fault "+fault)+" primary="+primary);cases++;return;
            }
            check(error==null&&f.owner.hasCommittedPresentation(),"busy committed "+error+" / "+f.owner.diagnostic());
            check(f.renderer.view("task.responsible")==f.edit&&f.edit.getText()==buffer&&f.edit.getText().toString().equals(value(busy,"task.responsible")),"same View and Editable, unchanged text");
            check(!f.edit.isEnabled()&&!f.edit.hasFocus()&&BaseInputConnection.getComposingSpanStart(buffer)<0,"disabled/unfocused/composition consumed");
            check(f.edit.onCreateInputConnection(new EditorInfo())==null,"disabled cannot open input");
            check(!old.commitText("late",1)&&!old.setComposingText("late",1),"late predecessor fenced");old.closeConnection();old.closeConnection();
            check(f.events.size()==events,"no programmatic reducer event");
            check(ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry")==1&&ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==1,"one finish and one close");
            f.owner.installExternal(saved,descriptor);check(f.owner.hasCommittedPresentation(),"captured saved frame commits");
            check(f.renderer.view("task.responsible")==f.edit&&f.edit.getText()==buffer&&!f.edit.isEnabled(),"saved frame retains disabled View and Editable");
            check(f.renderer.packet.nodes.get("task.save").text("label","").equals("Saved"),"actual saved action visible");
            check(ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry")==1&&ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==1,"saved frame never reconsumes predecessor");
            System.out.println("PASS captured busy -> saved under actual owner, same View/Editable, finish/close once, late input fenced, no disabled connection");cases++;
        }
    }
    static void controls()throws Exception{
        for(String change:List.of("binding","style","actions","value","generation","topology","target","owner","x","width","y","height","unacknowledged","unknown")){
            byte[] next=List.of("binding","style","actions","value","generation","topology").contains(change)?variant(busy,change):busy;
            try(Fixture f=new Fixture(opened);Fixture shadow=new Fixture(next)){
                InputConnection old=f.acknowledged();
                if(change.equals("unacknowledged"))check(old.commitText("unacknowledged",1),"new native input");
                if(change.equals("unknown")){var a=((NativeAppearanceViewsV2.NativeField)f.edit).attempt;a.revoked=true;a.close=NativeAppearanceViewsV2.NativeField.Close.FAILED_UNCERTAIN;}
                int x=shadow.edit.getLeft(),y=shadow.edit.getTop(),w=shadow.edit.getWidth(),h=shadow.edit.getHeight();
                if(change.equals("x"))x++;if(change.equals("y"))y++;if(change.equals("width"))w++;if(change.equals("height"))h++;shadow.edit.layout(x,y,x+w,y+h);
                var c=candidate(f,shadow,change);String text=f.edit.getText().toString();Throwable failure;
                if(change.equals("owner")){try{f.renderer.attachV2(c,f.root);failure=null;}catch(RuntimeException e){failure=e;}}
                else failure=preflight(f,c);
                check(failure!=null,"fail closed "+change);check(f.edit.getText().toString().equals(text),"no mutation "+change);
                check(ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry")==0&&ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==0,"no retirement during invalid preflight");
                System.out.println("PASS refusal "+change+" "+failure);cases++;
            }
        }
    }
    static byte[] settledOpened(){
        Map<String,Object> p=packet(echo);Json.object(node(p,"task.responsible").get("properties")).put("value","");Json.object(p.get("document")).put("revision",new Json.Num("1"));return encode(p);
    }
    static byte[] horizontalOnly(byte[] frame){Map<String,Object> p=packet(frame);Json.object(node(p,"task.title").get("properties")).remove("axis");return encode(p);}
    static void legacy()throws Exception{
        for(AndroidUIProfile profile:List.of(AndroidUIProfile.LEGACY_HORIZONTAL,AndroidUIProfile.MEASURED_MULTILINE_V2)){
            byte[] prior=horizontalOnly(echo),next=horizontalOnly(busy);
            try(Fixture f=new Fixture(prior,profile);Fixture shadow=new Fixture(next,profile)){
                check(f.edit.requestFocus()&&f.edit.onCreateInputConnection(new EditorInfo())!=null,"legacy live editor");
                check(preflight(f,candidate(f,shadow,"")) instanceof AppearanceDescriptorV2.Failure,"legacy disable refuses");System.out.println("PASS legacy unchanged disable refusal "+profile);cases++;
            }
        }
    }
    public static void main(String[] args)throws Exception{
        Path p=Path.of(args[0]);descriptor=Files.readAllBytes(p.resolve("descriptor.json"));echo=Files.readAllBytes(p.resolve("synthesized-acknowledged-presave.json"));opened=settledOpened();busy=Files.readAllBytes(p.resolve("201-2.json"));saved=Files.readAllBytes(p.resolve("201-3.json"));
        boolean baseline=args[1].equals("baseline");diagnose(baseline);save(baseline,"");
        if(!baseline){controls();legacy();for(String fault:List.of("finish","close","attach","rollback"))save(false,fault);}
        System.out.println("PASS "+args[1]+" cases="+cases+" checks="+checks+"; actual production closure B; controlled Android/JNI leaves; no native runtime qualification");
    }
}
