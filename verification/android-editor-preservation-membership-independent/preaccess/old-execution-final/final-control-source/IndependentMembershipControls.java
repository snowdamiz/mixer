package dev.mixer.android;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.lang.reflect.Modifier;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Bounded private-state invariant controls, prepared before correction access.
 * Reuses only the frozen unchanged witness's real three-field fixture. New
 * adversarial steps and oracles below do not assume correction member names.
 * No ordinary reachability, Android runtime or arbitrary memory defense claim.
 */
public final class IndependentMembershipControls {
    private IndependentMembershipControls() {}
    private static int assertions;
    private static final List<String> trace = new ArrayList<>();
    private static void check(boolean value, String why) {
        assertions++;
        if (!value) throw new AssertionError(why + " trace=" + trace);
    }
    private static Field field(Object object, String name) {
        try { Field f = object.getClass().getDeclaredField(name); f.setAccessible(true); return f; }
        catch (ReflectiveOperationException e) { throw new AssertionError("frozen fixture contract: " + name, e); }
    }
    private static Object get(Object object, String name) {
        try { return field(object, name).get(object); } catch (IllegalAccessException e) { throw new AssertionError(e); }
    }
    private static void put(Object object, String name, Object value) {
        try { field(object, name).set(object, value); } catch (IllegalAccessException e) { throw new AssertionError(e); }
    }
    private static Object call(Object object, String name, Object... args) {
        for (Method m : object.getClass().getDeclaredMethods()) {
            if (!m.getName().equals(name) || m.getParameterCount() != args.length) continue;
            try { m.setAccessible(true); return m.invoke(object, args); }
            catch (InvocationTargetException e) {
                if (e.getCause() instanceof Error fatal) throw fatal;
                if (e.getCause() instanceof RuntimeException ordinary) throw ordinary;
                throw new AssertionError(e.getCause());
            } catch (ReflectiveOperationException e) { throw new AssertionError(e); }
        }
        throw new AssertionError("missing selected endpoint " + name);
    }
    private static int count(Object object, String name) { return (Integer) get(object, name); }
    private static boolean flag(Object object, String name) { return (Boolean) get(object, name); }
    private static boolean frame(String name) { return ConcreteHostProbe.lastEvent().productionFrames.stream().anyMatch(f -> f.methodName().equals(name)); }
    private static final class Fixture implements AutoCloseable {
        final Object delegate;
        final NativeRenderer renderer;
        final NativeAppearanceViewsV2.NativeField a, b, c;
        final NativeOwnerV2.Fence fence;
        Fixture(boolean history) {
            try {
                Class<?> type = Class.forName("dev.mixer.android.IndependentPreservationCompletionControls$Fixture");
                Constructor<?> constructor = type.getDeclaredConstructor(boolean.class, boolean.class); constructor.setAccessible(true);
                delegate = constructor.newInstance(history, true);
            } catch (ReflectiveOperationException e) { throw new AssertionError("unchanged frozen fixture failed", e); }
            renderer = (NativeRenderer) get(delegate, "renderer"); a = (NativeAppearanceViewsV2.NativeField) get(delegate, "a");
            b = (NativeAppearanceViewsV2.NativeField) get(delegate, "b"); c = (NativeAppearanceViewsV2.NativeField) get(delegate, "c");
            fence = (NativeOwnerV2.Fence) get(delegate, "fence");
        }
        boolean edit() { return (Boolean) call(delegate, "edit"); }
        @Override public void close() { call(delegate, "close"); }
    }
    private static final class Snapshot {
        final IdentityHashMap<Object, Map<Field,Object>> objects = new IdentityHashMap<>();
        final IdentityHashMap<Object,Object[]> arrays = new IdentityHashMap<>();
        Snapshot(Object... selected) {
            for (Object object : selected) {
                if (object == null || objects.containsKey(object)) continue;
                Map<Field,Object> values = new LinkedHashMap<>();
                for (Field f : object.getClass().getDeclaredFields()) if (!Modifier.isStatic(f.getModifiers())) {
                    try { f.setAccessible(true); Object value=f.get(object); values.put(f,value); if(value instanceof Object[] a) arrays.put(a,a.clone()); }
                    catch (IllegalAccessException e) { throw new AssertionError(e); }
                }
                objects.put(object,values);
            }
        }
        void unchanged() {
            for (var object : objects.entrySet()) for (var value : object.getValue().entrySet()) {
                Object actual;
                try { actual=value.getKey().get(object.getKey()); } catch(IllegalAccessException e){throw new AssertionError(e);}
                check(value.getKey().getType().isPrimitive()?value.getValue().equals(actual):value.getValue()==actual,
                    "reentry/replay preserves "+object.getKey().getClass().getSimpleName()+"."+value.getKey().getName());
            }
            for(var a:arrays.entrySet()) check(Arrays.equals((Object[])a.getKey(),a.getValue()),"reentry/replay preserves exact ordered array elements");
        }
    }
    private static void refused(Runnable action,Object... objects) {
        Snapshot before=new Snapshot(objects);int events=ConcreteHostProbe.events().size();boolean refused=false;
        try{action.run();}catch(IllegalArgumentException|IllegalStateException expected){refused=true;}
        check(refused,"foreign/consumed/reentrant endpoint must refuse");before.unchanged();
        check(events==ConcreteHostProbe.events().size(),"refusal precedes platform/native effect");
    }
    private static final class Track {
        final Fixture f;final boolean history;
        Object candidate,journal,aState,cState;
        Object[] originalStates;
        NativeAppearanceViewsV2.FieldPreservation aScope,cScope;
        Object originalPacket,originalRecords;
        boolean commit,injected;
        Track(Fixture f,boolean history){this.f=f;this.history=history;}
        void capture() {
            if(candidate!=null)return;Object pending=get(f.renderer,"v2Pending");if(pending==null)return;
            if(history&&(f.a.record.fieldPreservation==null||f.c.record.fieldPreservation==null))return;
            candidate=pending;journal=get(candidate,"journal");originalStates=((Object[])get(journal,"states")).clone();
            for(Object state:originalStates){Object record=get(state,"record");if(record==f.a.record)aState=state;if(record==f.c.record)cState=state;}
            check(aState!=null&&cState!=null&&aState!=cState,"actual distinct constructor states for A/C");
            aScope=f.a.record.fieldPreservation;cScope=f.c.record.fieldPreservation;
            if(history)check(aScope!=null&&cScope!=null&&aScope!=cScope&&aScope.entered&&cScope.entered&&aScope.counted&&cScope.counted,"both genuine A/C native holds already entered");
            else check(aScope==null&&cScope==null,"ordinary no-history candidate has no fabricated scopes");
            originalPacket=get(f.renderer,"packet");originalRecords=get(f.renderer,"v2Records");
        }
        void observe(String method,String phase){
            if(history){if(method.equals("View.invalidate")&&phase.equals("entry")&&ConcreteHostProbe.lastEvent().receiver==f.a)capture();}
            else if(method.equals("NativeBridge.commitV2")&&phase.equals("entry"))capture();
            if(method.equals("NativeBridge.commitV2")&&phase.equals("entry")){
                commit=true;check(candidate!=null&&count(f.renderer,"outstandingEditorNativeCalls")== (history?3:1),"real engine commit holds exact A/C plus real B lease");
            }
        }
        Object[] watched(){return new Object[]{f.renderer,candidate,journal,aScope,cScope,f.a.record,f.c.record};}
        void retained(String boundary){
            check(!flag(candidate,"used")&&!flag(journal,"complete"),boundary+": no success candidate consumption");
            check(get(f.renderer,"packet")==originalPacket&&get(f.renderer,"v2Records")==originalRecords,boundary+": no success presentation swap");
            if(history){
                check(aScope.counted&&cScope.counted&&!aScope.released&&!cScope.released,boundary+": retain both original unproven claims");
                check(count(candidate,"heldPreservations")==2&&count(f.renderer,"outstandingFieldPreservations")==2,boundary+": exact original preservation tallies retained");
            }
        }
        void terminalResult(boolean returned){
            check(injected&&commit&&!returned&&f.fence.terminal,"actual malformed membership refuses success and seals operation");
            check(count(journal,"completion")==4&&flag(journal,"failedInvoked"),"own malformed roster consumes failed endpoint and reaches FAILED_DONE once");
            retained("post unwind");
            check(count(f.renderer,"outstandingEditorNativeCalls")== (history?2:0),"only real B lease unwound; no ledger repair");
            if(history)check(f.renderer.editorDisposalBusyV2()&&NativeBridge.destroyCalls==0,"unproven custody remains busy and undestroyed");
            check(get(call(get(f.delegate,"coordinator"),"cleanupLedger"),"rollback").toString().equals("NOT_REQUESTED"),"successful engine commit plus hostile private membership is not fabricated rollback");
            refused(()->call(f.renderer,"completeFailedV2",candidate,null,null),watched());
            refused(()->call(f.renderer,"finishV2",candidate,journal),watched());
        }
    }
    private static int index(Object[] states,Object state){for(int i=0;i<states.length;i++)if(states[i]==state)return i;throw new AssertionError("missing state");}
    private static NativeAppearanceViewsV2.FieldPreservation cloneScope(NativeAppearanceViewsV2.FieldPreservation old) {
        // Explicit hostile private substitution; it acquires no actual native count.
        var clone=new NativeAppearanceViewsV2.FieldPreservation(old.field,old.original,old.selected,old.editable,old.renderer,old.candidate,old.journal);
        for(Field f:old.getClass().getDeclaredFields())if(!Modifier.isStatic(f.getModifiers())&&!Modifier.isFinal(f.getModifiers()))try{f.setAccessible(true);f.set(clone,f.get(old));}catch(IllegalAccessException e){throw new AssertionError(e);}
        return clone;
    }
    private static void mutate(Track t,String mode,Object foreign){
        Object[] states=(Object[])get(t.journal,"states");int a=index(states,t.aState),c=index(states,t.cState);
        switch(mode){
            case "duplicate" -> states[c]=t.aState;
            case "swap" -> {states[a]=t.cState;states[c]=t.aState;}
            case "null" -> states[c]=null;
            case "foreign" -> states[c]=foreign;
            case "size-short" -> put(t.journal,"stateCount",states.length-1);
            case "size-long" -> put(t.journal,"stateCount",states.length+1);
            case "size-negative" -> put(t.journal,"stateCount",-1);
            case "scope-null" -> put(t.cState,"preservation",null);
            case "scope-clone" -> {var clone=cloneScope(t.cScope);put(t.cState,"preservation",clone);t.f.c.record.fieldPreservation=clone;}
            case "forward-clear" -> put(t.cState,"forwardPreserved",false);
            default -> throw new AssertionError(mode);
        }
        t.injected=true;trace.add("private "+mode+" at existing commit beforeReturn");
    }
    private static Object foreignState(){
        try(Fixture foreign=new Fixture(false)){
            Object[] selected={null};ConcreteHostProbe.hook=(m,p)->{if(m.equals("NativeBridge.commitV2")&&p.equals("beforeReturn")){
                Object j=get(get(foreign.renderer,"v2Pending"),"journal");for(Object s:(Object[])get(j,"states"))if(get(s,"record")==foreign.c.record)selected[0]=s;
            }};
            check(foreign.edit()&&selected[0]!=null,"real distinct foreign constructor member available");ConcreteHostProbe.hook=null;return selected[0];
        }
    }
    private static void membership(String mode,boolean history){
        Object foreign=mode.equals("foreign")?foreignState():null;
        try(Fixture f=new Fixture(history)){
            Track t=new Track(f,history);boolean[] report={false};Object observer=get(f.renderer,"v2Environment");
            var original=(NativeEnvironmentV2.Sink)get(observer,"sink");
            NativeEnvironmentV2.Sink guarded=(source,change,cause,primary,fatal)->{
                if(t.injected&&!report[0]){report[0]=true;t.retained("first actual deferred reporter");check(count(f.renderer,"outstandingEditorNativeCalls")== (history?3:1),"whole-cohort refusal precedes any exact preservation count release");}
                original.changed(source,change,cause,primary,fatal);
            };
            put(observer,"sink",guarded);
            ConcreteHostProbe.hook=(m,p)->{t.observe(m,p);if(!t.injected&&t.commit&&m.equals("NativeBridge.commitV2")&&p.equals("beforeReturn"))mutate(t,mode,foreign);};
            boolean returned=false;Throwable escaped=null;try{returned=f.edit();}catch(RuntimeException|Error e){escaped=e;}finally{ConcreteHostProbe.hook=null;put(observer,"sink",original);}
            System.out.println("OBSERVATION mode="+mode+" history="+history+" returned="+returned+" escaped="+escaped+" terminal="+f.fence.terminal+" completion="+get(t.journal,"completion")+" shared="+count(f.renderer,"outstandingEditorNativeCalls")+" preservation="+count(f.renderer,"outstandingFieldPreservations"));
            check(report[0],"actual deferred reporter observes whole-cohort refusal before cleanup");t.terminalResult(returned);
        }
    }
    private static final class Fatal extends Error {private static final long serialVersionUID=1L;Fatal(String s){super(s);}}
    private static void reporterReentry(){
        try(Fixture f=new Fixture(true)){
            Track t=new Track(f,true);Fatal first=new Fatal("first original failed endpoint fatal"),later=new Fatal("later reporter fatal");
            boolean[] called={false},reported={false};Object observer=get(f.renderer,"v2Environment");var original=(NativeEnvironmentV2.Sink)get(observer,"sink");
            NativeEnvironmentV2.Sink reentrant=(source,change,cause,primary,fatal)->{
                if(called[0]&&!reported[0]){
                    reported[0]=true;check(flag(t.journal,"failedInvoked")&&count(t.journal,"completion")==3,"own failed endpoint claimed before actual reporter reentry");
                    check(get(get(f.renderer,"v2Cleanup"),"firstFatal")==first,"original fatal remembered before first reporter");t.retained("failed reporter reentry");
                    refused(()->call(f.renderer,"completeFailedV2",t.candidate,later,later),t.watched());
                    refused(()->call(f.renderer,"finishV2",t.candidate,t.journal),t.watched());
                    throw later;
                }
                original.changed(source,change,cause,primary,fatal);
            };
            put(observer,"sink",reentrant);
            ConcreteHostProbe.hook=(m,p)->{
                t.observe(m,p);if(!called[0]&&t.candidate!=null&&m.equals("View.invalidate")&&p.equals("entry")&&ConcreteHostProbe.lastEvent().receiver==f.a&&!frame("restoreV2")){
                    called[0]=true;mutate(t,"duplicate",null);call(f.renderer,"completeFailedV2",t.candidate,first,first);
                }
            };
            Throwable escaped=null;try{f.edit();}catch(RuntimeException|Error e){escaped=e;}finally{ConcreteHostProbe.hook=null;put(observer,"sink",original);}
            check(called[0]&&reported[0]&&escaped==first,"first fatal survives later actual reporter fatal by identity");
            check(count(t.journal,"completion")==4&&flag(t.journal,"failedInvoked"),"own malformed failed endpoint terminal after reporter");
            check(t.aScope.counted&&t.cScope.counted&&count(f.renderer,"outstandingFieldPreservations")==2&&count(f.renderer,"outstandingEditorNativeCalls")==2&&f.renderer.editorDisposalBusyV2(),"reentry retains both actual unproven holds after B unwind");
            refused(()->call(f.renderer,"completeFailedV2",t.candidate,first,first),t.watched());
        }
    }
    private static void healthy() {
        try(Fixture f=new Fixture(true)){
            Track t=new Track(f,true);boolean[] scalarObserved={false};
            ConcreteHostProbe.hook=(m,p)->{
                t.observe(m,p);
                if(t.commit&&!scalarObserved[0]&&!f.fence.commitFinish&&flag(t.candidate,"used")&&flag(t.journal,"complete")){
                    scalarObserved[0]=true;check(count(f.renderer,"outstandingEditorNativeCalls")==1,"healthy scalar finish leaves only genuine B lease");
                    check(t.aScope.released&&t.cScope.released&&!t.aScope.counted&&!t.cScope.counted,"healthy scalar finish releases exact A/C once");
                }
            };
            check(f.edit(),"healthy coordinator edit succeeds");ConcreteHostProbe.hook=null;
            check(t.commit&&scalarObserved[0]&&count(t.journal,"completion")==2,"healthy final source succeeds");
            check(count(f.renderer,"outstandingEditorNativeCalls")==0&&count(f.renderer,"outstandingFieldPreservations")==0&&count(t.candidate,"heldPreservations")==0,"healthy count3 to1 to0 with original tallies");
            check(f.a.record.fieldPreservation==null&&f.c.record.fieldPreservation==null&&!f.fence.terminal,"healthy exact registration release");
            refused(()->call(f.renderer,"completeFailedV2",t.candidate,null,null),t.watched());
        }
    }
    private static void capturedSubstitution(){
        try(Fixture f=new Fixture(true)){
            NativeAppearanceViewsV2.Input exact=f.a.record.input;
            Object[] candidate={null};NativeAppearanceViewsV2.FieldPreservation[] actual={null},substitute={null};boolean[] installed={false},refusal={false};
            ConcreteHostProbe.hook=(m,p)->{
                if(installed[0]||ConcreteHostProbe.lastEvent().receiver!=f.a||!frame("beginFieldPreservationsV2")||!frame("sameNativeBaseV2"))return;
                installed[0]=true;candidate[0]=get(f.renderer,"v2Pending");
                Object proxy=Proxy.newProxyInstance(NativeAppearanceViewsV2.Input.class.getClassLoader(),new Class<?>[]{NativeAppearanceViewsV2.Input.class},(receiver,method,args)->{
                    if(method.getName().equals("fieldPreservationBegin")){
                        put(f.a.record,"input",exact);actual[0]=(NativeAppearanceViewsV2.FieldPreservation)args[1];substitute[0]=cloneScope(actual[0]);
                        Object j=get(candidate[0],"journal");Object state=null;for(Object s:(Object[])get(j,"states"))if(get(s,"record")==f.a.record)state=s;
                        check(state!=null&&!actual[0].entered&&!actual[0].counted&&count(f.renderer,"outstandingEditorNativeCalls")==1,"real CAPTURED member exists before first Begin/count");
                        put(state,"preservation",substitute[0]);f.a.record.fieldPreservation=substitute[0];
                        try{exact.fieldPreservationBegin(f.a.record,substitute[0]);}catch(IllegalArgumentException|IllegalStateException expected){refusal[0]=true;}
                        check(refusal[0]&&!substitute[0].entered&&!substitute[0].counted&&!actual[0].entered&&!actual[0].counted&&count(f.renderer,"outstandingEditorNativeCalls")==1,"new equal-identity CAPTURED substitute cannot borrow original capture or acquire a count");
                        throw new IllegalStateException("bounded captured-substitution exit after asserted Begin refusal");
                    }
                    try{return method.invoke(exact,args);}catch(InvocationTargetException e){throw e.getCause();}
                });
                put(f.a.record,"input",proxy);
            };
            Throwable escaped=null;try{f.edit();}catch(RuntimeException|Error e){escaped=e;}finally{ConcreteHostProbe.hook=null;put(f.a.record,"input",exact);}
            check(!(escaped instanceof AssertionError),"CAPTURED substitution fixture assertion must surface");
            check(installed[0]&&refusal[0]&&actual[0]!=null&&substitute[0]!=actual[0],"captured substitution at real first Begin was refused");
            check(count(f.renderer,"outstandingEditorNativeCalls")==0&&count(f.renderer,"outstandingFieldPreservations")==0&&count(candidate[0],"heldPreservations")==0,"CAPTURED refusal manufactures no preservation ledger or release");
            check(count(get(candidate[0],"journal"),"completion")==4&&flag(get(candidate[0],"journal"),"failedInvoked"),"malformed CAPTURED roster still consumes own failure endpoint once");
            refused(()->call(f.renderer,"completeFailedV2",candidate[0],null,null),f.renderer,candidate[0],get(candidate[0],"journal"),actual[0],substitute[0],f.a.record);
        }
    }
    public static void main(String[] args)throws Exception{
        Field descriptor=IndependentPreservationCompletionControls.class.getDeclaredField("descriptor");descriptor.setAccessible(true);descriptor.set(null,Files.readAllBytes(Path.of(args[1])));
        String selected=args[0];
        if(selected.equals("healthy"))healthy();
        else if(selected.equals("captured-substitution"))capturedSubstitution();
        else if(selected.equals("reporter-reentry"))reporterReentry();
        else if(selected.startsWith("no-scope-"))membership(selected.substring(9),false);
        else membership(selected,true);
        System.out.println("PASS independent membership "+selected+" / "+assertions+" assertions; trace="+trace);
    }
}
