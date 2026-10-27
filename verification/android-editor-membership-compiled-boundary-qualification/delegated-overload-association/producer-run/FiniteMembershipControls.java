package dev.mixer.android;

import java.lang.invoke.MethodType;
import java.lang.reflect.Array;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collection;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Finite host controls only. Original fixture and exact product bytecode stay unchanged. */
public final class FiniteMembershipControls {
    private FiniteMembershipControls() {}
    private static final String CONTEXT = "1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd";
    private static final List<Object> rows = new ArrayList<>();
    private static int checks;
    private static final IdentityHashMap<Object,Integer> objectIds = new IdentityHashMap<>();
    private static String identity(Object value) {
        if(value==null)return "null";
        Integer id=objectIds.get(value);if(id==null){id=objectIds.size()+1;objectIds.put(value,id);}
        return value.getClass().getName()+"@fixture-object-"+id;
    }
    private static String classHash;
    private static Object fixture, foreignFixture, candidate, journal, foreignCandidate, foreignJournal;
    private static NativeRenderer renderer, foreignRenderer;
    private static NativeAppearanceViewsV2.NativeField a, b, c;
    private static NativeAppearanceViewsV2.FieldPreservation scopeA, scopeC, foreignScope;
    private static Object stateA, stateC, membershipA, membershipC;
    private static Object[] states;
    private static boolean observed;
    private static int countAtEntry;
    private static final List<Object> boundaryFrames=new ArrayList<>();
    private static final Map<String,Method> methods = new LinkedHashMap<>();
    private static void check(boolean condition, String why) {
        checks++;
        if (!condition) throw new AssertionError(why);
    }
    private static Field field(Object object, String name) {
        for (Class<?> type = object instanceof Class<?> value ? value : object.getClass(); type != null; type = type.getSuperclass()) {
            try { Field result = type.getDeclaredField(name); result.setAccessible(true); return result; }
            catch (NoSuchFieldException ignored) { /* exact superclass field lookup */ }
        }
        throw new AssertionError("missing exact field " + name);
    }
    private static Object get(Object object, String name) {
        try { return field(object,name).get(object instanceof Class<?> ? null : object); }
        catch (IllegalAccessException failure) { throw new AssertionError(failure); }
    }
    private static void put(Object object, String name, Object value) {
        try { field(object,name).set(object instanceof Class<?> ? null : object,value); }
        catch (IllegalAccessException failure) { throw new AssertionError(failure); }
    }
    private static Object invoke(Object receiver, String name, Object... arguments) {
        for (Method method : receiver.getClass().getDeclaredMethods()) if (method.getName().equals(name) && method.getParameterCount() == arguments.length) {
            try { method.setAccessible(true); return method.invoke(receiver,arguments); }
            catch (InvocationTargetException failure) {
                if (failure.getCause() instanceof Error fatal) throw fatal;
                if (failure.getCause() instanceof RuntimeException ordinary) throw ordinary;
                throw new AssertionError(failure.getCause());
            } catch (ReflectiveOperationException failure) { throw new AssertionError(failure); }
        }
        throw new AssertionError("original fixture method missing: " + name);
    }
    private static Object newFixture() throws ReflectiveOperationException {
        Class<?> type = Class.forName("dev.mixer.android.SelectedIdentityMembershipReviewControls$Fixture");
        Constructor<?> constructor = type.getDeclaredConstructor(boolean.class,boolean.class);
        constructor.setAccessible(true);
        return constructor.newInstance(true,true);
    }
    private static int integer(Object object, String name) { return (Integer)get(object,name); }
    private static int[] counts() {
        return new int[] {integer(candidate,"heldPreservations"),integer(renderer,"outstandingFieldPreservations"),integer(renderer,"outstandingEditorNativeCalls")};
    }
    private static Object exactState(NativeAppearanceViewsV2.Record record) {
        for (Object state : states) if (get(state,"record") == record) return state;
        throw new AssertionError("actual state absent");
    }
    private static boolean boundary(Object selected, String method, String phase) {
        return method.equals("View.invalidate") && phase.equals("entry") && ConcreteHostProbe.lastEvent().receiver == selected &&
            ((NativeAppearanceViewsV2.NativeField)selected).record.fieldPreservation != null;
    }
    /** Capture every reachable product/host field (including inherited fields), array slot and collection member.
     * JDK value objects remain reference anchors; no reflective access into JDK internals. */
    private static final class State {
        private final IdentityHashMap<Object,Map<Field,Object>> fields = new IdentityHashMap<>();
        private final IdentityHashMap<Object,List<Object>> contents = new IdentityHashMap<>();
        private final Map<Field,Object> bridge = new LinkedHashMap<>();
        private final List<ConcreteHostProbe.Event> events = ConcreteHostProbe.events();
        private int slots;
        State(Object... roots) {
            for (Object root : roots) add(root);
            for (Field selected : NativeBridge.class.getDeclaredFields()) if (Modifier.isStatic(selected.getModifiers())) {
                try { selected.setAccessible(true); Object value = selected.get(null); bridge.put(selected,value); add(value); }
                catch (IllegalAccessException failure) { throw new AssertionError(failure); }
            }
        }
        private void add(Object value) {
            if (value == null || fields.containsKey(value) || contents.containsKey(value)) return;
            Class<?> type = value.getClass();
            if (type.isArray()) {
                List<Object> saved = new ArrayList<>(); contents.put(value,saved);
                for (int i=0;i<Array.getLength(value);i++) { Object item=Array.get(value,i);saved.add(item);slots++;if(!type.getComponentType().isPrimitive())add(item); }
            } else if (value instanceof Map<?,?> map) {
                List<Object> saved = new ArrayList<>();contents.put(value,saved);
                for (var item : map.entrySet()) { saved.add(item.getKey());saved.add(item.getValue());slots+=2;add(item.getKey());add(item.getValue()); }
            } else if (value instanceof Collection<?> collection) {
                List<Object> saved = new ArrayList<>(collection);contents.put(value,saved);slots+=saved.size();for(Object item:saved)add(item);
            } else if ((type.getName().startsWith("dev.mixer.android.") || type.getName().startsWith("android.")) && !type.isEnum()) {
                Map<Field,Object> saved = new LinkedHashMap<>();fields.put(value,saved);
                for(Class<?> owner=type;owner!=null && owner!=Object.class;owner=owner.getSuperclass()) {
                    for(Field selected:owner.getDeclaredFields()) if(!Modifier.isStatic(selected.getModifiers())) {
                        try { selected.setAccessible(true);Object item=selected.get(value);saved.put(selected,item);add(item); }
                        catch(IllegalAccessException failure){throw new AssertionError(failure);}
                    }
                }
            }
        }
        int fieldCount() { int result=bridge.size();for(var saved:fields.values())result+=saved.size();return result; }
        String digest() {
            List<String> lines=new ArrayList<>();
            for(var saved:fields.entrySet())for(var item:saved.getValue().entrySet())lines.add(identity(saved.getKey())+"/"+item.getKey()+"="+(item.getKey().getType().isPrimitive()?String.valueOf(item.getValue()):identity(item.getValue())));
            for(var item:bridge.entrySet())lines.add("static/"+item.getKey()+"="+(item.getKey().getType().isPrimitive()?String.valueOf(item.getValue()):identity(item.getValue())));
            for(var saved:contents.entrySet())for(int i=0;i<saved.getValue().size();i++)lines.add(identity(saved.getKey())+"/["+i+"]="+(saved.getKey().getClass().isArray()&&saved.getKey().getClass().getComponentType().isPrimitive()?String.valueOf(saved.getValue().get(i)):identity(saved.getValue().get(i))));
            for(int i=0;i<events.size();i++)lines.add("native-event/["+i+"]="+identity(events.get(i)));
            lines.sort(String::compareTo);
            try{return java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(String.join("\n",lines).getBytes(java.nio.charset.StandardCharsets.UTF_8)));}
            catch(java.security.NoSuchAlgorithmException failure){throw new AssertionError(failure);}
        }
        void unchanged() {
            for(var saved:fields.entrySet())for(var item:saved.getValue().entrySet()) {
                try { Object value=item.getKey().get(saved.getKey());check(item.getKey().getType().isPrimitive()?item.getValue().equals(value):item.getValue()==value,"pure exact field "+item.getKey()); }
                catch(IllegalAccessException failure){throw new AssertionError(failure);}
            }
            for(var item:bridge.entrySet()) {
                try {Object value=item.getKey().get(null);check(item.getKey().getType().isPrimitive()?item.getValue().equals(value):item.getValue()==value,"no JNI leaf counter/reference effect "+item.getKey());}
                catch(IllegalAccessException failure){throw new AssertionError(failure);}
            }
            for(var saved:contents.entrySet()) {
                Object value=saved.getKey();List<Object> actual=new ArrayList<>();boolean primitive=value.getClass().isArray()&&value.getClass().getComponentType().isPrimitive();
                if(value.getClass().isArray())for(int i=0;i<Array.getLength(value);i++)actual.add(Array.get(value,i));
                else if(value instanceof Map<?,?> map)for(var item:map.entrySet()){actual.add(item.getKey());actual.add(item.getValue());}
                else actual.addAll((Collection<?>)value);
                check(actual.size()==saved.getValue().size(),"pure array/collection extent");
                for(int i=0;i<actual.size();i++)check(primitive?saved.getValue().get(i).equals(actual.get(i)):saved.getValue().get(i)==actual.get(i),"pure exact array/collection member");
            }
            List<ConcreteHostProbe.Event> after=ConcreteHostProbe.events();check(after.size()==events.size(),"zero new native/platform events");
            for(int i=0;i<events.size();i++)check(events.get(i)==after.get(i),"exact native event prefix");
        }
    }
    private record Change(Object target,String name,Object replacement) {}
    private static Change change(Object target,String name,Object replacement) {return new Change(target,name,replacement);}
    private static void mutated(Runnable body, Change... changes) {
        Object[] previous=new Object[changes.length];
        for(int i=0;i<changes.length;i++){Change change=changes[i];previous[i]=get(change.target,change.name);put(change.target,change.name,change.replacement);}
        try{body.run();}finally{for(int i=changes.length-1;i>=0;i--)put(changes[i].target,changes[i].name,previous[i]);}
    }
    private static void arrayAt(Object array,int index,Object replacement,Runnable body) {
        Object old=Array.get(array,index);Array.set(array,index,replacement);try{body.run();}finally{Array.set(array,index,old);}
    }
    private static void test(String method,String label,Boolean expected,Class<? extends Throwable> failure,String oracle,Object... args) {
        Method selected=methods.get(method);check(selected!=null,"exact bound method");
        State before=new State(fixture,foreignFixture,candidate,journal,scopeA,scopeC,foreignScope,stateA,stateC,membershipA,membershipC,args);
        String beforeDigest=before.digest();int[] beforeCounts=counts();int events=ConcreteHostProbe.events().size();Object result=null;Throwable thrown=null;
        try{result=selected.invoke(renderer,args);}catch(InvocationTargetException wrapped){thrown=wrapped.getCause();}catch(IllegalAccessException error){throw new AssertionError(error);}
        before.unchanged();
        State after=new State(fixture,foreignFixture,candidate,journal,scopeA,scopeC,foreignScope,stateA,stateC,membershipA,membershipC,args);
        String afterDigest=after.digest();check(beforeDigest.equals(afterDigest),"exact before/after identity/scalar/native-event snapshot digest");
        if(failure==null){check(thrown==null,"unexpected product failure "+method+"/"+label+": "+thrown);check(result instanceof Boolean&&result.equals(expected),"independent literal boolean "+method+"/"+label+" expected="+expected+" actual="+result);}
        else{check(thrown!=null&&thrown.getClass()==failure,"exact typed failure "+method+"/"+label);check(result==null,"throw has no fabricated boolean result");}
        String descriptor=MethodType.methodType(selected.getReturnType(),selected.getParameterTypes()).toMethodDescriptorString();
        rows.add(Json.map("subject_id","dev/mixer/android/NativeRenderer#"+method+descriptor,"descriptor",descriptor,
            "class_sha256",classHash,"source_context",CONTEXT,"case_id","renderer-finite-source-invariants","control_case",label,
            "oracle",oracle,"expected",failure==null?expected:failure.getName(),"actual",thrown==null?result:thrown.getClass().getName(),
            "typed_outcome",thrown==null?"java.lang.Boolean":"throw","all_snapshots_unchanged",true,"snapshot_before_sha256",beforeDigest,"snapshot_after_sha256",afterDigest,
            "identity_anchors",Json.map("renderer",identity(renderer),"candidate",identity(candidate),"journal",identity(journal),"scope_A",identity(scopeA),"scope_C",identity(scopeC),"state_A",identity(stateA),"state_C",identity(stateC),"original",identity(scopeA.original)),"snapshotted_objects",before.fields.size(),
            "snapshotted_fields",before.fieldCount(),"snapshotted_array_collection_slots",before.slots,"counts_before",beforeCounts,"counts_after",counts(),
            "native_events_before",events,"native_events_after",ConcreteHostProbe.events().size(),"native_effects",0,
            "restoration","outer test-only finally restores every deliberate mutation before original edit resumes"));
    }
    private static void yes(String m,String label,String oracle,Object...args){test(m,label,true,null,oracle,args);}
    private static void no(String m,String label,String oracle,Object...args){test(m,label,false,null,oracle,args);}
    private static void npe(String m,String label,String oracle,Object...args){test(m,label,null,NullPointerException.class,oracle,args);}
    private static Object[] tuple(){return new Object[]{candidate,journal,a.record,scopeA};}
    private static void membership() {
        String m="preservationMembershipV2";
        yes(m,"actual-ordered-two-scope-roster","actual constructor-bound ordered identities are retained",journal);
        no(m,"null-journal","no journal cannot name a roster",(Object)null);
        mutated(()->no(m,"null-states","no state array cannot name roster",journal),change(journal,"states",null));
        for(int wrong:new int[]{-1,states.length-1,states.length+1})mutated(()->no(m,"length-count-"+wrong,"exact roster length differs from stored count",journal),change(journal,"stateCount",wrong));
        int index=integer(stateA,"position"),other=integer(stateC,"position");
        arrayAt(states,index,null,()->no(m,"null-state","each ordered slot requires its actual state",journal));
        mutated(()->no(m,"foreign-state-journal","state journal identity is foreign",journal),change(stateA,"journal",foreignJournal));
        for(int wrong:new int[]{-1,index+1})mutated(()->no(m,"wrong-position-"+wrong,"state position must name its exact slot",journal),change(stateA,"position",wrong));
        arrayAt(states,other,stateA,()->no(m,"duplicate-owned-state","duplicate exact A state cannot occupy C's slot",journal));
        arrayAt(states,index,stateC,()->arrayAt(states,other,stateA,()->no(m,"reordered-owned-states","moving state references retains wrong constructor positions",journal)));
        mutated(()->no(m,"scope-without-membership","registered scope alone is insufficient",journal),change(stateA,"membership",null));
        mutated(()->no(m,"forward-without-membership","forward flag alone is insufficient",journal),change(stateA,"membership",null),change(stateA,"preservation",null));
        mutated(()->yes(m,"no-scope-no-forward-no-membership","a slot without preservation is valid",journal),change(stateA,"membership",null),change(stateA,"preservation",null),change(stateA,"forwardPreserved",false));
        mutated(()->no(m,"membership-state-wrong","membership binds an exact state reference",journal),change(membershipA,"state",stateC));
        mutated(()->no(m,"membership-scope-wrong","membership must identify the actual state scope",journal),change(membershipA,"scope",scopeC));
        mutated(()->no(m,"missing-forward","captured scope requires forward flag",journal),change(stateA,"forwardPreserved",false));
        mutated(()->no(m,"scope-record-wrong","captured scope and state record must be identical",journal),change(scopeA,"record",c.record));
        mutated(()->no(m,"scope-journal-wrong","scope journal must be the exact roster owner",journal),change(scopeA,"journal",foreignJournal));
        mutated(()->yes(m,"matching-null-record-pointers","scalar membership accepts matching null record pointers; it is not capture authority",journal),change(stateA,"record",null),change(scopeA,"record",null));
        mutated(()->npe(m,"matching-null-scope-pointers","matching malformed null scope pointers reach actual field dereference; no invented false",journal),change(membershipA,"scope",null),change(stateA,"preservation",null));
        Object empty=Array.newInstance(states.getClass().getComponentType(),0);
        mutated(()->yes(m,"valid-empty-roster","exact empty array and zero count are valid membership",journal),change(journal,"states",empty),change(journal,"stateCount",0));
    }
    private static void captured() {
        String m="fieldPreservationCapturedV2";yes(m,"actual-captured-tuple","all exact captured references and transaction token match",tuple());
        no(m,"null-candidate","candidate required",null,journal,a.record,scopeA);
        no(m,"null-journal","journal required",candidate,null,a.record,scopeA);
        no(m,"wrong-journal-argument","argument journal must be candidate journal",candidate,foreignJournal,a.record,scopeA);
        no(m,"null-record","record required",candidate,journal,null,scopeA);
        no(m,"wrong-record-argument","scope must capture the argument record",candidate,journal,c.record,scopeA);
        no(m,"null-scope","scope required",candidate,journal,a.record,null);
        Change[] wrongs={change(candidate,"owner",foreignRenderer),change(journal,"candidate",foreignCandidate),change(scopeA,"renderer",foreignRenderer),
            change(scopeA,"candidate",foreignCandidate),change(scopeA,"journal",foreignJournal),change(scopeA,"record",c.record),change(a.record,"view",c),
            change(scopeA,"field",c),change(a,"record",c.record),change(a.record,"input",get(foreignRenderer,"v2Input")),change(a.record,"editorFence",get(foreignFixture,"fence")),
            change(candidate,"originalMutation",null),change(scopeA.original,"fence",get(foreignFixture,"fence")),change(scopeA.original,"mode",NativeAppearanceViewsV2.Mutation.Mode.LIVE_PRESENTATION),
            change(scopeA.original,"token",foreignScope.original.token),change(scopeA.original,"editorLease",b.record.editorCallbackLease),change(scopeA.original,"fieldLease",scopeC)};
        for(int i=0;i<wrongs.length;i++){Change wrong=wrongs[i];final int number=i;mutated(()->no(m,"wrong-identity-"+number+"-"+wrong.name,"one captured tuple identity/mode/nested-lease premise deliberately differs",tuple()),wrong);}
        var twin=NativeAppearanceViewsV2.Mutation.transaction(scopeA.original.fence,scopeA.original.token);
        check(twin!=scopeA.original&&twin.token==scopeA.original.token,"equal-token original is a distinct actual ordinary Mutation");
        mutated(()->no(m,"equal-token-new-candidate-original","equal token does not substitute the identical original object",tuple()),change(candidate,"originalMutation",twin));
        mutated(()->no(m,"equal-token-new-scope-original","scope original must be same original object",tuple()),change(scopeA,"original",twin));
        var replacement=new NativeAppearanceViewsV2.Replacement(a,scopeA.original,scopeA.editable,0);
        mutated(()->no(m,"nested-replacement-lease","original cannot carry a replacement lease",tuple()),change(scopeA.original,"replacementLease",replacement));
        mutated(()->no(m,"cleanup-mode","captured original must be transaction mode",tuple()),change(scopeA.original,"mode",NativeAppearanceViewsV2.Mutation.Mode.CLEANUP));
        mutated(()->yes(m,"terminal-current-fence-does-not-rewrite-capture","capture identity is distinct from current authority",tuple()),change(scopeA.original.fence,"terminal",true));
        mutated(()->yes(m,"counts-do-not-authorize-capture","capture predicate ignores held/global/shared counts",tuple()),change(candidate,"heldPreservations",-1),change(renderer,"outstandingFieldPreservations",-1),change(renderer,"outstandingEditorNativeCalls",-1));
        mutated(()->npe(m,"matching-null-field-pointers","matching null record.view/scope.field reaches actual field.record dereference",tuple()),change(a.record,"view",null),change(scopeA,"field",null));
    }
    private static void provenance() {
        String m="preservationProvenanceV2";yes(m,"actual-own-provenance","actual own captured scopes share exact tuple",candidate,journal);
        npe(m,"null-journal","journal dereference is an actual typed failure",candidate,null);
        mutated(()->yes(m,"null-states-own-malformed","null states is own malformed classification and grants no release authority",candidate,journal),change(journal,"states",null));
        int index=integer(stateA,"position");
        arrayAt(states,index,null,()->yes(m,"null-state-skipped","classifier skips null state",candidate,journal));
        mutated(()->yes(m,"wrong-journal-state-skipped","classifier skips state belonging to another journal even if its capture is foreign",candidate,journal),change(stateA,"journal",foreignJournal),change(membershipA,"scope",foreignScope));
        mutated(()->yes(m,"state-count-does-not-authorize-provenance","classifier iterates actual state array independent of malformed stored count",candidate,journal),change(journal,"stateCount",-1));
        mutated(()->yes(m,"wrong-position-does-not-authorize-provenance","classifier ignores own malformed constructor position",candidate,journal),change(stateA,"position",-1));
        mutated(()->no(m,"matching-null-record-is-not-capture","null matching record pointers are not capture identity",candidate,journal),change(stateA,"record",null),change(scopeA,"record",null));
        mutated(()->no(m,"foreign-membership-scope","foreign captured scope rejects provenance",candidate,journal),change(membershipA,"scope",foreignScope));
        mutated(()->no(m,"foreign-current-scope","foreign state preservation rejects provenance",candidate,journal),change(stateA,"preservation",foreignScope));
        mutated(()->no(m,"conflicting-record-registration","another current record scope conflicts with this captured membership",candidate,journal),change(a.record,"fieldPreservation",scopeC));
        mutated(()->yes(m,"null-current-registration","absence of current record registration does not invent foreign capture",candidate,journal),change(a.record,"fieldPreservation",null));
        mutated(()->yes(m,"membership-only-own-capture","own captured membership without current state scope is own classification",candidate,journal),change(stateA,"preservation",null));
        mutated(()->yes(m,"no-capture-in-state","empty preservation state does not supply foreign authority",candidate,journal),change(stateA,"membership",null),change(stateA,"preservation",null));
        mutated(()->no(m,"no-membership-conflicting-registration","current own state scope with another registration rejects",candidate,journal),change(stateA,"membership",null),change(a.record,"fieldPreservation",scopeC));
        var twin=new NativeAppearanceViewsV2.FieldPreservation(a,scopeA.original,scopeA.selected,scopeA.editable,renderer,(NativeRenderer.Candidate)candidate,(NativeRenderer.AttachmentJournal)journal);
        mutated(()->yes(m,"registered-exact-membership-scope","classifier accepts current registration equal to independently captured membership scope",candidate,journal),change(membershipA,"scope",twin),change(a.record,"fieldPreservation",twin));
        no(m,"null-candidate-with-capture","actual own captures cannot be captured by null candidate",null,journal);
        Object empty=Array.newInstance(states.getClass().getComponentType(),0);
        mutated(()->yes(m,"empty-states-null-candidate","classifier has no captured scope to inspect in empty states",null,journal),change(journal,"states",empty));
    }
    private static void identity() {
        String m="fieldPreservationIdentityV2";yes(m,"actual-exact-member","captured tuple plus full roster identifies exact member",tuple());
        no(m,"null-candidate","captured tuple guard fails before membership",null,journal,a.record,scopeA);
        mutated(()->no(m,"malformed-other-state","whole roster validity is required even for exact A tuple",tuple()),change(stateC,"position",-1));
        mutated(()->no(m,"nonmember-valid-empty-roster","valid empty membership contains no A record",tuple()),change(journal,"states",Array.newInstance(states.getClass().getComponentType(),0)),change(journal,"stateCount",0));
        mutated(()->no(m,"valid-unpreserved-record","valid state with no preservation is not an exact preserved member",tuple()),change(stateA,"membership",null),change(stateA,"preservation",null),change(stateA,"forwardPreserved",false));
        mutated(()->no(m,"different-scope-not-same-reference","another scope does not identify this exact membership",candidate,journal,a.record,scopeC));
        Object earlier=states[0];check(earlier!=stateA&&get(earlier,"preservation")==null,"actual first roster state precedes A without preservation");
        mutated(()->no(m,"first-matching-record-controls","first exact record occurrence has no forward scope, even if a later A occurrence does",tuple()),change(earlier,"record",a.record));
        var twin=new NativeAppearanceViewsV2.FieldPreservation(a,scopeA.original,scopeA.selected,scopeA.editable,renderer,(NativeRenderer.Candidate)candidate,(NativeRenderer.AttachmentJournal)journal);
        mutated(()->no(m,"same-record-different-captured-scope","valid roster carries another own captured scope for the record, not the argument scope",tuple()),change(stateA,"preservation",twin),change(membershipA,"scope",twin));
        mutated(()->yes(m,"counts-independent","identity makes no count authorization claim",tuple()),change(candidate,"heldPreservations",-1),change(renderer,"outstandingFieldPreservations",-1),change(renderer,"outstandingEditorNativeCalls",-1));
        mutated(()->yes(m,"used-terminal-still-captured-identity","captured identity is independent of current success authority",tuple()),change(candidate,"used",true),change(scopeA.original.fence,"terminal",true));
    }
    private static void funding() {
        String cohort="preservationCohortV2",fund="preservationFailureFundedV2";int bound=states.length;check(bound>=3,"actual roster has capacity for held three");
        // Each row is independent literal [counted A, counted C, held, global, shared, cohort, funded].
        int[][] cases={
            {1,1,2,2,3,1,1},{1,1,2,2,2,1,1},{1,1,2,2,1,0,0},{1,1,1,1,3,0,0},{1,1,3,3,3,0,1},
            {1,1,3,3,2,0,0},{1,1,-1,-1,3,0,0},{1,1,bound+1,bound+1,bound+1,0,0},{1,1,2,1,3,0,0},{1,1,2,3,3,0,0},{1,1,2,2,-1,0,0},
            {0,1,1,1,1,1,1},{1,0,1,1,3,1,1},{0,1,2,2,3,0,1},{0,1,0,0,3,0,0},{0,1,3,3,3,0,1},
            {0,0,0,0,0,1,1},{0,0,0,0,3,1,1},{0,0,1,1,1,0,1},{0,0,-1,-1,3,0,0},{0,0,0,1,3,0,0},{0,0,0,0,-1,0,0},
            {0,0,bound,bound,bound,0,1},{0,0,bound+1,bound+1,bound+1,0,0},{0,0,0,-1,3,0,0}
        };
        for(int i=0;i<cases.length;i++){int[] v=cases[i];final int n=i;mutated(()->{
            test(cohort,"literal-count-vector-"+n,v[5]==1,null,"cohort requires represented == held == global with sufficient shared; unrelated shared work permitted",candidate);
            test(fund,"literal-count-vector-"+n,v[6]==1,null,"funding permits held above represented within roster bound, exact global and sufficient shared; no healthy release authorization",candidate);
        },change(scopeA,"counted",v[0]==1),change(scopeC,"counted",v[1]==1),change(candidate,"heldPreservations",v[2]),change(renderer,"outstandingFieldPreservations",v[3]),change(renderer,"outstandingEditorNativeCalls",v[4]));}
        for(String m:new String[]{cohort,fund}){
            npe(m,"null-candidate","candidate journal dereference is actual typed failure",(Object)null);
            mutated(()->no(m,"null-candidate-journal","missing journal has no membership",candidate),change(candidate,"journal",null));
            mutated(()->no(m,"malformed-membership","invalid ordered membership refuses before count authorization",candidate),change(stateC,"position",-1));
            mutated(()->yes(m,"ended-release-flags-do-not-authorize-health","finite count predicate ignores healthy ending/current-authority flags",candidate),change(scopeA,"ended",true),change(scopeA,"released",true),change(scopeA,"entered",false),change(candidate,"used",true));
            mutated(()->yes(m,"zero-empty-roster","empty roster with zero held/global/shared is valid count relationship",candidate),change(journal,"states",Array.newInstance(states.getClass().getComponentType(),0)),change(journal,"stateCount",0),change(candidate,"heldPreservations",0),change(renderer,"outstandingFieldPreservations",0),change(renderer,"outstandingEditorNativeCalls",0));
        }
    }
    private static void matrix() {
        check(states.length==integer(journal,"stateCount"),"actual full constructor roster");
        check(scopeA!=scopeC&&scopeA.candidate==candidate&&scopeC.candidate==candidate&&scopeA.original==scopeC.original,"actual two scopes capture same candidate and identical original");
        check(scopeA.counted&&scopeC.counted&&integer(candidate,"heldPreservations")==2&&integer(renderer,"outstandingFieldPreservations")==2&&integer(renderer,"outstandingEditorNativeCalls")==3,"real count3 boundary before finite mutations");
        State baseline=new State(fixture,foreignFixture,candidate,journal,scopeA,scopeC,foreignScope);
        RuntimeException primary=new IllegalStateException("test-only original primary identity");Error fatal=new AssertionError("test-only original first Error identity");
        mutated(()->{membership();captured();provenance();identity();funding();},change(get(renderer,"v2Cleanup"),"primary",primary),change(get(renderer,"v2Cleanup"),"firstFatal",fatal));
        baseline.unchanged();
    }
    private static void write(StringBuilder output,Object value) {
        if(value instanceof int[] array){output.append('[');for(int i=0;i<array.length;i++){if(i>0)output.append(',');output.append(array[i]);}output.append(']');}
        else if(value instanceof Map<?,?> map){output.append('{');boolean comma=false;for(var item:map.entrySet()){if(comma)output.append(',');comma=true;Json.write(output,item.getKey());output.append(':');write(output,item.getValue());}output.append('}');}
        else if(value instanceof Collection<?> collection){output.append('[');boolean comma=false;for(Object item:collection){if(comma)output.append(',');comma=true;write(output,item);}output.append(']');}
        else if(value instanceof Number)output.append(value);
        else Json.write(output,value);
    }
    public static void main(String[] arguments) throws Exception {
        Class<?> original=Class.forName("dev.mixer.android.SelectedIdentityMembershipReviewControls");
        put(original,"descriptor",Files.readAllBytes(Path.of(arguments[0])));
        try(var stream=NativeRenderer.class.getResourceAsStream("NativeRenderer.class")){check(stream!=null,"actual class bytes");classHash=java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(stream.readAllBytes()));}
        check(classHash.equals("c7ad938bb6a6cc5403927006171a344750966bef2d1fa8e8b6b6ae7ef8551d2f"),"exact released class hash");
        Class<?> ct=Class.forName("dev.mixer.android.NativeRenderer$Candidate"),jt=Class.forName("dev.mixer.android.NativeRenderer$AttachmentJournal");
        for(String name:new String[]{"preservationMembershipV2","fieldPreservationCapturedV2","preservationProvenanceV2","fieldPreservationIdentityV2","preservationCohortV2","preservationFailureFundedV2"}){
            Class<?>[] parameters=name.equals("preservationMembershipV2")?new Class<?>[]{jt}:name.equals("preservationProvenanceV2")?new Class<?>[]{ct,jt}:name.startsWith("fieldPreservation")?new Class<?>[]{ct,jt,NativeAppearanceViewsV2.Record.class,NativeAppearanceViewsV2.FieldPreservation.class}:new Class<?>[]{ct};
            Method method=NativeRenderer.class.getDeclaredMethod(name,parameters);method.setAccessible(true);check(method.getReturnType()==boolean.class,"exact boolean method descriptor");methods.put(name,method);
        }
        try{
            foreignFixture=newFixture();foreignRenderer=(NativeRenderer)get(foreignFixture,"renderer");var foreignA=(NativeAppearanceViewsV2.NativeField)get(foreignFixture,"a");
            ConcreteHostProbe.hook=(method,phase)->{if(foreignScope==null&&boundary(foreignA,method,phase)){foreignScope=foreignA.record.fieldPreservation;foreignCandidate=get(foreignRenderer,"v2Pending");foreignJournal=get(foreignCandidate,"journal");}};
            check((Boolean)invoke(foreignFixture,"edit"),"ordinary foreign fixture edit completed");ConcreteHostProbe.hook=null;check(foreignScope!=null&&integer(foreignRenderer,"outstandingEditorNativeCalls")==0,"foreign actual completed identities retained without custody");
            fixture=newFixture();renderer=(NativeRenderer)get(fixture,"renderer");a=(NativeAppearanceViewsV2.NativeField)get(fixture,"a");b=(NativeAppearanceViewsV2.NativeField)get(fixture,"b");c=(NativeAppearanceViewsV2.NativeField)get(fixture,"c");
            ConcreteHostProbe.hook=(method,phase)->{if(!observed&&boundary(a,method,phase)){
                observed=true;
                for(var site:ConcreteHostProbe.lastEvent().productionFrames)boundaryFrames.add(Json.map("class",site.className(),"method",site.methodName(),"descriptor",site.descriptor(),"bci",site.bytecodeIndex(),"line",site.line()));
                scopeA=a.record.fieldPreservation;scopeC=c.record.fieldPreservation;candidate=get(renderer,"v2Pending");journal=get(candidate,"journal");states=(Object[])get(journal,"states");
                stateA=exactState(a.record);stateC=exactState(c.record);membershipA=get(stateA,"membership");membershipC=get(stateC,"membership");countAtEntry=integer(renderer,"outstandingEditorNativeCalls");matrix();
            }};
            check((Boolean)invoke(fixture,"edit"),"original compatible edit succeeds after all finite test-state restores");ConcreteHostProbe.hook=null;
            check(observed&&integer(renderer,"outstandingEditorNativeCalls")==0&&integer(renderer,"outstandingFieldPreservations")==0&&integer(candidate,"heldPreservations")==0,"actual restored edit releases exact all three counts to zero");
            check(a.record.fieldPreservation==null&&c.record.fieldPreservation==null&&!scopeA.counted&&!scopeC.counted&&scopeA.released&&scopeC.released,"actual original scope registrations/counts unwind");
            StringBuilder result=new StringBuilder();write(result,Json.map("schema",1,"scope","six exact finite pure host predicates; enclosing original obligations remain pending","source_context",CONTEXT,"invocations",rows.size(),"checks",checks,
                "count_at_original_boundary",countAtEntry,"original_boundary",Json.map("leaf_method","View.invalidate","phase","entry","receiver",identity(a),"actual_production_frames",boundaryFrames),"original_edit_completed_after_restores",true,"original_final_counts",counts(),"rows",rows));
            Files.writeString(Path.of(arguments[1]),result+"\n");System.out.println("PASS six exact finite membership/count methods: "+rows.size()+" direct invocations / "+checks+" assertions; actual restored edit count3 -> count0");
        }finally{
            ConcreteHostProbe.hook=null;
            // Original fixture intentionally catches close errors. This is host disposal only, not physical cleanup evidence.
            if(fixture!=null)invoke(fixture,"close");if(foreignFixture!=null)invoke(foreignFixture,"close");
        }
    }
}
