package dev.mixer.android;

import android.text.Editable;
import java.lang.invoke.MethodType;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Four exact ordinary host bodies, with literal oracles; no membership or release authority. */
public final class FieldFiniteControls {
    private FieldFiniteControls() {}
    private static final String CONTEXT="1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd";
    private static final String FP="dev/mixer/android/NativeAppearanceViewsV2$FieldPreservation";
    private static final String RP="dev/mixer/android/NativeAppearanceViewsV2$Replacement";
    private static final String FD="(Ldev/mixer/android/NativeAppearanceViewsV2$NativeField;Ldev/mixer/android/NativeAppearanceViewsV2$Mutation;Ldev/mixer/android/NativeAppearanceViewsV2$Binding;Landroid/text/Editable;Ldev/mixer/android/NativeRenderer;Ldev/mixer/android/NativeRenderer$Candidate;Ldev/mixer/android/NativeRenderer$AttachmentJournal;)V";
    private static final String RD="(Ldev/mixer/android/NativeAppearanceViewsV2$NativeField;Ldev/mixer/android/NativeAppearanceViewsV2$Mutation;Landroid/text/Editable;J)V";
    private static final List<Object> rows=new ArrayList<>();
    private static final IdentityHashMap<Object,Integer> identities=new IdentityHashMap<>();
    private static final IdentityHashMap<Object,Boolean> constructorHooks=new IdentityHashMap<>();
    private static final List<Object> boundary=new ArrayList<>();
    private static Object fixture,candidate,journal,fence;
    private static NativeRenderer renderer;
    private static NativeAppearanceViewsV2.NativeField field;
    private static NativeAppearanceViewsV2.FieldPreservation originalScope;
    private static NativeAppearanceViewsV2.Input exactInput;
    private static int checks,workersStarted,workersReaped;
    private static boolean entered;
    private static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    private static String id(Object value){if(value==null)return "null";Integer n=identities.get(value);if(n==null){n=identities.size()+1;identities.put(value,n);}return value.getClass().getName()+"@object-"+n;}
    private static Field reflected(Object receiver,String name){for(Class<?> type=receiver instanceof Class<?> c?c:receiver.getClass();type!=null;type=type.getSuperclass())try{Field f=type.getDeclaredField(name);f.setAccessible(true);return f;}catch(NoSuchFieldException absent){/* inherited field lookup */}throw new AssertionError(name);}
    private static Object get(Object receiver,String name){try{return reflected(receiver,name).get(receiver instanceof Class<?>?null:receiver);}catch(IllegalAccessException failure){throw new AssertionError(failure);}}
    private static void put(Object receiver,String name,Object value){try{reflected(receiver,name).set(receiver instanceof Class<?>?null:receiver,value);}catch(IllegalAccessException failure){throw new AssertionError(failure);}}
    private static Object rethrow(Throwable failure){if(failure instanceof Error fatal)throw fatal;if(failure instanceof RuntimeException ordinary)throw ordinary;throw new AssertionError(failure);}
    private static Object invoke(Object receiver,String name,Object... args){for(Method method:receiver.getClass().getDeclaredMethods())if(method.getName().equals(name)&&method.getParameterCount()==args.length)try{method.setAccessible(true);return method.invoke(receiver,args);}catch(InvocationTargetException failure){return rethrow(failure.getCause());}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}throw new AssertionError(name);}
    private static Object construct(Constructor<?> constructor,Object... args){try{return constructor.newInstance(args);}catch(InvocationTargetException failure){return rethrow(failure.getCause());}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static final class Changes implements AutoCloseable {
        private record Change(Object receiver,String name,Object prior){}
        private final List<Change> changes=new ArrayList<>();
        void set(Object receiver,String name,Object value){changes.add(new Change(receiver,name,get(receiver,name)));put(receiver,name,value);}
        @Override public void close(){for(int i=changes.size()-1;i>=0;i--){var c=changes.get(i);put(c.receiver,c.name,c.prior);}}
    }
    private static List<Integer> counts(){return List.of((Integer)get(candidate,"heldPreservations"),(Integer)get(renderer,"outstandingFieldPreservations"),(Integer)get(renderer,"outstandingEditorNativeCalls"));}
    private static List<Object> frames(){return StackWalker.getInstance(StackWalker.Option.RETAIN_CLASS_REFERENCE).walk(stream->stream.filter(f->f.getClassName().startsWith("dev.mixer.android.Native")).map(f->(Object)Json.map("class",f.getClassName(),"method",f.getMethodName(),"descriptor",f.getDescriptor(),"bci",f.getByteCodeIndex(),"line",f.getLineNumber())).toList());}
    private static final class InputObservation implements InvocationHandler {
        final NativeAppearanceViewsV2.Input proxy;
        int calls;
        Long value;
        Throwable exception;
        List<Object> callFrames=List.of();
        InputObservation(){proxy=(NativeAppearanceViewsV2.Input)Proxy.newProxyInstance(FieldFiniteControls.class.getClassLoader(),new Class<?>[]{NativeAppearanceViewsV2.Input.class},this);}
        @Override public Object invoke(Object receiver,Method method,Object[] args)throws Throwable{
            if(!method.getName().equals("editorLossObservation"))throw new AssertionError("unexpected Input call: "+method.getName());
            calls++;callFrames=frames();
            try{Object result=method.invoke(exactInput,args);value=(Long)result;return result;}
            catch(InvocationTargetException failure){exception=failure.getCause();throw exception;}
        }
        Object json(){return Json.map("delegate_reference",id(exactInput),"interceptor_reference",id(proxy),"method","editorLossObservation","descriptor","()J","calls",calls,"actual_return_long",value,"actual_exception_reference",id(exception),"actual_exception_type",exception==null?null:exception.getClass().getName(),"actual_exception_message",exception==null?null:exception.getMessage(),"production_call_frames",callFrames,"instrumentation_only_no_native_callback",true);}
        void site(String owner,String method,String descriptor,int bci){check(calls==1,"one actual Input invocation");check(callFrames.size()<24,"complete bounded product frames");check(callFrames.stream().anyMatch(o->{Map<?,?> f=(Map<?,?>)o;return owner.replace('/','.').equals(f.get("class"))&&method.equals(f.get("method"))&&descriptor.equals(f.get("descriptor"))&&Integer.valueOf(bci).equals(f.get("bci"));}),"exact Input caller BCI and descriptor");}
    }
    private record FrozenField(NativeAppearanceViewsV2.FieldPreservation reference,NativeAppearanceViewsV2.NativeField field,NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.Mutation original,NativeAppearanceViewsV2.Binding selected,Editable editable,NativeRenderer renderer,Object candidate,Object journal,NativeAppearanceViewsV2.Binding before,Object predecessor,Object disposition,long loss,Object snapshot,int phase,boolean entered,boolean ended,boolean checking,boolean counted,boolean released,boolean releaseReady,int callbacks,ArrayDeque<String> hooks,List<String> hookValues){
        static FrozenField of(NativeAppearanceViewsV2.FieldPreservation p){return new FrozenField(p,p.field,p.record,p.original,p.selected,p.editable,p.renderer,p.candidate,p.journal,p.before,p.predecessor,p.disposition,p.lossObservation,p.snapshot,p.phase,p.entered,p.ended,p.checking,p.counted,p.released,p.releaseReady,p.callbacks,p.hooks,List.copyOf(p.hooks));}
        Object json(){return Json.map("reference",id(reference),"field",id(field),"record",id(record),"original",id(original),"selected",id(selected),"editable",id(editable),"renderer",id(renderer),"candidate",id(candidate),"journal",id(journal),"before",id(before),"predecessor",id(predecessor),"disposition",id(disposition),"loss_observation",loss,"snapshot",id(snapshot),"phase",phase,"entered",entered,"ended",ended,"checking",checking,"counted",counted,"released",released,"release_ready",releaseReady,"callbacks",callbacks,"hooks_reference",id(hooks),"hooks_values",hookValues);}
    }
    private record FrozenReplacement(NativeAppearanceViewsV2.Replacement reference,NativeAppearanceViewsV2.NativeField field,NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.Mutation original,Editable oldEditable,Object predecessor,long loss,String stage,Editable nextEditable,CharSequence proposal,String eventValue,boolean registered,boolean nativeExecuting,boolean setterActive,boolean started,boolean setterReturned,boolean watcherSeen,boolean lost,boolean completed,boolean eventClaimed,boolean eventEvaluating,int setterCalls,int callbacks,ArrayDeque<String> hooks,List<String> hookValues){
        static FrozenReplacement of(NativeAppearanceViewsV2.Replacement r){return new FrozenReplacement(r,r.field,r.record,r.original,r.oldEditable,r.predecessor,r.lossObservation,r.stage.name(),r.nextEditable,r.proposal,r.eventValue,r.registered,r.nativeExecuting,r.setterActive,r.started,r.setterReturned,r.watcherSeen,r.lost,r.completed,r.eventClaimed,r.eventEvaluating,r.setterCalls,r.callbacks,r.hooks,List.copyOf(r.hooks));}
        Object json(){return Json.map("reference",id(reference),"field",id(field),"record",id(record),"original",id(original),"old_editable",id(oldEditable),"predecessor",id(predecessor),"loss_observation",loss,"stage",stage,"next_editable",id(nextEditable),"proposal",id(proposal),"event_value",eventValue,"registered",registered,"native_executing",nativeExecuting,"setter_active",setterActive,"started",started,"setter_returned",setterReturned,"watcher_seen",watcherSeen,"lost",lost,"completed",completed,"event_claimed",eventClaimed,"event_evaluating",eventEvaluating,"setter_calls",setterCalls,"callbacks",callbacks,"hooks_reference",id(hooks),"hooks_values",hookValues);}
    }
    private record Shared(NativeAppearanceViewsV2.Input input,Object scope,Object attempt,Object binding,Object pending,Object journal,Object operation,Object presentation,long loss,List<Integer> counts,int events){
        static Shared capture(){return new Shared(field.record.input,field.record.fieldPreservation,get(field,"attempt"),field.record.binding,get(renderer,"v2Pending"),get(candidate,"journal"),get(fence,"operation"),get(fence,"presentation"),(Long)get(renderer,"editorLossSerial"),FieldFiniteControls.counts(),ConcreteHostProbe.events().size());}
        void unchanged(){check(equals(capture()),"all selected shared identities, loss, counts, native events restored exactly");}
    }
    private static void row(String owner,String method,String descriptor,String branch,Object expected,Object before,Object after,Object result,InputObservation observation,Throwable exception){
        check(counts().equals(List.of(2,2,3)),"ordinary held/shared counts preserved");
        rows.add(Json.map("subject_id",owner+"#"+method+descriptor,"class_sha256",owner.equals(FP)?"b2303f133ba416b0b35ccaf714da5d8d53c9f1d436cf8d0687d932367c474099":"bead2d12c5532c594e456c0d736d407565b1d450a5917d3def39226a60309cf2","original_required_cases_retained",true,"finite_case",branch,"native_callback_state","not-applicable-no-fabricated-native-callback","independent_expected_before_invocation",expected,"actual_before",before,"actual_after",after,"completion",exception==null?"normal":"exact-actual-input-exception","actual_result",result,"exact_exception_reference",id(exception),"input_observation",observation==null?null:observation.json(),"counts_before",List.of(2,2,3),"counts_after",counts(),"shared_mutations_restored",true,"no_native_events",true,"no_membership_release_authority",true));
    }
    private static NativeAppearanceViewsV2.FieldPreservation fieldConstructor(String branch,long serial,boolean nullPredecessor,boolean nullArguments,boolean nullBefore,NativeAppearanceViewsV2.NativeField.Close close,boolean alterClose){
        Shared shared=Shared.capture();InputObservation observer=new InputObservation();NativeAppearanceViewsV2.FieldPreservation result;
        var original=nullArguments?null:originalScope.original;var selected=nullArguments?null:originalScope.selected;var editable=nullArguments?null:originalScope.editable;
        NativeRenderer selectedRenderer=nullArguments?null:renderer;NativeRenderer.Candidate selectedCandidate=nullArguments?null:(NativeRenderer.Candidate)candidate;NativeRenderer.AttachmentJournal selectedJournal=nullArguments?null:(NativeRenderer.AttachmentJournal)journal;
        Object predecessor=nullPredecessor?null:get(field,"attempt");Object disposition=predecessor==null?null:alterClose?close:get(predecessor,"close");Object before=nullBefore?null:field.record.binding;
        Object expected=Json.map("field",id(field),"record",id(field.record),"original",id(original),"selected",id(selected),"editable",id(editable),"renderer",id(selectedRenderer),"candidate",id(selectedCandidate),"journal",id(selectedJournal),"before",id(before),"predecessor",id(predecessor),"disposition",id(disposition),"loss_observation",serial,"snapshot",null,"phase",0,"all_flags_false",true,"callbacks",0,"hooks","fresh empty java.util.ArrayDeque");
        try(Changes changes=new Changes()){
            changes.set(renderer,"editorLossSerial",serial);changes.set(field.record,"input",observer.proxy);if(nullPredecessor)changes.set(field,"attempt",null);if(nullBefore)changes.set(field.record,"binding",null);if(alterClose&&predecessor!=null)changes.set(predecessor,"close",close);
            result=new NativeAppearanceViewsV2.FieldPreservation(field,original,selected,editable,selectedRenderer,selectedCandidate,selectedJournal);var actual=FrozenField.of(result);
            check(actual.field==field&&actual.record==field.record&&actual.original==original&&actual.selected==selected&&actual.editable==editable&&actual.renderer==selectedRenderer&&actual.candidate==selectedCandidate&&actual.journal==selectedJournal,"literal FieldPreservation captured argument identities");
            check(actual.before==before&&actual.predecessor==predecessor&&actual.disposition==disposition&&actual.loss==serial,"literal FieldPreservation captured prior identities and actual long");
            check(actual.snapshot==null&&actual.phase==0&&!actual.entered&&!actual.ended&&!actual.checking&&!actual.counted&&!actual.released&&!actual.releaseReady&&actual.callbacks==0,"literal FieldPreservation default state");
            check(actual.hooks.getClass()==ArrayDeque.class&&actual.hookValues.isEmpty()&&constructorHooks.put(actual.hooks,Boolean.TRUE)==null&&actual.hooks!=originalScope.hooks,"fresh exact constructor hook deque");observer.site(FP,"<init>",FD,116);check(observer.value==serial&&observer.exception==null,"actual Input returned long captured exactly");
        }
        shared.unchanged();row(FP,"<init>",FD,branch,expected,null,FrozenField.of(result).json(),id(result),observer,null);return result;
    }
    private static NativeAppearanceViewsV2.Replacement replacementConstructor(String branch,long loss,boolean nullPredecessor,boolean nullArguments,boolean nullInput){
        Shared shared=Shared.capture();InputObservation observer=new InputObservation();var original=nullArguments?null:originalScope.original;var editable=nullArguments?null:originalScope.editable;Object predecessor=nullPredecessor?null:get(field,"attempt");NativeAppearanceViewsV2.Replacement result;
        Object expected=Json.map("field",id(field),"record",id(field.record),"original",id(original),"old_editable",id(editable),"predecessor",id(predecessor),"loss_observation",loss,"stage","SNAPSHOTTING","next_editable",null,"proposal",null,"event_value",null,"all_flags_false",true,"setter_calls",0,"callbacks",0,"hooks","fresh empty java.util.ArrayDeque","Input_calls",0);
        try(Changes changes=new Changes()){
            changes.set(field.record,"input",nullInput?null:observer.proxy);if(nullPredecessor)changes.set(field,"attempt",null);
            result=new NativeAppearanceViewsV2.Replacement(field,original,editable,loss);var a=FrozenReplacement.of(result);
            check(a.field==field&&a.record==field.record&&a.original==original&&a.oldEditable==editable&&a.predecessor==predecessor&&a.loss==loss,"literal Replacement captured identities and supplied full long");
            check(a.stage.equals("SNAPSHOTTING")&&a.nextEditable==null&&a.proposal==null&&a.eventValue==null&&!a.registered&&!a.nativeExecuting&&!a.setterActive&&!a.started&&!a.setterReturned&&!a.watcherSeen&&!a.lost&&!a.completed&&!a.eventClaimed&&!a.eventEvaluating&&a.setterCalls==0&&a.callbacks==0,"literal Replacement complete defaults");
            check(a.hooks.getClass()==ArrayDeque.class&&a.hookValues.isEmpty()&&constructorHooks.put(a.hooks,Boolean.TRUE)==null,"fresh exact Replacement hook deque");check(observer.calls==0,"Replacement constructor never calls Input");
        }
        shared.unchanged();row(RP,"<init>",RD,branch,expected,null,FrozenReplacement.of(result).json(),id(result),observer,null);return result;
    }
    private static void endReady(NativeAppearanceViewsV2.FieldPreservation p,String branch,int mask,int callbackValue,boolean foreign,int ignoredPhase){
        Shared shared=Shared.capture();FrozenField actualBefore,actualAfter;boolean result;boolean expected=mask==63;
        Object oracle=Json.map("mask_bit_order",List.of("entered","ended","registration_null","callbacks_zero","hooks_empty","not_checking"),"mask",mask,"expected",expected,"only_true_mask",63,"callbacks_if_nonzero",callbackValue,"ignored_phase",ignoredPhase);
        try(Changes changes=new Changes()){
            changes.set(p,"entered",(mask&1)!=0);changes.set(p,"ended",(mask&2)!=0);changes.set(field.record,"fieldPreservation",(mask&4)!=0?null:foreign?originalScope:p);changes.set(p,"callbacks",(mask&8)!=0?0:callbackValue);if((mask&16)==0)p.hooks.push("literal guard hook");changes.set(p,"checking",(mask&32)==0);changes.set(p,"phase",ignoredPhase);changes.set(p,"counted",true);changes.set(p,"released",true);changes.set(p,"releaseReady",true);
            try{actualBefore=FrozenField.of(p);result=p.endReady();actualAfter=FrozenField.of(p);check(actualBefore.equals(actualAfter),"endReady typed receiver snapshot unchanged");check(result==expected,"literal exhaustive endReady truth table");}
            finally{if((mask&16)==0)p.hooks.pop();}
        }
        shared.unchanged();row(FP,"endReady","()Z",branch,oracle,actualBefore.json(),actualAfter.json(),result,null,null);
    }
    private static Throwable[] execute(boolean worker,Runnable call){Throwable[] escaped={null};if(!worker){try{call.run();}catch(RuntimeException|Error failure){escaped[0]=failure;}return escaped;}
        Thread thread=new Thread(()->{try{call.run();}catch(RuntimeException|Error failure){escaped[0]=failure;}},"finite-host-Input-wrong-thread");thread.setDaemon(true);workersStarted++;thread.start();try{thread.join(5000);}catch(InterruptedException failure){Thread.currentThread().interrupt();throw new AssertionError(failure);}if(thread.isAlive()){thread.interrupt();throw new AssertionError("bounded host worker did not terminate");}workersReaped++;return escaped;
    }
    private static void unchangedLoss(NativeAppearanceViewsV2.Replacement r,String branch,long stored,long serial,boolean lost,boolean worker,Boolean expected){
        Shared shared=Shared.capture();InputObservation observer=new InputObservation();FrozenReplacement before,after;boolean[] actual={false};Throwable exception;
        Object oracle=Json.map("stored_long",stored,"actual_Input_long_if_called",serial,"lost",lost,"wrong_thread",worker,"expected_boolean",expected,"expected_Input_calls",lost?0:1,"expected_exception",worker&&!lost?"java.lang.IllegalStateException: V2 requires UI owner thread":null);
        try(Changes changes=new Changes()){
            changes.set(r,"lossObservation",stored);changes.set(r,"lost",lost);changes.set(renderer,"editorLossSerial",serial);changes.set(field.record,"input",observer.proxy);before=FrozenReplacement.of(r);exception=execute(worker,()->actual[0]=r.unchangedLoss())[0];after=FrozenReplacement.of(r);check(before.equals(after),"unchangedLoss typed receiver snapshot unchanged");
            if(lost){check(!actual[0]&&exception==null&&observer.calls==0&&observer.value==null&&observer.exception==null,"lost exact short-circuit calls no Input even off owner thread");}
            else{observer.site(RP,"unchangedLoss","()Z",14);if(worker){check(exception==observer.exception&&exception instanceof IllegalStateException&&exception.getMessage().equals("V2 requires UI owner thread")&&observer.value==null,"exact actual Input requireMain exception propagated by identity");}else check(exception==null&&observer.exception==null&&observer.value==serial&&actual[0]==expected,"literal exact 64-bit equality against actual Input result");}
        }
        shared.unchanged();row(RP,"unchangedLoss","()Z",branch,oracle,before.json(),after.json(),exception==null?actual[0]:null,observer,exception);
    }
    private static void wrongThreadConstructor(){
        Shared shared=Shared.capture();InputObservation observer=new InputObservation();Object[] result={null};Throwable exception;
        try(Changes changes=new Changes()){
            changes.set(field.record,"input",observer.proxy);exception=execute(true,()->result[0]=new NativeAppearanceViewsV2.FieldPreservation(field,originalScope.original,originalScope.selected,originalScope.editable,renderer,(NativeRenderer.Candidate)candidate,(NativeRenderer.AttachmentJournal)journal))[0];
            observer.site(FP,"<init>",FD,116);check(result[0]==null&&exception==observer.exception&&exception instanceof IllegalStateException&&exception.getMessage().equals("V2 requires UI owner thread")&&observer.value==null,"throwing constructor exposes no partial receiver and preserves exact actual Input exception");
        }
        shared.unchanged();row(FP,"<init>",FD,"actual-Input-wrong-thread",Json.map("normal_receiver_observable",false,"exception","java.lang.IllegalStateException: V2 requires UI owner thread","exact_actual_Input_exception",true),null,null,null,observer,exception);
    }
    private static void matrix(){
        var previous=ConcreteHostProbe.hook;ConcreteHostProbe.hook=null;
        try{
            long[] captures={0,1,-1,Long.MIN_VALUE,Long.MAX_VALUE-1};NativeAppearanceViewsV2.FieldPreservation p=null;
            for(long serial:captures)p=fieldConstructor("actual-Input-long-"+serial,serial,false,false,false,null,false);
            fieldConstructor("null-predecessor",17,true,false,false,null,false);fieldConstructor("null-optional-arguments",19,false,true,false,null,false);fieldConstructor("null-before-binding",23,false,false,true,null,false);fieldConstructor("null-disposition",29,false,false,false,null,true);
            for(var close:NativeAppearanceViewsV2.NativeField.Close.values())fieldConstructor("exact-disposition-"+close,31,false,false,false,close,true);
            wrongThreadConstructor();
            for(int mask=0;mask<64;mask++)endReady(p,"truth-table-"+mask,mask,1,false,0);
            endReady(p,"negative-callback",55,-1,false,0);endReady(p,"recursion-limit-callback",55,16,false,0);endReady(p,"foreign-registration",59,1,true,0);
            for(int phase=0;phase<9;phase++)endReady(p,"ignored-phase-"+phase,63,1,false,phase);
            NativeAppearanceViewsV2.Replacement r=null;for(long loss:new long[]{0,1,-1,Long.MIN_VALUE,Long.MAX_VALUE-1,Long.MAX_VALUE})r=replacementConstructor("supplied-long-"+loss,loss,false,false,false);
            replacementConstructor("null-predecessor",37,true,false,false);replacementConstructor("null-optional-arguments",41,false,true,false);replacementConstructor("null-input-no-call",43,false,false,true);
            long[][] pairs={{0,0},{0,1},{1,0},{-1,-1},{Long.MIN_VALUE,Long.MIN_VALUE},{Long.MAX_VALUE,Long.MAX_VALUE-1},{Long.MAX_VALUE-1,Long.MAX_VALUE-1},{1,4294967297L},{Long.MIN_VALUE,0},{0,Long.MIN_VALUE}};
            boolean[] equality={true,false,false,true,true,false,true,false,false,false};
            for(int i=0;i<pairs.length;i++){unchangedLoss(r,"literal-equality-"+i,pairs[i][0],pairs[i][1],false,false,equality[i]);unchangedLoss(r,"lost-short-circuit-"+i,pairs[i][0],pairs[i][1],true,false,false);}
            unchangedLoss(r,"actual-Input-wrong-thread",0,0,false,true,null);unchangedLoss(r,"lost-off-thread-short-circuit",0,Long.MAX_VALUE,true,true,false);
        }finally{ConcreteHostProbe.hook=previous;}
    }
    private static void write(StringBuilder out,Object value){if(value instanceof Map<?,?> map){out.append('{');boolean comma=false;for(var entry:map.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,entry.getKey());out.append(':');write(out,entry.getValue());}out.append('}');}else if(value instanceof Iterable<?> iterable){out.append('[');boolean comma=false;for(Object item:iterable){if(comma)out.append(',');comma=true;write(out,item);}out.append(']');}else if(value instanceof Number n)out.append(n);else Json.write(out,value);}
    private static void hash(Class<?> type,String expected)throws Exception{try(var stream=type.getResourceAsStream("/"+type.getName().replace('.','/')+".class")){check(stream!=null,"loaded exact product class");check(java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(stream.readAllBytes())).equals(expected),"exact loaded subject class");}}
    public static void main(String[] args)throws Exception{
        Class<?> fixtureClass=Class.forName("dev.mixer.android.SelectedIdentityMembershipReviewControls$Fixture");put(Class.forName("dev.mixer.android.SelectedIdentityMembershipReviewControls"),"descriptor",Files.readAllBytes(Path.of(args[0])));Constructor<?> constructor=fixtureClass.getDeclaredConstructor(boolean.class,boolean.class);constructor.setAccessible(true);
        Constructor<?> fp=NativeAppearanceViewsV2.FieldPreservation.class.getDeclaredConstructors()[0],rp=NativeAppearanceViewsV2.Replacement.class.getDeclaredConstructors()[0];check(MethodType.methodType(void.class,fp.getParameterTypes()).toMethodDescriptorString().equals(FD)&&MethodType.methodType(void.class,rp.getParameterTypes()).toMethodDescriptorString().equals(RD),"exact frozen constructor descriptors");hash(NativeAppearanceViewsV2.FieldPreservation.class,"b2303f133ba416b0b35ccaf714da5d8d53c9f1d436cf8d0687d932367c474099");hash(NativeAppearanceViewsV2.Replacement.class,"bead2d12c5532c594e456c0d736d407565b1d450a5917d3def39226a60309cf2");
        try{
            fixture=construct(constructor,true,true);renderer=(NativeRenderer)get(fixture,"renderer");field=(NativeAppearanceViewsV2.NativeField)get(fixture,"a");fence=get(fixture,"fence");exactInput=field.record.input;
            ConcreteHostProbe.hook=(method,phase)->{var event=ConcreteHostProbe.lastEvent();if(!entered&&method.equals("View.invalidate")&&phase.equals("entry")&&event.receiver==field&&field.record.fieldPreservation!=null){entered=true;originalScope=field.record.fieldPreservation;candidate=get(renderer,"v2Pending");journal=get(candidate,"journal");for(var frame:event.productionFrames)boundary.add(Json.map("class",frame.className(),"method",frame.methodName(),"descriptor",frame.descriptor(),"bci",frame.bytecodeIndex(),"line",frame.line()));check(event.productionFrames.size()<24,"ordinary boundary full frames");check(counts().equals(List.of(2,2,3)),"ordinary selected preservation boundary counts");matrix();}};
            check(Boolean.TRUE.equals(invoke(fixture,"edit")),"actual original edit completes after every restore");ConcreteHostProbe.hook=null;check(entered&&counts().equals(List.of(0,0,0))&&field.record.fieldPreservation==null,"actual original final counts and registration");check(workersStarted==3&&workersReaped==3,"all three bounded host threads joined");
            StringBuilder out=new StringBuilder();write(out,Json.map("schema",1,"scope","exact four FieldPreservation/Replacement finite host bodies","source_context",CONTEXT,"original_fixture","exact SelectedIdentityMembershipReviewControls$Fixture(true,true)","original_boundary",boundary,"original_boundary_counts",List.of(2,2,3),"original_edit_completed_after_restores",true,"original_final_counts",counts(),"checks",checks,"invocations",rows.size(),"host_threads_started",workersStarted,"host_threads_joined",workersReaped,"rows",rows,"limits",List.of("Original required categories, semantic cases and enclosing obligations remain pending; these finite rows grant no membership or release authority.","Actual Input results and wrong-thread exceptions are observed through a forwarding instrumentation-only interceptor; no native callback states are fabricated.","Runtime allocation failures and exceptional constructor receiver/partial fields are unobserved.","Actual Input Long.MAX_VALUE exhaustion terminal path is not executed or credited.","Host leaves are finite models; native/UI/capture/process inventories remain paused.")));Files.writeString(Path.of(args[1]),out+"\n");System.out.println("PASS four exact FieldPreservation/Replacement bodies: "+rows.size()+" invocations, "+checks+" checks; host only");
        }finally{ConcreteHostProbe.hook=null;if(fixture!=null)invoke(fixture,"close");}
    }
}
