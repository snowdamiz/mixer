package dev.mixer.android;

import android.text.Editable;
import android.text.SpannableStringBuilder;
import android.text.Spanned;
import android.view.View;
import android.widget.FrameLayout;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

/** Three independent finite host observations; no product decision or authority oracle. */
public final class IndependentConstructorControls {
    private IndependentConstructorControls() {}
    private static final List<Object> rows=new ArrayList<>();
    private static final IdentityHashMap<Object,Integer> ids=new IdentityHashMap<>();
    private static int checks;
    private static Object fixture,renderer,candidate,journal,fence,record,field,root;
    private static Constructor<?> stateConstructor,journalConstructor;
    private static boolean entered;
    private static void check(boolean value,String why){checks++;if(!value)throw new AssertionError(why);}
    private static String id(Object value){if(value==null)return "null";return value.getClass().getName()+"@"+ids.computeIfAbsent(value,key->ids.size()+1);}
    private static Field field(Object receiver,String name){
        for(Class<?> type=receiver instanceof Class<?> c?c:receiver.getClass();type!=null;type=type.getSuperclass())try{Field f=type.getDeclaredField(name);f.setAccessible(true);return f;}catch(NoSuchFieldException absent){/* inherited field */}
        throw new AssertionError(name);
    }
    private static Object get(Object receiver,String name){try{return field(receiver,name).get(receiver instanceof Class<?>?null:receiver);}catch(IllegalAccessException failure){throw new AssertionError(failure);}}
    private static void put(Object receiver,String name,Object value){try{field(receiver,name).set(receiver instanceof Class<?>?null:receiver,value);}catch(IllegalAccessException failure){throw new AssertionError(failure);}}
    private static Object construct(Constructor<?> constructor,Object... args){try{return constructor.newInstance(args);}catch(InvocationTargetException failure){throw new AssertionError("unexpected original exception",failure.getCause());}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static Object invoke(Object receiver,String name){for(Method m:receiver.getClass().getDeclaredMethods())if(m.getName().equals(name)&&m.getParameterCount()==0)try{m.setAccessible(true);return m.invoke(receiver);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}throw new AssertionError(name);}
    private static final class Changes implements AutoCloseable {
        private record Change(Object receiver,String name,Object value){}
        private final List<Change> changes=new ArrayList<>();
        void set(Object receiver,String name,Object value){changes.add(new Change(receiver,name,get(receiver,name)));put(receiver,name,value);}
        @Override public void close(){for(int i=changes.size()-1;i>=0;i--){Change c=changes.get(i);put(c.receiver,c.name,c.value);}}
    }
    private static List<Integer> counts(){return List.of((Integer)get(candidate,"heldPreservations"),(Integer)get(renderer,"outstandingFieldPreservations"),(Integer)get(renderer,"outstandingEditorNativeCalls"));}
    private static List<Object> frames(List<ConcreteHostProbe.Site> source){check(source.size()<24,"full frames below cap");List<Object> out=new ArrayList<>();for(var s:source)out.add(Json.map("class",s.className(),"method",s.methodName(),"descriptor",s.descriptor(),"bci",s.bytecodeIndex(),"line",s.line()));return List.copyOf(out);}
    private static int firstBci(List<ConcreteHostProbe.Site> source){check(!source.isEmpty(),"nonempty production frames");check(source.get(0).methodName().equals("<init>"),"direct constructor is first captured production scope");return source.get(0).bytecodeIndex();}
    private static Object outcome(NativeOutcomeProbe.Outcome o){
        check(o.completion().equals("return"),"no manufactured exception in finite cases");
        Object value=o.value();
        Object frozen=value instanceof Editable?Json.map("reference",id(value),"text",value.toString()):Json.map("type",value.getClass().getName(),"value",value);
        return Json.map("method",o.method(),"descriptor",o.descriptor(),"receiver",id(o.receiver()),"completion",o.completion(),"value",frozen,"frames",frames(o.productionFrames()));
    }
    private static void observe(String name,Consumer<ConcreteHostProbe.Event> mutation,Runnable body,int expectedOutcomes){
        List<Integer> before=counts();Object operation=get(fence,"operation"),presentation=get(fence,"presentation"),pending=get(renderer,"v2Pending");
        List<Object> outcomes=new ArrayList<>(),events=new ArrayList<>();
        Consumer<ConcreteHostProbe.Event> hook=e->{
            int index=ConcreteHostProbe.events().size()-1;
            check(ConcreteHostProbe.events().get(index)==e,"immutable actual event identity and index");
            events.add(Json.map("reference",id(e),"index",index,"method",e.method,"phase",e.phase,"receiver",id(e.receiver),"frames",frames(e.productionFrames)));
            mutation.accept(e);
        };
        NativeOutcomeProbe.begin(o->outcomes.add(outcome(o)));
        ConcreteHostProbe.installQualificationHook(hook);
        try{body.run();}finally{ConcreteHostProbe.clearQualificationHook(hook);NativeOutcomeProbe.end();}
        check(NativeOutcomeProbe.clean(),"unfiltered passive capture clean");
        check(outcomes.size()==expectedOutcomes,"all observed nonvoid native returns counted, including nested state calls");
        check(counts().equals(before)&&get(fence,"operation")==operation&&get(fence,"presentation")==presentation&&get(renderer,"v2Pending")==pending&&get(candidate,"journal")==journal,"original callback scope identities/counts preserved");
        rows.add(Json.map("id",name,"all_unfiltered_passive_outcomes",outcomes,"all_actual_constructor_events",events,"counts",before,"callback_scope_only",true));
    }
    private static void cases(){
        var savedHook=ConcreteHostProbe.hook;ConcreteHostProbe.hook=null;
        try(Changes c=new Changes()){
            c.set(record,"view",field);c.set(field,"text",new SpannableStringBuilder("focused-live"));c.set(field,"focused",true);c.set(field,"selectable",false);
            observe("I01-focused-short-circuit",e->{},()->{
                Object result=construct(stateConstructor,journal,6,record);
                check((Boolean)get(result,"active"),"focused field active independently of composing helper");
                check(get(result,"nativeBuffer")==get(field,"text")&&get(result,"text").equals("focused-live"),"exact normal text identity/value");
                check((Integer)get(result,"position")==6&&get(result,"membership")==null,"actual constructor position and no membership");
            },1);
        }finally{ConcreteHostProbe.hook=savedHook;}
        try(Changes c=new Changes()){
            ConcreteHostProbe.hook=null;
            Editable buffer=new SpannableStringBuilder("initial-live");Object composing=new Object();buffer.setSpan(composing,1,4,Spanned.SPAN_COMPOSING|17);
            c.set(record,"view",field);c.set(field,"text",buffer);c.set(field,"focused",false);c.set(field,"selectable",false);
            int[] changed={0};
            observe("I02-two-getter-times-and-frozen-content",e->{
                if(e.receiver==field&&e.method.equals("TextView.getText")&&e.phase.equals("beforeReturn")&&firstBci(e.productionFrames)==145){buffer.removeSpan(composing);buffer.replace(0,buffer.length(),"return-live");changed[0]++;}
            },()->{
                Object result=construct(stateConstructor,journal,7,record);
                check(changed[0]==1&&(Boolean)get(result,"active"),"active captured from earlier composing return");
                check(((List<?>)get(result,"composition")).isEmpty(),"composition captured at later native-buffer return");
                check(get(result,"nativeBuffer")==buffer&&get(result,"text").equals("return-live"),"later exact live identity and copied text");
                buffer.replace(0,buffer.length(),"later-live");
                check(get(result,"text").equals("return-live")&&get(result,"nativeBuffer").toString().equals("later-live"),"immutable state text diverges from later live buffer");
            },2);
        }finally{ConcreteHostProbe.hook=savedHook;}
        try(Changes c=new Changes()){
            ConcreteHostProbe.hook=null;
            Editable buffer=new SpannableStringBuilder("alias-live");c.set(record,"view",field);c.set(field,"text",buffer);c.set(field,"focused",false);c.set(field,"selectable",false);
            Map<String,Object> repeated=new LinkedHashMap<>();repeated.put("first",record);repeated.put("alias",record);c.set(candidate,"baseRecords",repeated);
            c.set(root,"left",0);c.set(root,"top",0);c.set(root,"right",500);c.set(root,"bottom",700);
            int[] changed={0};
            observe("I03-alias-order-width-height-local-return-values",e->{
                if(e.receiver!=root)return;
                if(e.method.equals("View.getWidth")&&e.phase.equals("beforeReturn")){check(firstBci(e.productionFrames)==184,"exact journal width BCI");c.set(root,"right",900);changed[0]++;}
                if(e.method.equals("View.getHeight")&&e.phase.equals("entry")){check(firstBci(e.productionFrames)==192,"exact journal height BCI");c.set(root,"bottom",333);changed[0]++;}
            },()->{
                Object result=construct(journalConstructor,candidate);Object[] states=(Object[])get(result,"states");List<?> previous=(List<?>)get(result,"previous");
                check(states.length==2&&states[0]!=states[1],"one distinct constructor output per map value even with aliased record");
                for(int i=0;i<2;i++)check(states[i]==previous.get(i)&&get(states[i],"record")==record&&get(states[i],"nativeBuffer")==buffer&&(Integer)get(states[i],"position")==i,"exact repeated identity/order and distinct position");
                check((Integer)get(result,"rootWidth")==500&&(Integer)get(result,"rootHeight")==333&&changed[0]==2,"width local value precedes callback mutation; height reads later mutation");
                check((Integer)get(result,"completion")==0&&!(Boolean)get(result,"complete")&&get(candidate,"journal")==journal,"finite journal has no publication/completion authority");
            },6);
        }finally{ConcreteHostProbe.hook=savedHook;}
    }
    private static void write(StringBuilder out,Object value){if(value instanceof Map<?,?> map){out.append('{');boolean comma=false;for(var e:map.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,e.getKey());out.append(':');write(out,e.getValue());}out.append('}');}else if(value instanceof Iterable<?> list){out.append('[');boolean comma=false;for(Object e:list){if(comma)out.append(',');comma=true;write(out,e);}out.append(']');}else if(value instanceof Number n)out.append(n);else Json.write(out,value);}
    public static void main(String[] args)throws Exception{
        Class<?> original=Class.forName("dev.mixer.android.SelectedIdentityMembershipReviewControls"),fixtureClass=Class.forName(original.getName()+"$Fixture"),stateClass=Class.forName("dev.mixer.android.NativeRenderer$NativeState"),journalClass=Class.forName("dev.mixer.android.NativeRenderer$AttachmentJournal"),candidateClass=Class.forName("dev.mixer.android.NativeRenderer$Candidate");
        put(original,"descriptor",Files.readAllBytes(Path.of(args[0])));
        stateConstructor=stateClass.getDeclaredConstructor(journalClass,int.class,NativeAppearanceViewsV2.Record.class);stateConstructor.setAccessible(true);journalConstructor=journalClass.getDeclaredConstructor(candidateClass);journalConstructor.setAccessible(true);
        Constructor<?> fc=fixtureClass.getDeclaredConstructor(boolean.class,boolean.class);fc.setAccessible(true);
        try{
            fixture=construct(fc,true,true);renderer=get(fixture,"renderer");field=get(fixture,"a");record=get(field,"record");root=get(fixture,"root");fence=get(fixture,"fence");
            ConcreteHostProbe.hook=(method,phase)->{var event=ConcreteHostProbe.lastEvent();if(!entered&&method.equals("View.invalidate")&&phase.equals("entry")&&event.receiver==field&&get(record,"fieldPreservation")!=null){entered=true;candidate=get(renderer,"v2Pending");journal=get(candidate,"journal");check(counts().equals(List.of(2,2,3)),"original paused callback scope");cases();}};
            check(Boolean.TRUE.equals(invoke(fixture,"edit")),"original edit completes after restores");ConcreteHostProbe.hook=null;
            check(entered&&counts().equals(List.of(0,0,0))&&get(record,"fieldPreservation")==null,"original balanced final scope");
            StringBuilder out=new StringBuilder();write(out,Json.map("schema",1,"independent_cases",rows.size(),"checks",checks,"rows",rows,"final_counts",counts(),"native_or_authority_credit",false));Files.writeString(Path.of(args[1]),out+"\n");System.out.println("PASS three independent constructor cases; "+checks+" checks");
        }finally{ConcreteHostProbe.hook=null;if(fixture!=null)invoke(fixture,"close");}
    }
}
