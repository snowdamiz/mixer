package dev.mixer.android;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.ArrayDeque;
import java.util.IdentityHashMap;
import java.util.List;

/** Four focused independent host predicates; no Begin/End or release authority. */
public final class IndependentFieldControls {
    private IndependentFieldControls() {}
    private static int checks, started, joined;
    private static boolean entered;
    private static final List<String> cases=new ArrayList<>();
    private static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    private static Field member(Object receiver,String name)throws ReflectiveOperationException{
        for(Class<?> type=receiver instanceof Class<?> c?c:receiver.getClass();type!=null;type=type.getSuperclass())try{
            Field field=type.getDeclaredField(name);field.setAccessible(true);return field;
        }catch(NoSuchFieldException missing){/* superclass lookup */}
        throw new NoSuchFieldException(name);
    }
    private static Object get(Object receiver,String name){try{return member(receiver,name).get(receiver instanceof Class<?>?null:receiver);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static void set(Object receiver,String name,Object value){try{member(receiver,name).set(receiver instanceof Class<?>?null:receiver,value);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static Object call(Object receiver,String name){try{Method method=receiver.getClass().getDeclaredMethod(name);method.setAccessible(true);return method.invoke(receiver);}catch(InvocationTargetException failure){throw new AssertionError(failure.getCause());}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static final class Snapshot {
        final Object receiver;
        final IdentityHashMap<Field,Object> fields=new IdentityHashMap<>();
        final Object hooks;
        final List<?> hookValues;
        Snapshot(Object value){
            receiver=value;
            try{for(Field field:value.getClass().getDeclaredFields())if(!Modifier.isStatic(field.getModifiers())){field.setAccessible(true);fields.put(field,field.get(value));}}
            catch(IllegalAccessException failure){throw new AssertionError(failure);}
            hooks=get(value,"hooks");hookValues=List.copyOf((ArrayDeque<?>)hooks);
        }
        void unchanged(){
            try{for(var entry:fields.entrySet()){Object actual=entry.getKey().get(receiver);check(entry.getKey().getType().isPrimitive()?entry.getValue().equals(actual):entry.getValue()==actual,"all receiver primitive values and reference identities unchanged: "+entry.getKey().getName());}}
            catch(IllegalAccessException failure){throw new AssertionError(failure);}
            check(get(receiver,"hooks")==hooks&&List.copyOf((ArrayDeque<?>)hooks).equals(hookValues),"hook reference and frozen contents unchanged");
        }
    }
    private static List<Integer> counts(Object candidate,NativeRenderer renderer){return List.of((Integer)get(candidate,"heldPreservations"),(Integer)get(renderer,"outstandingFieldPreservations"),(Integer)get(renderer,"outstandingEditorNativeCalls"));}
    private static void controls(NativeAppearanceViewsV2.NativeField field,NativeRenderer renderer,Object candidate,Object journal){
        var scope=field.record.fieldPreservation;var exactInput=field.record.input;Object snapshot=scope.snapshot;
        check(snapshot!=null,"reuse actual original nonnull EditorSnapshot without invoking its methods");
        long serial=(Long)get(renderer,"editorLossSerial");int events=ConcreteHostProbe.events().size();
        // Setup calls actual constructors before perturbing Input; both receivers remain unregistered.
        var preservation=new NativeAppearanceViewsV2.FieldPreservation(field,scope.original,scope.selected,scope.editable,renderer,(NativeRenderer.Candidate)candidate,(NativeRenderer.AttachmentJournal)journal);
        var replacement=new NativeAppearanceViewsV2.Replacement(field,scope.original,scope.editable,Long.MAX_VALUE);
        preservation.entered=true;preservation.ended=true;preservation.snapshot=scope.snapshot;preservation.phase=-1;
        check(!preservation.counted&&!preservation.released&&!preservation.releaseReady,"ignored custody flags all false");
        replacement.lost=true;
        var previousHook=ConcreteHostProbe.hook;ConcreteHostProbe.hook=null;
        try{
            set(field.record,"input",null);field.record.fieldPreservation=null;set(renderer,"editorLossSerial",Long.MAX_VALUE);
            Snapshot before=new Snapshot(preservation);
            check(preservation.endReady(),"endReady true with null Input, actual nonnull snapshot, negative phase and false ignored flags");before.unchanged();cases.add("endReady-null-Input-nonnull-real-snapshot-false-ignored-flags");
            preservation.callbacks=Integer.MIN_VALUE;before=new Snapshot(preservation);
            check(!preservation.endReady(),"endReady rejects minimum signed callback count");before.unchanged();cases.add("endReady-minimum-int-callback-refusal");
            Snapshot replacementBefore=new Snapshot(replacement);
            check(!replacement.unchangedLoss(),"lost short circuit skips null Input at MAX sentinel on owner thread");replacementBefore.unchanged();cases.add("lost-null-Input-MAX-owner-short-circuit");
            boolean[] answer={true};Throwable[] failure={null};Thread worker=new Thread(()->{try{answer[0]=replacement.unchangedLoss();}catch(RuntimeException|Error escaped){failure[0]=escaped;}},"independent-lost-null-Input");
            worker.setDaemon(true);started++;worker.start();try{worker.join(5000);}catch(InterruptedException interrupted){Thread.currentThread().interrupt();throw new AssertionError(interrupted);}
            if(worker.isAlive()){worker.interrupt();throw new AssertionError("independent worker did not terminate");}joined++;
            check(!answer[0]&&failure[0]==null,"lost short circuit skips null Input and requireMain on actual nonowner thread");replacementBefore.unchanged();cases.add("lost-null-Input-MAX-worker-short-circuit");
            check(ConcreteHostProbe.events().size()==events,"no native leaf calls during independent predicates");
        }finally{
            set(field.record,"input",exactInput);field.record.fieldPreservation=scope;set(renderer,"editorLossSerial",serial);ConcreteHostProbe.hook=previousHook;
        }
        check(field.record.input==exactInput&&field.record.fieldPreservation==scope&&(Long)get(renderer,"editorLossSerial")==serial&&scope.snapshot==snapshot,"exact shared Input registration serial and original snapshot restored");
        check(counts(candidate,renderer).equals(List.of(2,2,3)),"actual shared custody unchanged");
    }
    public static void main(String[] args)throws Exception{
        Class<?> fixtureClass=Class.forName("dev.mixer.android.SelectedIdentityMembershipReviewControls$Fixture");
        set(Class.forName("dev.mixer.android.SelectedIdentityMembershipReviewControls"),"descriptor",Files.readAllBytes(Path.of(args[0])));
        Constructor<?> constructor=fixtureClass.getDeclaredConstructor(boolean.class,boolean.class);constructor.setAccessible(true);
        Object fixture=constructor.newInstance(true,true);NativeRenderer renderer=(NativeRenderer)get(fixture,"renderer");var field=(NativeAppearanceViewsV2.NativeField)get(fixture,"a");Object[] selected={null};
        try{
            ConcreteHostProbe.hook=(method,phase)->{var event=ConcreteHostProbe.lastEvent();if(!entered&&method.equals("View.invalidate")&&phase.equals("entry")&&event.receiver==field&&field.record.fieldPreservation!=null){entered=true;selected[0]=get(renderer,"v2Pending");check(counts(selected[0],renderer).equals(List.of(2,2,3)),"same actual preservation boundary");controls(field,renderer,selected[0],get(selected[0],"journal"));}};
            check(Boolean.TRUE.equals(call(fixture,"edit")),"original fixture edit completes after independent restores");ConcreteHostProbe.hook=null;
            check(entered&&cases.size()==4&&started==1&&joined==1,"four predicates and one joined worker");
            check(counts(selected[0],renderer).equals(List.of(0,0,0))&&field.record.fieldPreservation==null,"original final custody and registration");
            Files.writeString(Path.of(args[1]),"{\"schema\":1,\"status\":\"passed-host-only\",\"cases\":4,\"checks\":"+checks+",\"setup_constructor_calls\":2,\"host_threads_started\":"+started+",\"host_threads_joined\":"+joined+",\"original_edit_completed\":true,\"original_final_counts\":[0,0,0],\"case_names\":[\""+String.join("\",\"",cases)+"\"],\"Input_MAX_exhaustion_executed\":false,\"native_callback_state_credit\":0}\n");
            System.out.println("PASS independent four targeted predicates / "+checks+" checks; host only");
        }finally{ConcreteHostProbe.hook=null;call(fixture,"close");}
    }
}
