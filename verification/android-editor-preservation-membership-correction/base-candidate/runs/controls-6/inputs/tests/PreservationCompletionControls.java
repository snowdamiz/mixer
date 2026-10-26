package dev.mixer.android;

import android.app.Activity;
import android.os.Handler;
import android.text.Editable;
import android.text.Spanned;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Bounded complete-product controls. Reflection denotes hostile invariant fixtures only. */
public final class PreservationCompletionControls {
    private PreservationCompletionControls() {}
    private static byte[] descriptor;private static int checks;
    private static void check(boolean condition,String label){checks++;if(!condition)throw new AssertionError(label);}
    private static Object get(Object object,String name){try{Field field=object.getClass().getDeclaredField(name);field.setAccessible(true);return field.get(object);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static void put(Object object,String name,Object value){try{Field field=object.getClass().getDeclaredField(name);field.setAccessible(true);field.set(object,value);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static void call(Object object,String name){try{Method method=object.getClass().getDeclaredMethod(name);method.setAccessible(true);method.invoke(object);}catch(InvocationTargetException failure){Throwable cause=failure.getCause();if(cause instanceof Error fatal)throw fatal;throw (RuntimeException)cause;}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static boolean in(String method){return ConcreteHostProbe.lastEvent().productionFrames.stream().anyMatch(frame->frame.className().equals("dev.mixer.android.NativeRenderer")&&frame.methodName().equals(method));}
    private static void write(StringBuilder out,Object value){if(value instanceof List<?> values){out.append('[');for(int i=0;i<values.size();i++){if(i>0)out.append(',');write(out,values.get(i));}out.append(']');}else if(value instanceof Map<?,?> values){out.append('{');boolean comma=false;for(var entry:values.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,entry.getKey());out.append(':');write(out,entry.getValue());}out.append('}');}else Json.write(out,value);}
    private static Object field(String id,String value){return Json.map("id",id,"kind","textField","properties",Json.map("label",id,"value",value),"children",List.of(),"actions",List.of(Json.map("id",id+"Changed","event","textChange")));}
    private static byte[] packet(long revision,String active){Object root=Json.map("id","root","kind","vStack","properties",Json.map(),"children",List.of(field("alpha","alpha"),field("gamma","gamma"),field("beta",active)),"actions",List.of());StringBuilder out=new StringBuilder();write(out,Json.map("schemaVersion",new Json.Num("1"),"document",Json.map("schemaVersion",new Json.Num("1"),"revision",new Json.Num(Long.toString(revision)),"root",root),"identities",List.of(Json.map("id","root","generation",new Json.Num("1")),Json.map("id","alpha","generation",new Json.Num("2")),Json.map("id","gamma","generation",new Json.Num("3")),Json.map("id","beta","generation",new Json.Num("4")))));return out.toString().getBytes(StandardCharsets.UTF_8);}
    private static final class Fatal extends Error {private static final long serialVersionUID=1L;Fatal(String label){super(label);}}
    private static final class Fixture implements AutoCloseable {
        final Activity activity=new Activity();final FrameLayout root=new FrameLayout(activity);final NativeOwnerV2 owner;final NativeCoordinatorV2 coordinator;final Handler queue;final NativeRenderer renderer;
        final NativeAppearanceViewsV2.NativeField a,c,b;InputConnection oldA,oldC,liveB;BaseInputConnection targetA,targetC,targetB;
        Fixture(boolean history,boolean active){ConcreteHostProbe.reset();NativeBridge.reset();activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);root.hostAttach(new Object());NativeBridge.preparedPacket=packet(1,"beta");owner=new NativeOwnerV2(activity,root);queue=(Handler)get(owner,"handler");owner.onResume();owner.start();queue.drainAll(6);check(owner.hasCommittedPresentation(),"complete owner initial presentation");coordinator=(NativeCoordinatorV2)get(owner,"coordinator");renderer=(NativeRenderer)get(coordinator,"renderer");a=(NativeAppearanceViewsV2.NativeField)renderer.view("alpha");c=(NativeAppearanceViewsV2.NativeField)renderer.view("gamma");b=(NativeAppearanceViewsV2.NativeField)renderer.view("beta");
            if(history){oldA=connect(a);targetA=(BaseInputConnection)a.lastConnection;check(oldA.setSelection(1,4),"A distinct selection before actual blur");Object spanA=new Object();a.getText().setSpan(spanA,1,3,Spanned.SPAN_COMPOSING|Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);a.clearFocus();check(targetA.closeCalls==1&&!oldA.beginBatchEdit(),"A exact settled close");oldC=connect(c);targetC=(BaseInputConnection)c.lastConnection;check(oldC.setSelection(2,3),"C distinct selection before actual blur");Object spanC=new Object();c.getText().setSpan(spanC,2,4,Spanned.SPAN_COMPOSING|Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);c.clearFocus();check(targetC.closeCalls==1&&!oldC.beginBatchEdit(),"C exact settled close");}
            if(active){liveB=connect(b);targetB=(BaseInputConnection)b.lastConnection;check(liveB.setSelection(4,4),"B explicit end cursor");}ConcreteHostProbe.reset();
        }
        InputConnection connect(NativeAppearanceViewsV2.NativeField field){field.requestFocus();InputConnection result=field.onCreateInputConnection(new EditorInfo());check(result!=null,"real admitted native adapter");return result;}
        NativeOwnerV2.Fence fence(){return (NativeOwnerV2.Fence)get(owner,"fence");}
        int count(){return (Integer)get(renderer,"outstandingEditorNativeCalls");}
        boolean edit(){NativeBridge.preparedPacket=packet(2,"betaz");return liveB.commitText("z",1);}
        @Override public void close(){ConcreteHostProbe.hook=null;try{owner.close();queue.drainAll(8);}catch(RuntimeException|Error expected){/* assertion precedes bounded fixture teardown */}ConcreteHostProbe.reset();}
    }
    private static final class Observation {
        final Fixture f;final NativeAppearanceViewsV2.FieldPreservation[] scopes=new NativeAppearanceViewsV2.FieldPreservation[2];final Object ea,ec,ba,bc,ga,gc;final NativeAppearanceViewsV2.EditorSnapshot sa,sc;
        final List<String> trace=new ArrayList<>();boolean captured,atCommit,afterFinish;int setters,restores,intervalCalls;NativeRenderer.Candidate candidate;NativeRenderer.AttachmentJournal journal;
        Observation(Fixture f){this.f=f;ea=f.a.getText();ec=f.c.getText();ba=f.a.record.binding;bc=f.c.record.binding;ga=f.a.record.geometry;gc=f.c.record.geometry;sa=new NativeAppearanceViewsV2.EditorSnapshot(f.a,f.a.getText());sc=new NativeAppearanceViewsV2.EditorSnapshot(f.c,f.c.getText());}
        void event(String method,String phase){Object receiver=ConcreteHostProbe.lastEvent().receiver;
            if(captured&&in("finishV2"))intervalCalls++;
            if((receiver==f.a||receiver==f.c)&&method.equals("TextView.setText")&&phase.equals("entry"))setters++;
            if(!captured&&receiver==f.a&&method.equals("View.invalidate")&&phase.equals("entry")&&f.a.record.fieldPreservation!=null){captured=true;scopes[0]=f.a.record.fieldPreservation;scopes[1]=f.c.record.fieldPreservation;candidate=scopes[0].candidate;journal=scopes[0].journal;trace.add("forward:"+f.count());check(scopes[1]!=null&&scopes[0]!=scopes[1],"separate exact A/C scopes");check(scopes[0].original==scopes[1].original&&scopes[0].original==get(candidate,"originalMutation")&&scopes[0].candidate==scopes[1].candidate&&scopes[0].journal==scopes[1].journal,"same original object/candidate/journal");check(f.count()==(f.liveB==null?2:3),"exact independent holds plus real B lease");check(f.liveB==null||f.b.record.editorCallbackLease!=null,"B actual EditorLease remains entered");for(var scope:scopes){try{scope.continuation().requireMutation();throw new AssertionError("field continuation mutated transaction");}catch(IllegalStateException expected){check(scope.counted,"target-free field continuation refuses transaction mutation");}}}
            if(captured&&(receiver==f.a||receiver==f.c)&&method.equals("View.invalidate")&&phase.equals("entry")&&in("restoreV2")){restores++;trace.add("restore:"+f.count());var scope=receiver==f.a?scopes[0]:scopes[1];check((receiver==f.a?f.a:f.c).record.fieldPreservation==scope&&!scope.ended&&scope.original==get(candidate,"originalMutation"),"restoration under same unended original scope");}
            if(captured&&method.equals("NativeBridge.commitV2")&&phase.equals("entry")){atCommit=true;trace.add("commit:"+f.count());for(var scope:scopes)check(!scope.ended&&scope.counted&&scope.phase==NativeAppearanceViewsV2.FieldPreservation.PRECOMMIT_READY,"unended scope held and prevalidated at actual commit");check(f.count()==3,"commit count three");}
            if(captured&&method.equals("NativeBridge.abortV2")&&phase.equals("entry")){trace.add("abort:"+f.count());check(f.count()==3,"abort remains fully held");}
            if(captured&&method.equals("Handler.post")&&phase.equals("entry")&&get(journal,"completion").equals(NativeRenderer.AttachmentJournal.FAILED_IN_PROGRESS)){trace.add("report:"+f.count());check(f.count()>=2,"report before count release");}
            if(captured&&!afterFinish&&get(journal,"completion").equals(NativeRenderer.AttachmentJournal.SUCCESS_DONE)){afterFinish=true;trace.add("after-finish:"+f.count());check(f.count()==(f.liveB==null?0:1),"scalar finish releases only A/C");for(var scope:scopes)check(scope.ended&&scope.released&&!scope.counted&&scope.record.fieldPreservation==null,"scope ended/unregistered/released at scalar finish");check(f.liveB==null||f.b.record.editorCallbackLease!=null,"same B lease remains after finish");}
        }
        void snapshots(){check(f.a.getText()==ea&&f.c.getText()==ec&&sa.same(f.a,f.a.getText())&&sc.same(f.c,f.c.getText())&&setters==0,"exact final inactive snapshots and no text setter");check(f.targetA.closeCalls==1&&f.targetC.closeCalls==1&&!f.oldA.beginBatchEdit()&&!f.oldC.beginBatchEdit()&&f.a.onCreateInputConnection(new EditorInfo())==null&&f.c.onCreateInputConnection(new EditorInfo())==null,"predecessors closed once and no fresh unfocused target");}
    }
    private static void outcome(String mode){try(Fixture f=new Fixture(true,true)){
        Observation o=new Observation(f);Fatal commitFatal=new Fatal("commit fatal"),abortFatal=new Fatal("abort fatal");
        int status=switch(mode){case "success"->0;case "terminal"->2;case "unknown"->8;case "reject3"->3;case "reject4"->4;case "reject5"->5;case "reject6"->6;case "reject7"->7;default->1;};NativeBridge.commitStatus=status;
        if(mode.equals("commit-throw"))NativeBridge.commitFailure=new IllegalStateException("commit throw");if(mode.equals("commit-fatal"))NativeBridge.commitFailure=commitFatal;
        if(mode.equals("abort-nonzero"))NativeBridge.abortStatus=1;if(mode.equals("abort-throw"))NativeBridge.abortFailure=new IllegalStateException("abort throw");if(mode.equals("abort-fatal"))NativeBridge.abortFailure=abortFatal;
        ConcreteHostProbe.hook=o::event;Throwable escaped=null;boolean returned=false;try{returned=f.edit();}catch(RuntimeException|Error failure){escaped=failure;}ConcreteHostProbe.hook=null;
        check(o.captured&&o.atCommit,"real three-field path entered actual commit");check(f.count()==0&&!f.renderer.editorDisposalBusyV2(),"all balanced A/C/B holds released after outcome");for(var scope:o.scopes)check(scope.ended&&!scope.counted&&scope.released&&scope.record.fieldPreservation==null,"exact completed scope disposition");
        boolean restore=status>=1&&status<=7&&status!=2&&!mode.startsWith("abort-")&&!mode.startsWith("commit-");
        if(restore){check(f.coordinator.cleanupLedger().rollback()==NativeCoordinatorV2.Outcome.RETURNED&&f.a.record.binding==o.ba&&f.c.record.binding==o.bc&&f.a.record.geometry==o.ga&&f.c.record.geometry==o.gc&&o.restores==2,"eligible known rejection restores both exact Binding and geometry");}
        else check(o.restores==0,"unknown/terminal/abort failure does not obtain native restoration");
        if(mode.equals("success")){check(returned&&!f.fence().terminal&&o.afterFinish&&o.intervalCalls==0,"successful scalar completion with no host native interval calls");check(f.targetB.closeCalls==0,"B target retained on ordinary success");}
        else check(!returned&&f.fence().terminal,"existing rejection/unknown retirement policy");
        if(mode.equals("commit-fatal"))check(escaped==commitFatal,"commit fatal preserved by identity");if(mode.equals("abort-fatal"))check(escaped==abortFatal,"abort fatal preserved by identity");
        o.snapshots();System.out.println("OUTCOME "+mode+" "+o.trace+" final="+f.count()+" escaped="+escaped);
        int count=f.count();int calls=ConcreteHostProbe.events().size();try{f.renderer.completeFailedV2(o.candidate,null,null);throw new AssertionError("completed failed endpoint replay");}catch(IllegalArgumentException expected){check(f.count()==count&&ConcreteHostProbe.events().size()==calls,"completed success/failure endpoint replay inert");}
        try{f.renderer.finishV2(o.candidate,o.journal);throw new AssertionError("finish replay");}catch(IllegalArgumentException expected){check(f.count()==count,"successful finish replay inert");}
    }}
    private static void refresh(){try(Fixture f=new Fixture(true,false)){
        Observation o=new Observation(f);ConcreteHostProbe.hook=o::event;int engine=NativeBridge.commitCalls;f.root.layout(0,0,1001,1501);f.queue.drainAll(8);ConcreteHostProbe.hook=null;
        if(o.captured&&get(o.journal,"completion").equals(NativeRenderer.AttachmentJournal.SUCCESS_DONE)){o.afterFinish=true;o.trace.add("outer-refresh-finish:"+f.count());for(var scope:o.scopes)check(scope.ended&&scope.released&&!scope.counted&&scope.record.fieldPreservation==null,"refresh exact scalar released disposition");}
        System.out.println("REFRESH_OBSERVATION captured="+o.captured+" after="+o.afterFinish+" terminal="+f.fence().terminal+" count="+f.count()+" primary="+f.renderer.cleanupLedger().primary()+" owner="+f.owner.cleanupLedger().primary()+" trace="+o.trace);
        check(o.captured&&o.afterFinish&&!o.atCommit&&NativeBridge.commitCalls==engine&&!f.fence().terminal&&f.count()==0,"refresh holds two fields then scalar finish reaches zero without synthetic engine commit");o.snapshots();System.out.println("REFRESH "+o.trace);
    }}
    private static void noScopes(){for(String mode:new String[]{"success","failure","refresh","pre-attach"})try(Fixture f=new Fixture(false,true)){
        final NativeRenderer.Candidate[] candidate={null};final boolean[] stopped={false};RuntimeException first=new IllegalStateException("pre-attach no-original");
        ConcreteHostProbe.hook=(method,phase)->{Object pending=get(f.renderer,"v2Pending");if(pending!=null){candidate[0]=(NativeRenderer.Candidate)pending;if(mode.equals("pre-attach")&&get(pending,"originalMutation")==null&&!stopped[0]){stopped[0]=true;throw first;}}};
        if(mode.equals("failure"))NativeBridge.commitStatus=1;
        Throwable escaped=null;try{if(mode.equals("refresh")){f.root.layout(0,0,1001,1501);f.queue.drainAll(8);}else f.edit();}catch(RuntimeException|Error failure){escaped=failure;}ConcreteHostProbe.hook=null;
        check(candidate[0]!=null&&f.count()==0,"no-preservation completion fabricates no holds");Object journal=get(candidate[0],"journal");check((Integer)get(candidate[0],"heldPreservations")==0,"no-preservation cohort remains zero");
        if(mode.equals("pre-attach"))check(stopped[0]&&get(candidate[0],"originalMutation")==null&&(Boolean)get(journal,"failedInvoked"),"pre-attach no-original failed endpoint consumed once without scope");
        else if(mode.equals("success")||mode.equals("refresh"))check(get(journal,"completion").equals(NativeRenderer.AttachmentJournal.SUCCESS_DONE),"no-preservation successful completion");
        else check((Boolean)get(journal,"failedInvoked"),"no-preservation rejection completed");
        System.out.println("NO_SCOPE "+mode+" original="+get(candidate[0],"originalMutation")+" escaped="+escaped);
    }}
    private static void partialEntry(){for(String mode:new String[]{"before-first","constructor-first","constructor-second","begin-first","begin-second"})try(Fixture f=new Fixture(true,true)){
        boolean[] injected={false};NativeRenderer.Candidate[] candidate={null};NativeAppearanceViewsV2.FieldPreservation[] firstScope={null};Object[] borrowed={null};Fatal first=new Fatal("attach before returned journal");
        ConcreteHostProbe.hook=(method,phase)->{Object pending=get(f.renderer,"v2Pending");if(pending!=null)candidate[0]=(NativeRenderer.Candidate)pending;
            if(!injected[0]&&pending!=null&&in("beginFieldPreservationsV2")&&phase.equals("beforeReturn")&&method.equals("TextView.getText")&&ConcreteHostProbe.lastEvent().receiver==(mode.endsWith("second")?f.c:f.a)&&f.a.record.fieldPreservation==(mode.endsWith("second")?f.a.record.fieldPreservation:null)&&get(pending,"originalMutation")!=null){
                if(mode.endsWith("second")&&f.a.record.fieldPreservation==null)return;injected[0]=true;firstScope[0]=f.a.record.fieldPreservation;
                if(mode.equals("before-first"))throw first;
                if(mode.startsWith("constructor"))put(f.renderer,"editorLossSerial",Long.MAX_VALUE);
                else{NativeAppearanceViewsV2.Record record=mode.endsWith("second")?f.c.record:f.a.record;borrowed[0]=record;record.editorCallbackLease=f.b.record.editorCallbackLease;}
            }
        };
        Throwable escaped=null;try{f.edit();}catch(RuntimeException|Error failure){escaped=failure;}ConcreteHostProbe.hook=null;
        check(injected[0]&&candidate[0]!=null,"actual attach failed before caller journal assignment");check((Boolean)get(get(candidate[0],"journal"),"failedInvoked"),"immutable candidate journal completed despite caller local absence");check(f.count()==0&&NativeBridge.commitCalls==1,"only actually entered own holds release; no second engine commit");
        var scope=mode.endsWith("second")?f.c.record.fieldPreservation:f.a.record.fieldPreservation;check(scope==null,"unentered exact registration revoked");
        if(mode.startsWith("begin")){NativeAppearanceViewsV2.Record record=(NativeAppearanceViewsV2.Record)borrowed[0];check(get(record.view,"primary")==null,"CAPTURED Begin refusal adds no native-prefix field error");record.editorCallbackLease=null;System.out.println("HOSTILE_REPAIR removed deliberately borrowed callback lease only");}
        if(mode.endsWith("second"))check(firstScope[0]!=null&&firstScope[0].entered&&firstScope[0].ended&&firstScope[0].released&&!firstScope[0].counted,"entered A before refused C releases once");
        if(mode.equals("before-first"))check(escaped==first,"first attach fatal transported before later abort");System.out.println("PARTIAL_ENTRY "+mode+" count="+f.count()+" escaped="+escaped);
    }}
    private static String state(Fixture f,NativeAppearanceViewsV2.FieldPreservation scope){return f.count()+":"+scope.entered+":"+scope.counted+":"+scope.ended+":"+scope.released+":"+scope.phase+":"+scope.callbacks+":"+(scope.record.fieldPreservation==scope)+":"+get(scope.candidate,"heldPreservations")+":"+get(scope.journal,"completion")+":"+get(scope.journal,"failedInvoked");}
    private static void partialRelease(){try(Fixture f=new Fixture(true,true)){
        Observation o=new Observation(f);boolean[] injected={false};ConcreteHostProbe.hook=(method,phase)->{var entry=ConcreteHostProbe.lastEvent();o.event(method,phase);if(o.captured&&!injected[0]&&method.equals("NativeBridge.commitV2")&&phase.equals("beforeReturn")){injected[0]=true;var released=o.scopes[0];released.record.fieldPreservation=null;released.ended=true;released.counted=false;released.released=true;released.phase=NativeAppearanceViewsV2.FieldPreservation.COMMITTED;put(o.candidate,"heldPreservations",1);put(f.renderer,"outstandingFieldPreservations",1);put(f.renderer,"outstandingEditorNativeCalls",2);put(o.journal,"completion",NativeRenderer.AttachmentJournal.SUCCESS_IN_PROGRESS);throw new IllegalStateException("hostile partial-success-state fixture");}};
        try{f.edit();}catch(RuntimeException expected){check(true,"hostile state transports failure");}ConcreteHostProbe.hook=null;
        check(injected[0]&&o.scopes[0].released&&!o.scopes[0].counted&&o.scopes[1].released&&!o.scopes[1].counted&&f.count()==0,"first failed endpoint releases only remaining exact count; no double decrement");check((Boolean)get(o.journal,"failedInvoked"),"success progress did not consume failed invocation claim");String before=state(f,o.scopes[1]);try{f.renderer.completeFailedV2(o.candidate,null,null);throw new AssertionError("failed replay");}catch(IllegalArgumentException expected){check(before.equals(state(f,o.scopes[1])),"true failed replay inert");}System.out.println("HOSTILE_PARTIAL_RELEASE direct scalar fixture, not an ordinary synchronous failure boundary");
    }}
    private static void chronology(){for(boolean imbalance:new boolean[]{false,true})try(Fixture f=new Fixture(true,true)){
        Observation o=new Observation(f);Fatal first=new Fatal("F native"),restore=new Fatal("G restoration/report"),abort=new Fatal("H later abort/report");boolean[] injected={false},g={false},h={false},busy={false};
        ConcreteHostProbe.hook=(method,phase)->{var entry=ConcreteHostProbe.lastEvent();o.event(method,phase);if(o.captured&&!injected[0]&&entry.receiver==f.a&&method.equals("View.invalidate")&&phase.equals("entry")&&!in("restoreV2")){injected[0]=true;if(imbalance)o.scopes[0].callbacks=1;throw first;}
            if(injected[0]&&!g[0]&&((in("restoreV2")&&method.equals("View.invalidate")&&phase.equals("entry"))||(method.equals("Handler.post")&&phase.equals("entry")))){g[0]=true;busy[0]|=f.count()==3;throw restore;}
            if(injected[0]&&method.equals("NativeBridge.abortV2")&&phase.equals("entry")){h[0]=true;check(f.count()==3,"abort H after F/G still fully held");throw abort;}
        };Throwable escaped=null;try{f.edit();}catch(RuntimeException|Error failure){escaped=failure;}ConcreteHostProbe.hook=null;
        System.out.println("CHRONOLOGY_OBSERVATION imbalance="+imbalance+" F="+injected[0]+" G="+g[0]+" H="+h[0]+" busy="+busy[0]+" escaped="+escaped+" rendererFatal="+f.renderer.cleanupLedger().firstFatal()+" coordinatorFatal="+f.coordinator.cleanupLedger().firstFatal()+" count="+f.count()+" trace="+o.trace);
        check(injected[0]&&g[0]&&h[0]&&busy[0]&&escaped==first,"chronology F before restoration/report G before abort H by identity");check(f.renderer.cleanupLedger().firstFatal()==first&&f.coordinator.cleanupLedger().firstFatal()==first,"both renderer/coordinator retain actual first fatal");
        check(o.scopes[1].released&&!o.scopes[1].counted&&f.count()==(imbalance?1:0),"C and B release before F surfaces, only A imbalance may remain");check(f.a.record.fieldPreservation==null&&f.c.record.fieldPreservation==null,"no callback revival after failed completion");
        if(imbalance){check(o.scopes[0].counted&&f.renderer.editorDisposalBusyV2()&&NativeBridge.destroyCalls==0,"held A prevents disposal");String before=state(f,o.scopes[0]);try{f.renderer.completeFailedV2(o.candidate,null,null);throw new AssertionError("imbalance replay repair");}catch(IllegalArgumentException expected){check(before.equals(state(f,o.scopes[0])),"replay does not repair imbalance");}o.scopes[0].callbacks=0;f.a.record.input.fieldPreservationEnd(f.a.record,o.scopes[0]);System.out.println("HOSTILE_REPAIR balanced injected A callback count only for fixture teardown");}
        System.out.println("CHRONOLOGY imbalance="+imbalance+" escaped="+escaped+" trace="+o.trace);
    }}

    private static void refused(Runnable action,Fixture own,Fixture other,NativeAppearanceViewsV2.FieldPreservation scope,String label){
        String before=state(own,scope);int otherCount=other.count(),effects=ConcreteHostProbe.events().size();Object primary=own.renderer.cleanupLedger().primary();
        try{action.run();throw new AssertionError("accepted "+label);}catch(IllegalArgumentException|IllegalStateException expected){check(before.equals(state(own,scope))&&other.count()==otherCount&&ConcreteHostProbe.events().size()==effects&&own.renderer.cleanupLedger().primary()==primary,label+" refuses before endpoint effects on both owners");}
    }
    private static void foreignEndpoints(){try(Fixture f=new Fixture(true,true);Fixture other=new Fixture(true,true)){
        Observation foreign=new Observation(other);ConcreteHostProbe.hook=foreign::event;check(other.edit(),"second real owner prior complete candidate");ConcreteHostProbe.hook=null;
        Observation o=new Observation(f);boolean[] nativeMatrix={false},finishMatrix={false};
        ConcreteHostProbe.hook=(method,phase)->{var entry=ConcreteHostProbe.lastEvent();o.event(method,phase);
            boolean finish=o.captured&&method.equals("NativeBridge.commitV2")&&phase.equals("entry");
            if(o.captured&&((!nativeMatrix[0]&&entry.receiver==f.a&&method.equals("View.invalidate")&&phase.equals("entry"))||finish&&!finishMatrix[0])){
                if(finish)finishMatrix[0]=true;else nativeMatrix[0]=true;
                var scope=o.scopes[0];
                for(String identity:new String[]{"renderer","candidate","journal","record","view","input","original","fence","token","membership"}){
                    Object target;String member;Object wrong;
                    switch(identity){case "renderer"->{target=scope;member="renderer";wrong=other.renderer;}case "candidate"->{target=scope;member="candidate";wrong=foreign.candidate;}case "journal"->{target=scope;member="journal";wrong=foreign.journal;}case "record"->{target=scope;member="record";wrong=f.c.record;}case "view"->{target=f.a.record;member="view";wrong=f.c;}case "input"->{target=f.a.record;member="input";wrong=other.a.record.input;}case "original"->{target=o.candidate;member="originalMutation";wrong=foreign.scopes[0].original;}case "fence"->{target=scope.original;member="fence";wrong=other.fence();}case "token"->{target=scope.original;member="token";wrong=foreign.scopes[0].original.token;}default->{Object[] states=(Object[])get(o.journal,"states");target=null;for(Object state:states)if(get(state,"record")==f.a.record)target=state;member="preservation";wrong=foreign.scopes[0];}}
                    Object previous=get(target,member);NativeAppearanceViewsV2.Input input=f.a.record.input;put(target,member,wrong);
                    try{if(finish)refused(()->f.renderer.finishV2(o.candidate,o.journal),f,other,scope,"finish wrong "+identity);
                        else{refused(()->input.fieldPreservationBegin(f.a.record,scope),f,other,scope,"Begin wrong "+identity);refused(()->input.fieldPreservationEnd(f.a.record,scope),f,other,scope,"End wrong "+identity);refused(()->f.renderer.completeFailedV2(o.candidate,null,null),f,other,scope,"failed completion wrong "+identity);}}
                    finally{put(target,member,previous);}
                }
                refused(()->other.a.record.input.fieldPreservationEnd(f.a.record,scope),f,other,scope,"foreign receiving Input");
                refused(()->other.renderer.completeFailedV2(o.candidate,null,null),f,other,scope,"foreign receiving renderer");
                refused(()->f.renderer.finishV2(foreign.candidate,foreign.journal),f,other,scope,"foreign candidate and journal");
            }
        };
        check(f.edit(),"all foreign refusals preserve legitimate owner success");ConcreteHostProbe.hook=null;check(nativeMatrix[0]&&finishMatrix[0]&&f.count()==0&&other.count()==0,"actual callbacks and scalar interval tested with two complete owners");
    }}
    private static void terminalEnd(){try(Fixture f=new Fixture(true,true);Fixture other=new Fixture(true,true)){
        Observation o=new Observation(f);boolean[] injected={false};ConcreteHostProbe.hook=(method,phase)->{var entry=ConcreteHostProbe.lastEvent();o.event(method,phase);if(o.captured&&!injected[0]&&entry.receiver==f.a&&method.equals("View.invalidate")&&phase.equals("entry")){injected[0]=true;o.scopes[0].callbacks=1;throw new IllegalStateException("hold real A for direct terminal End tests");}};
        try{f.edit();}catch(RuntimeException expected){check(true,"terminal hold");}ConcreteHostProbe.hook=null;var scope=o.scopes[0];check(scope.ended&&scope.counted&&f.count()==1&&f.fence().operation==null,"held real A after operation loss");scope.callbacks=0;
        for(String identity:new String[]{"renderer","candidate","journal","record","view","input","original","fence","token","membership"}){
            Object target;String member;Object wrong;
            switch(identity){case "renderer"->{target=scope;member="renderer";wrong=other.renderer;}case "candidate"->{target=scope;member="candidate";wrong=null;}case "journal"->{target=scope;member="journal";wrong=null;}case "record"->{target=scope;member="record";wrong=f.c.record;}case "view"->{target=f.a.record;member="view";wrong=f.c;}case "input"->{target=f.a.record;member="input";wrong=other.a.record.input;}case "original"->{target=o.candidate;member="originalMutation";wrong=null;}case "fence"->{target=scope.original;member="fence";wrong=other.fence();}case "token"->{target=scope.original;member="token";wrong=null;}default->{Object[] states=(Object[])get(o.journal,"states");target=null;for(Object state:states)if(get(state,"record")==f.a.record)target=state;member="preservation";wrong=null;}}
            Object previous=get(target,member);NativeAppearanceViewsV2.Input input=f.a.record.input;put(target,member,wrong);
            try{String before=f.count()+":"+scope.counted+":"+scope.ended+":"+get(o.candidate,"heldPreservations");int effects=ConcreteHostProbe.events().size();try{input.fieldPreservationEnd(f.a.record,scope);throw new AssertionError("wrong terminal End "+identity);}catch(IllegalArgumentException expected){check(before.equals(f.count()+":"+scope.counted+":"+scope.ended+":"+get(o.candidate,"heldPreservations"))&&ConcreteHostProbe.events().size()==effects&&other.count()==0,"terminal End provenance "+identity);}}
            finally{put(target,member,previous);}
        }
        for(int count:new int[]{0,-1}){put(f.renderer,"outstandingEditorNativeCalls",count);int effects=ConcreteHostProbe.events().size();try{f.a.record.input.fieldPreservationEnd(f.a.record,scope);throw new AssertionError("unfunded terminal End");}catch(IllegalArgumentException expected){check(scope.counted&&f.count()==count&&f.renderer.editorDisposalBusyV2()&&ConcreteHostProbe.events().size()==effects,"unfunded terminal End retains independent custody");}put(f.renderer,"outstandingEditorNativeCalls",1);}
        int effects=ConcreteHostProbe.events().size();f.a.record.input.fieldPreservationEnd(f.a.record,scope);check(f.count()==0&&scope.released&&!scope.counted&&ConcreteHostProbe.events().size()==effects,"exact End after operation loss uses no current/native probe");
        try{f.a.record.input.fieldPreservationEnd(f.a.record,scope);throw new AssertionError("End replay");}catch(IllegalArgumentException expected){check(f.count()==0&&other.count()==0,"exact End replay leaves both owners unchanged");}
        System.out.println("HOSTILE_REPAIR balanced injected A callback counter before exact captured terminal End");
    }}
    private static void imbalances(){for(String kind:new String[]{"callbacks","hooks","checking","counted-not-entered","entered-not-counted","underfunded","negative","finish-mismatch","post-validation"})try(Fixture f=new Fixture(true,true)){
        Observation o=new Observation(f);boolean[] injected={false};
        ConcreteHostProbe.hook=(method,phase)->{var entry=ConcreteHostProbe.lastEvent();o.event(method,phase);
            if(o.captured&&!injected[0]&&(kind.equals("post-validation")?in("validateAttachedV2")&&method.equals("TextView.getEditableText")&&phase.equals("beforeReturn"):method.equals("NativeBridge.commitV2")&&phase.equals("beforeReturn"))){injected[0]=true;var scope=o.scopes[0];switch(kind){case "callbacks","finish-mismatch"->scope.callbacks=1;case "hooks"->scope.hooks.push("hostile");case "checking"->scope.checking=true;case "counted-not-entered"->scope.entered=false;case "entered-not-counted"->scope.counted=false;case "underfunded"->put(f.renderer,"outstandingEditorNativeCalls",1);case "negative"->put(f.renderer,"outstandingEditorNativeCalls",-1);default->put(f.renderer,"editorLossSerial",scope.lossObservation+1);}}
        };try{f.edit();}catch(RuntimeException|Error expected){check(true,"mismatched completion refused");}ConcreteHostProbe.hook=null;
        check(injected[0]&&f.fence().terminal&&o.scopes[0].ended&&o.scopes[1].ended&&f.a.record.fieldPreservation==null&&f.c.record.fieldPreservation==null,"invalid completion is terminal without callback authority");
        if(kind.equals("post-validation")){check(!o.atCommit&&f.count()==0&&o.scopes[0].released&&o.scopes[1].released,"postvalidation authority loss cleans balanced holds outside commit");}
        else if(kind.equals("underfunded")||kind.equals("negative")){check(o.scopes[0].counted&&o.scopes[1].counted&&!o.scopes[0].released&&!o.scopes[1].released&&f.renderer.editorDisposalBusyV2()&&NativeBridge.destroyCalls==0,"underfunded cohort cannot borrow B or become disposal-ready");}
        else check(!o.scopes[0].released&&o.scopes[1].released&&!o.scopes[1].counted&&f.count()==1&&f.renderer.editorDisposalBusyV2()&&NativeBridge.destroyCalls==0,"one inconsistent scope retains exact custody while C and B release");
        String before=state(f,o.scopes[0]);try{f.renderer.completeFailedV2(o.candidate,null,null);throw new AssertionError("repair by replay");}catch(IllegalArgumentException expected){check(before.equals(state(f,o.scopes[0])),"imbalanced failure replay inert");}
        System.out.println("IMBALANCE "+kind+" shared="+f.count()+" preservation="+get(f.renderer,"outstandingFieldPreservations")+" custody="+get(o.candidate,"heldPreservations")+" no repair/retry");
    }}
    public static void main(String[] args)throws Exception{descriptor=Files.readAllBytes(Path.of(args[1]));switch(args[0]){case "outcomes"->{for(String mode:new String[]{"success","reject1","reject3","reject4","reject5","reject6","reject7","terminal","unknown","commit-throw","commit-fatal","abort-nonzero","abort-throw","abort-fatal"})outcome(mode);}case "refresh"->refresh();case "no-scopes"->noScopes();case "partial-entry"->partialEntry();case "partial-release"->partialRelease();case "chronology"->chronology();case "foreign-endpoints"->foreignEndpoints();case "terminal-end"->terminalEnd();case "imbalances"->imbalances();default->throw new IllegalArgumentException(args[0]);}System.out.println("PASS preservation-completion "+args[0]+" / "+checks+" assertions; host only");}
}
