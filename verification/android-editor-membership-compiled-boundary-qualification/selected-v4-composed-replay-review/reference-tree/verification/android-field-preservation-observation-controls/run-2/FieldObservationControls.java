package dev.mixer.android;

import android.text.Editable;
import java.lang.invoke.MethodType;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
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

/** Four exact FieldPreservation observation bodies, with literal oracles; no membership or release authority. */
public final class FieldObservationControls {
    private FieldObservationControls() {}
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
        void set(Object receiver,String name,Object value){check(!Modifier.isFinal(reflected(receiver,name).getModifiers()),"no final field mutation");changes.add(new Change(receiver,name,get(receiver,name)));put(receiver,name,value);}
        @Override public void close(){for(int i=changes.size()-1;i>=0;i--){var c=changes.get(i);put(c.receiver,c.name,c.prior);}}
    }
    private static List<Integer> counts(){return List.of((Integer)get(candidate,"heldPreservations"),(Integer)get(renderer,"outstandingFieldPreservations"),(Integer)get(renderer,"outstandingEditorNativeCalls"));}
    private static List<Object> frames(){return StackWalker.getInstance(StackWalker.Option.RETAIN_CLASS_REFERENCE).walk(stream->stream.filter(f->f.getClassName().startsWith("dev.mixer.android.Native")).map(f->(Object)Json.map("class",f.getClassName(),"method",f.getMethodName(),"descriptor",f.getDescriptor(),"bci",f.getByteCodeIndex(),"line",f.getLineNumber())).toList());}
    private record FrozenField(NativeAppearanceViewsV2.FieldPreservation reference,NativeAppearanceViewsV2.NativeField field,NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.Mutation original,NativeAppearanceViewsV2.Binding selected,Editable editable,NativeRenderer renderer,Object candidate,Object journal,NativeAppearanceViewsV2.Binding before,Object predecessor,Object disposition,long loss,Object snapshot,int phase,boolean entered,boolean ended,boolean checking,boolean counted,boolean released,boolean releaseReady,int callbacks,ArrayDeque<String> hooks,List<String> hookValues){
        static FrozenField of(NativeAppearanceViewsV2.FieldPreservation p){return new FrozenField(p,p.field,p.record,p.original,p.selected,p.editable,p.renderer,p.candidate,p.journal,p.before,p.predecessor,p.disposition,p.lossObservation,p.snapshot,p.phase,p.entered,p.ended,p.checking,p.counted,p.released,p.releaseReady,p.callbacks,p.hooks,List.copyOf(p.hooks));}
        Object json(){return Json.map("reference",id(reference),"field",id(field),"record",id(record),"original",id(original),"selected",id(selected),"editable",id(editable),"renderer",id(renderer),"candidate",id(candidate),"journal",id(journal),"before",id(before),"predecessor",id(predecessor),"disposition",id(disposition),"loss_observation",loss,"snapshot",id(snapshot),"phase",phase,"entered",entered,"ended",ended,"checking",checking,"counted",counted,"released",released,"release_ready",releaseReady,"callbacks",callbacks,"hooks_reference",id(hooks),"hooks_values",hookValues);}
    }
    private record Shared(NativeAppearanceViewsV2.Input input,Object scope,Object attempt,Object binding,Object pending,Object journal,Object operation,Object presentation,long loss,List<Integer> counts,int events){
        static Shared capture(){return new Shared(field.record.input,field.record.fieldPreservation,get(field,"attempt"),field.record.binding,get(renderer,"v2Pending"),get(candidate,"journal"),get(fence,"operation"),get(fence,"presentation"),(Long)get(renderer,"editorLossSerial"),FieldObservationControls.counts(),0);}
        void unchanged(){check(equals(capture()),"all selected shared identities, loss, counts, native events restored exactly");}
    }
    private static final List<Object> getterOutcomes=new ArrayList<>();
    private static Throwable failureLatch;
    private static int getterEntries,checkingEntries;
    private static final class GetterFailure extends RuntimeException {
        private static final long serialVersionUID=1L;
        GetterFailure(){super("bounded host getter injection");}
    }
    private record SnapshotValue(NativeAppearanceViewsV2.EditorSnapshot reference,String textReference,String text,int start,int end,String spansReference,List<String> spanIdentities,String boundsReference,List<Integer> bounds){
        static SnapshotValue of(NativeAppearanceViewsV2.EditorSnapshot s){if(s==null)return null;return new SnapshotValue(s,id(s.text),s.text,s.start,s.end,id(s.spans),java.util.Arrays.stream(s.spans).map(FieldObservationControls::id).toList(),id(s.bounds),java.util.Arrays.stream(s.bounds).boxed().toList());}
        Object json(){return Json.map("type","NativeAppearanceViewsV2$EditorSnapshot","field_order",List.of("text:String","start:int","end:int","spans:Object[]","bounds:int[]"),"reference",id(reference),"text_reference",textReference,"text_value",text,"start",start,"end",end,"spans_array_reference",spansReference,"span_identities_in_order",spanIdentities,"bounds_array_reference",boundsReference,"bounds_values_in_order",bounds);}
    }
    private record BufferValue(Editable reference,String text,int start,int end,List<Object> spans,List<Integer> bounds){
        static BufferValue of(){Editable e=originalScope.editable;List<Object> spans=List.of(e.getSpans(0,e.length(),Object.class));List<Integer> bounds=new ArrayList<>();for(Object span:spans){bounds.add(e.getSpanStart(span));bounds.add(e.getSpanEnd(span));bounds.add(e.getSpanFlags(span));}return new BufferValue(e,e.toString(),(Integer)get(field,"selectionStart"),(Integer)get(field,"selectionEnd"),List.copyOf(spans),List.copyOf(bounds));}
        void restore(){reference.clear();reference.append(text);for(int i=0;i<spans.size();i++)reference.setSpan(spans.get(i),bounds.get(3*i),bounds.get(3*i+1),bounds.get(3*i+2));put(field,"selectionStart",start);put(field,"selectionEnd",end);}
        Object json(){return Json.map("editable_reference",id(reference),"text",text,"selection_start",start,"selection_end",end,"span_identities",spans.stream().map(FieldObservationControls::id).toList(),"span_bounds_and_flags",bounds);}
    }
    private static void row(String method,String descriptor,String branch,Object oracle,FrozenField before,FrozenField after,SnapshotValue snapBefore,SnapshotValue snapAfter,Object result,Object input,Throwable exception,List<Object> getters){
        check(counts().equals(List.of(2,2,3)),"ordinary held/shared counts preserved");
        rows.add(Json.map("subject_id",FP+"#"+method+descriptor,"class_sha256","b2303f133ba416b0b35ccaf714da5d8d53c9f1d436cf8d0687d932367c474099","original_eight_cases_retained_without_discharge",true,"finite_case",branch,"independent_expected_before_invocation",oracle,"actual_before",before.json(),"actual_after",after.json(),"snapshot_before",snapBefore==null?null:snapBefore.json(),"snapshot_after",snapAfter==null?null:snapAfter.json(),"original_final_Input_reference",id(exactInput),"exact_Input_invocation_counts_and_BCIs","pending: original final Input unchanged; no forwarding interceptor","actual_method_completion",exception==null?"normal":"exception","actual_result",result,"exact_exception_reference",id(exception),"exception_type",exception==null?null:exception.getClass().getName(),"exception_message",exception==null?null:exception.getMessage(),"actual_Input",input,"actual_native_getter_outcomes",getters,"counts_before",List.of(2,2,3),"counts_after",counts(),"restored_before_original_edit_resumes",true,"no_membership_release_authority",true));
    }
    private static Throwable call(Runnable action){try{action.run();return null;}catch(RuntimeException|Error failure){return failure;}}
    private static Throwable worker(Runnable action){Throwable[] result={null};Thread thread=new Thread(()->result[0]=call(action),"field-observation-bounded-host-thread");thread.setDaemon(true);workersStarted++;thread.start();try{thread.join(5000);}catch(InterruptedException failure){Thread.currentThread().interrupt();throw new AssertionError(failure);}if(thread.isAlive()){thread.interrupt();throw new AssertionError("bounded host thread failed to terminate");}workersReaped++;return result[0];}
    private static void tuple(String branch,int mask,String fieldName,Object value,Long serial,boolean offThread){
        Shared shared=Shared.capture();var scope=originalScope;Object input=null;FrozenField before,after;SnapshotValue snapshot=SnapshotValue.of(scope.snapshot);boolean[] actual={false};Throwable escaped;int oldGetters=getterOutcomes.size();
        boolean expected=mask==15&&fieldName==null&&(serial==null||serial.longValue()==scope.lossObservation)&&!offThread;
        Object oracle=Json.map("early_guard_bit_order",List.of("entered","counted","not_ended","exact_registration"),"mask",mask,"perturbed_nonfinal_field",fieldName,"actual_loss_serial",serial,"stored_loss_long",scope.lossObservation,"expected_boolean",offThread&&mask==15?null:expected,"expected_exception",offThread&&mask==15?"V2 requires UI owner thread":null,"exact_Input_invocation_count_and_BCI","pending: final original Input preserved unchanged");
        try(Changes changes=new Changes()){
            changes.set(scope,"entered",(mask&1)!=0);changes.set(scope,"counted",(mask&2)!=0);changes.set(scope,"ended",(mask&4)==0);changes.set(field.record,"fieldPreservation",(mask&8)!=0?scope:null);
            if(fieldName!=null){Object receiver=fieldName.startsWith("record.")?field.record:field;changes.set(receiver,fieldName.replace("record.",""),value);}
            if(serial!=null){check(serial!=Long.MAX_VALUE,"no loss exhaustion mutation");changes.set(renderer,"editorLossSerial",serial);}
            before=FrozenField.of(scope);escaped=offThread?worker(()->actual[0]=scope.tuple()):call(()->actual[0]=scope.tuple());after=FrozenField.of(scope);check(before.equals(after)&&snapshot.equals(SnapshotValue.of(scope.snapshot)),"tuple has no receiver/snapshot effects");
            if(offThread&&mask==15){check(escaped instanceof IllegalStateException&&escaped.getMessage().equals("V2 requires UI owner thread"),"actual renderer owner-thread exception before later tuple guards; Input tracing pending");}
            else{check(escaped==null&&actual[0]==expected,"literal tuple guard result");check(field.record.input==exactInput,"actual final Input reference unchanged");}
            check(getterOutcomes.size()==oldGetters,"tuple calls no native getter");
        }
        shared.unchanged();row("tuple","()Z",branch,oracle,before,after,snapshot,snapshot,escaped==null?actual[0]:null,null,escaped,List.of());
    }
    private static void installGetter(String mutation,Changes changes,BufferValue buffer,GetterFailure marker){
        ConcreteHostProbe.hook=(method,phase)->{
            if(!method.equals("TextView.getEditableText")||!phase.equals("entry"))return;
            var event=ConcreteHostProbe.lastEvent();if(event.receiver!=field)return;
            getterEntries++;check(originalScope.checking,"checking true at actual nativeEditable getter entry");checkingEntries++;
            check(event.productionFrames.size()<24,"actual getter full production frames; saturated frames refused");
            if(mutation.equals("throw"))throw marker;
            if(mutation.equals("foreign-buffer"))changes.set(field,"text",new android.text.SpannableStringBuilder(buffer.text));
            if(mutation.equals("text"))originalScope.editable.replace(0,originalScope.editable.length(),buffer.text+"!");
            if(mutation.equals("selection-start"))changes.set(field,"selectionStart",buffer.start==0?1:0);
            if(mutation.equals("selection-end"))changes.set(field,"selectionEnd",buffer.end==0?1:0);
            if(mutation.equals("composing-added"))originalScope.editable.setSpan(new Object(),0,0,android.text.Spanned.SPAN_COMPOSING);
            if(mutation.startsWith("composing-")&&!mutation.equals("composing-added")){Object first=buffer.spans.get(0);int start=buffer.bounds.get(0),end=buffer.bounds.get(1),flags=buffer.bounds.get(2);switch(mutation){case "composing-removed"->buffer.reference.removeSpan(first);case "composing-start"->buffer.reference.setSpan(first,start+1,end,flags);case "composing-end"->buffer.reference.setSpan(first,start,end+1,flags);case "composing-flags"->buffer.reference.setSpan(first,start,end,flags|16);case "composing-order"->buffer.reference.setSpan(first,start,end,flags);default->throw new AssertionError(mutation);}}
            if(mutation.equals("noncomposing-added"))originalScope.editable.setSpan(new Object(),0,0,0);
            if(mutation.equals("tuple-lost"))changes.set(originalScope,"ended",true);
            if(mutation.equals("reentrant")){int before=getterEntries;Throwable nested=call(()->originalScope.exact());check(nested instanceof IllegalStateException&&nested.getMessage().equals("lost exact field preservation")&&originalScope.checking&&getterEntries==before,"reentrant exact fails before another getter and leaves outer checking true");}
        };
    }
    private static Object mutationValue(NativeAppearanceViewsV2.Mutation mutation){return Json.map("reference",id(mutation),"mode",mutation.mode.name(),"fence",id(mutation.fence),"token",id(mutation.token),"editor_lease",id(mutation.editorLease),"replacement_lease",id(mutation.replacementLease),"field_lease",id(mutation.fieldLease));}
    private static NativeAppearanceViewsV2.EditorSnapshot observation(String method,String branch,String guard,String getterMutation){
        Shared shared=Shared.capture();var scope=originalScope;FrozenField before,after;SnapshotValue snapBefore,snapAfter;BufferValue buffer=BufferValue.of();Object input=null;Object[] result={null};Throwable escaped;GetterFailure marker=new GetterFailure();int getterOffset=getterOutcomes.size(),entryOffset=getterEntries;List<Object> getters;
        String expectedException=guard!=null?(method.equals("capture")?"invalid preserved field entry":"lost exact field preservation"):getterMutation.equals("throw")?marker.getMessage():List.of("foreign-buffer","text","selection-start","selection-end","composing-added","composing-removed","composing-start","composing-end","composing-flags","composing-order","tuple-lost").contains(getterMutation)?"preserved field changed after getter":null;
        Object oracle=Json.map("method",method,"guard",guard,"getter_perturbation",getterMutation,"expected_exception_message",expectedException,"expected_checking_after",guard!=null&&guard.equals("checking"),"actual_original_mode",scope.original.mode.name(),"actual_original_fence",id(scope.original.fence),"actual_original_token",id(scope.original.token),"expected_returned_Mutation_field_lease",method.equals("continuation")&&expectedException==null?id(scope):null,"getter_exception_origin",getterMutation.equals("throw")?"explicit host hook injection; same object escapes actual getter, not a platform-origin claim":null);
        try(Changes changes=new Changes()){
            changes.set(scope,"snapshot",scope.snapshot);changes.set(scope,"checking",scope.checking);
            if(guard!=null){if(guard.equals("snapshot"))changes.set(scope,"snapshot",null);else if(guard.equals("checking"))changes.set(scope,"checking",true);else changes.set(scope,"entered",false);}
            before=FrozenField.of(scope);snapBefore=SnapshotValue.of(scope.snapshot);installGetter(getterMutation,changes,buffer,marker);
            try{escaped=call(()->{switch(method){case "capture"->scope.capture();case "exact"->scope.exact();case "continuation"->result[0]=scope.continuation();default->throw new AssertionError(method);}});}
            finally{ConcreteHostProbe.hook=null;}
            after=FrozenField.of(scope);snapAfter=SnapshotValue.of(scope.snapshot);getters=List.copyOf(getterOutcomes.subList(getterOffset,getterOutcomes.size()));
            if(expectedException==null)check(escaped==null,"normal actual method completion");else check(escaped!=null&&escaped.getMessage().equals(expectedException),"exact failure message at method boundary");
            if(getterMutation.equals("throw"))check(escaped==marker&&getters.size()==1&&((Map<?,?>)getters.get(0)).get("exception_reference").equals(id(marker)),"identical injected host exception leaves actual getter and method");
            check(scope.checking==(guard!=null&&guard.equals("checking")),"checking resets after actual getter success/failure; preexisting early guard unchanged");
            if(guard!=null)check(getterEntries==entryOffset&&getters.isEmpty(),"early guard fails before getter");else check(getterEntries==entryOffset+1&&getters.size()==1,"one actual getter outcome");
            if(method.equals("capture")&&guard==null){check(scope.snapshot!=snapBefore.reference,"capture installs a fresh actual snapshot before exact");check(snapAfter.text.equals(buffer.text)&&snapAfter.start==buffer.start&&snapAfter.end==buffer.end,"capture retains independently read text and selection");List<String> expectedSpans=new ArrayList<>();List<Integer> expectedBounds=new ArrayList<>();for(int i=0;i<buffer.spans.size();i++)if((buffer.bounds.get(3*i+2)&android.text.Spanned.SPAN_COMPOSING)!=0){expectedSpans.add(id(buffer.spans.get(i)));expectedBounds.addAll(buffer.bounds.subList(3*i,3*i+3));}check(snapAfter.spanIdentities.equals(expectedSpans)&&snapAfter.bounds.equals(expectedBounds),"capture retains literal composing identities/bounds/flags in order");}
            else check(snapBefore==null?snapAfter==null:snapBefore.equals(snapAfter),"noncapture leaves exact snapshot values and identities unchanged");
            if(method.equals("continuation")&&escaped==null){var m=(NativeAppearanceViewsV2.Mutation)result[0];check(m!=scope.original&&m.mode==scope.original.mode&&m.fence==scope.original.fence&&m.token==scope.original.token&&m.fieldLease==scope&&m.editorLease==null&&m.replacementLease==null,"actual new Mutation captures original mode/fence/token and exact field identity");result[0]=mutationValue(m);}
            check(scope.field==field&&scope.record==field.record&&scope.original==before.original&&scope.editable==before.editable&&scope.renderer==renderer&&scope.candidate==candidate&&scope.journal==journal,"all original final fields untouched");
        }finally{buffer.restore();}
        shared.unchanged();check(buffer.equals(BufferValue.of()),"original buffer text selection spans restored exactly");
        row(method,method.equals("continuation")?"()Ldev/mixer/android/NativeAppearanceViewsV2$Mutation;":"()V",branch,oracle,before,after,snapBefore,snapAfter,result[0],null,escaped,getters);return after.snapshot instanceof NativeAppearanceViewsV2.EditorSnapshot snapshot?snapshot:null;
    }
    private static void compositionFamily(){
        Shared shared=Shared.capture();BufferValue original=BufferValue.of();
        try(Changes changes=new Changes()){
            changes.set(originalScope,"snapshot",originalScope.snapshot);
            original.reference.setSpan(new Object(),0,Math.min(2,original.reference.length()),android.text.Spanned.SPAN_COMPOSING|33);
            original.reference.setSpan(new Object(),0,Math.min(1,original.reference.length()),android.text.Spanned.SPAN_COMPOSING|17);
            original.reference.setSpan(new Object(),0,0,33);
            NativeAppearanceViewsV2.EditorSnapshot captured=observation("capture","seeded-two-real-composing-spans-and-noncomposing-span",null,"normal");
            changes.set(originalScope,"snapshot",captured);
            for(String mutation:List.of("normal","composing-removed","composing-start","composing-end","composing-flags","composing-order","noncomposing-added"))observation("exact","seeded-actual-getter-"+mutation,null,mutation);
        }finally{original.restore();}
        shared.unchanged();check(original.equals(BufferValue.of()),"composition family restores actual original buffer");
    }
    private static void matrix(){
        ConcreteHostProbe.hook=null;FrozenField originalFields=FrozenField.of(originalScope);BufferValue originalBuffer=BufferValue.of();check(originalScope.tuple(),"actual originally installed scope tuple is valid");check(originalScope.snapshot!=null,"ordinary transaction already captured actual snapshot");
        for(int mask=0;mask<16;mask++)tuple("four-early-guard-table-"+mask,mask,null,null,null,false);
        tuple("actual-field-depth",15,"depth",1,null,false);tuple("actual-field-finishing",15,"finishing",true,null,false);tuple("actual-field-permanent",15,"permanent",true,null,false);tuple("actual-record-constructed",15,"record.constructed",false,null,false);tuple("actual-record-null-binding",15,"record.binding",null,null,false);
        long stored=originalScope.lossObservation;for(long serial:new long[]{stored,stored^1L,stored^4294967296L,Long.MIN_VALUE,Long.MAX_VALUE-1,-1})tuple("actual-Input-loss-"+serial,15,null,null,serial,false);
        tuple("actual-renderer-owner-thread-exception",15,null,null,null,true);tuple("early-short-circuit-off-owner-thread",14,null,null,null,true);
        observation("capture","invalid-entry-preserves-snapshot","entered","normal");observation("capture","fresh-real-snapshot-and-postcheck",null,"normal");observation("capture","installed-snapshot-retained-on-getter-failure",null,"throw");
        observation("exact","checking-early-guard","checking","normal");observation("exact","null-snapshot-early-guard","snapshot","normal");observation("exact","invalid-tuple-early-guard","entered","normal");
        for(String mutation:List.of("normal","reentrant","throw","foreign-buffer","text","selection-start","selection-end","composing-added","tuple-lost"))observation("exact","actual-getter-"+mutation,null,mutation);
        compositionFamily();
        observation("continuation","actual-Mutation-captured-identity",null,"normal");observation("continuation","no-return-on-invalid-tuple","entered","normal");observation("continuation","exact-getter-exception-propagates",null,"throw");observation("continuation","no-return-on-content-change",null,"text");
        check(originalFields.equals(FrozenField.of(originalScope))&&originalBuffer.equals(BufferValue.of())&&field.record.input==exactInput,"entire actual original scope/buffer/Input restored before original transaction resumes");
    }
    private static void write(StringBuilder out,Object value){if(value instanceof Map<?,?> map){out.append('{');boolean comma=false;for(var entry:map.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,entry.getKey());out.append(':');write(out,entry.getValue());}out.append('}');}else if(value instanceof Iterable<?> iterable){out.append('[');boolean comma=false;for(Object item:iterable){if(comma)out.append(',');comma=true;write(out,item);}out.append(']');}else if(value instanceof Number n)out.append(n);else Json.write(out,value);}
    private static void hash(Class<?> type,String expected)throws Exception{try(var stream=type.getResourceAsStream("/"+type.getName().replace('.','/')+".class")){check(stream!=null,"loaded exact product class");check(java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(stream.readAllBytes())).equals(expected),"exact loaded subject class");}}
    public static void main(String[] args)throws Exception{
        Class<?> fixtureClass=Class.forName("dev.mixer.android.SelectedIdentityMembershipReviewControls$Fixture");put(Class.forName("dev.mixer.android.SelectedIdentityMembershipReviewControls"),"descriptor",Files.readAllBytes(Path.of(args[0])));Constructor<?> constructor=fixtureClass.getDeclaredConstructor(boolean.class,boolean.class);constructor.setAccessible(true);
        hash(NativeAppearanceViewsV2.FieldPreservation.class,"b2303f133ba416b0b35ccaf714da5d8d53c9f1d436cf8d0687d932367c474099");for(String method:List.of("tuple","capture","exact","continuation")){Method actual=NativeAppearanceViewsV2.FieldPreservation.class.getDeclaredMethod(method);check(MethodType.methodType(actual.getReturnType(),actual.getParameterTypes()).toMethodDescriptorString().equals(method.equals("tuple")?"()Z":method.equals("continuation")?"()Ldev/mixer/android/NativeAppearanceViewsV2$Mutation;":"()V"),"exact frozen method descriptor");}
        NativeOutcomeProbe.begin(outcome->{if(!outcome.method().equals("TextView.getEditableText")||outcome.receiver()!=field||!entered)return;try{check(outcome.productionFrames().size()<24,"actual outcome full frames; saturated frames refused");List<Object> frames=new ArrayList<>();for(var frame:outcome.productionFrames())frames.add(Json.map("class",frame.className(),"method",frame.methodName(),"descriptor",frame.descriptor(),"bci",frame.bytecodeIndex(),"line",frame.line()));getterOutcomes.add(Json.map("method",outcome.method(),"descriptor",outcome.descriptor(),"receiver",id(outcome.receiver()),"completion",outcome.completion(),"actual_value_reference",id(outcome.value()),"exception_reference",id(outcome.originalException()),"production_frames",frames,"checking_at_outcome",originalScope.checking));}catch(RuntimeException|Error failure){failureLatch=failure;throw failure;}});
        try{
            fixture=construct(constructor,true,true);renderer=(NativeRenderer)get(fixture,"renderer");field=(NativeAppearanceViewsV2.NativeField)get(fixture,"a");fence=get(fixture,"fence");exactInput=field.record.input;
            ConcreteHostProbe.hook=(method,phase)->{var event=ConcreteHostProbe.lastEvent();if(!entered&&method.equals("View.invalidate")&&phase.equals("entry")&&event.receiver==field&&field.record.fieldPreservation!=null){entered=true;originalScope=field.record.fieldPreservation;candidate=get(renderer,"v2Pending");journal=get(candidate,"journal");try{check(event.productionFrames.size()<24,"ordinary transaction full frames; saturated frames refused");for(var frame:event.productionFrames)boundary.add(Json.map("class",frame.className(),"method",frame.methodName(),"descriptor",frame.descriptor(),"bci",frame.bytecodeIndex(),"line",frame.line()));check(counts().equals(List.of(2,2,3)),"actual ordinary preservation counts");matrix();}catch(RuntimeException|Error failure){failureLatch=failure;throw failure;}}};
            boolean edited=Boolean.TRUE.equals(invoke(fixture,"edit"));ConcreteHostProbe.hook=null;if(failureLatch!=null)rethrow(failureLatch);check(edited,"unchanged original edit completes after all restores");check(entered&&counts().equals(List.of(0,0,0))&&field.record.fieldPreservation==null,"unchanged original final counts and registration");check(workersStarted==workersReaped&&workersStarted==2,"bounded two host threads joined");NativeOutcomeProbe.end();check(NativeOutcomeProbe.clean(),"passive observer clean, no swallowed evidence failure");
            StringBuilder out=new StringBuilder();write(out,Json.map("schema",1,"scope","exact FieldPreservation tuple/capture/exact/continuation source-specific finite host observations","source_context",CONTEXT,"original_fixture","unchanged SelectedIdentityMembershipReviewControls$Fixture(true,true)","original_boundary",boundary,"actual_original_boundary_counts",List.of(2,2,3),"original_edit_completed_after_restores",true,"actual_final_counts",counts(),"checks",checks,"invocations",rows.size(),"getter_entries",getterEntries,"checking_true_at_entries",checkingEntries,"host_threads_started",workersStarted,"host_threads_joined",workersReaped,"no_final_field_or_exhaustion_mutations",true,"failure_latch_clear",failureLatch==null,"rows",rows,"limits",List.of("Exact original Input invocation counts and BCIs remain pending because final Input is preserved without replacement.","All 280 original subjects and 189 historical dispositions plus five V1 sites remain unchanged; eight original semantic cases for each body remain pending.","Finite source-specific observations do not discharge enclosing operation, allocation failure, exceptional partial-output, membership, release, OTA or GA obligations.","Getter failures use explicit host hook injection and propagate the identical object; they are not native platform-origin failures.","Original mode/fence/token and final fields are observed unchanged, never fabricated or mutated.","Native runtime, physical, simulator/emulator, UI, capture and process inventories remain paused.")));Files.writeString(Path.of(args[1]),out+"\n");System.out.println("PASS four FieldPreservation observation bodies: "+rows.size()+" invocations, "+checks+" checks; host JVM only");
        }finally{ConcreteHostProbe.hook=null;if(fixture!=null)invoke(fixture,"close");if(!NativeOutcomeProbe.clean())NativeOutcomeProbe.end();}
    }
}
