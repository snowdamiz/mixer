package dev.mixer.android;

import android.app.Activity;
import android.text.Editable;
import android.text.Spanned;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.Switch;
import android.widget.TextView;
import java.lang.invoke.MethodType;
import java.lang.reflect.Array;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

/** Direct, ordinary-allocation host constructor controls. No product instrumentation or authority. */
public final class ConstructorControls {
    private ConstructorControls() {}
    private static final String CONTEXT="1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd";
    private static final String STATE_CLASS="dev.mixer.android.NativeRenderer$NativeState";
    private static final String JOURNAL_CLASS="dev.mixer.android.NativeRenderer$AttachmentJournal";
    private static final String STATE_DESC="(Ldev/mixer/android/NativeRenderer$AttachmentJournal;ILdev/mixer/android/NativeAppearanceViewsV2$Record;)V";
    private static final String JOURNAL_DESC="(Ldev/mixer/android/NativeRenderer$Candidate;)V";
    private static final String[] STATES={"clean","terminal-at-entry","terminal-before-return","dirty-at-entry","dirty-before-return","ordinary-throw-after-callback","fatal-throw-after-callback"};
    private static final List<Object> rows=new ArrayList<>();
    private static final IdentityHashMap<Object,Integer> ids=new IdentityHashMap<>();
    private static int checks;
    private static Object fixture,candidate,journal,fence,environmentSource;
    private static NativeRenderer renderer;
    private static NativeAppearanceViewsV2.NativeField actualField;
    private static Activity activity;
    private static FrameLayout root;
    private static Constructor<?> stateConstructor,journalConstructor;
    private static boolean entered;
    private static final List<Object> originalBoundary=new ArrayList<>();
    private static final class Fatal extends Error {
        private static final long serialVersionUID=1L;
        Fatal(String message){super(message);}
    }
    private static void check(boolean condition,String why){checks++;if(!condition)throw new AssertionError(why);}
    private static String id(Object value){
        if(value==null)return "null";
        Integer result=ids.get(value);if(result==null){result=ids.size()+1;ids.put(value,result);}
        return value.getClass().getName()+"@object-"+result;
    }
    private static Field field(Object receiver,String name){
        for(Class<?> type=receiver instanceof Class<?> c?c:receiver.getClass();type!=null;type=type.getSuperclass()){
            try{Field result=type.getDeclaredField(name);result.setAccessible(true);return result;}
            catch(NoSuchFieldException absent){/* exact inherited lookup */}
        }
        throw new AssertionError("exact field absent: "+name);
    }
    private static Object get(Object receiver,String name){try{return field(receiver,name).get(receiver instanceof Class<?>?null:receiver);}catch(IllegalAccessException failure){throw new AssertionError(failure);}}
    private static void put(Object receiver,String name,Object value){try{field(receiver,name).set(receiver instanceof Class<?>?null:receiver,value);}catch(IllegalAccessException failure){throw new AssertionError(failure);}}
    private static int integer(Object receiver,String name){return (Integer)get(receiver,name);}
    private static Object invoke(Object receiver,String name,Object... arguments){
        for(Method method:receiver.getClass().getDeclaredMethods())if(method.getName().equals(name)&&method.getParameterCount()==arguments.length){
            try{method.setAccessible(true);return method.invoke(receiver,arguments);}
            catch(InvocationTargetException failure){return rethrow(failure.getCause());}
            catch(ReflectiveOperationException failure){throw new AssertionError(failure);}
        }
        throw new AssertionError("exact fixture method absent: "+name);
    }
    private static Object rethrow(Throwable failure){if(failure instanceof Error error)throw error;if(failure instanceof RuntimeException ordinary)throw ordinary;throw new AssertionError(failure);}
    private static Object construct(Constructor<?> constructor,Object... arguments){try{return constructor.newInstance(arguments);}catch(InvocationTargetException failure){return rethrow(failure.getCause());}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static final class Changes implements AutoCloseable {
        private record Change(Object receiver,String name,Object old){}
        private final List<Change> changes=new ArrayList<>();
        void set(Object receiver,String name,Object value){changes.add(new Change(receiver,name,get(receiver,name)));put(receiver,name,value);}
        @Override public void close(){for(int i=changes.size()-1;i>=0;i--){Change change=changes.get(i);put(change.receiver,change.name,change.old);}}
    }
    private static List<Integer> ints(Object array){List<Integer> result=new ArrayList<>();for(int i=0;i<Array.getLength(array);i++)result.add((Integer)Array.get(array,i));return List.copyOf(result);}
    private static List<String> refs(Object array){List<String> result=new ArrayList<>();for(int i=0;i<Array.getLength(array);i++)result.add(id(Array.get(array,i)));return List.copyOf(result);}
    private static List<Integer> counts(){return List.of(integer(candidate,"heldPreservations"),integer(renderer,"outstandingFieldPreservations"),integer(renderer,"outstandingEditorNativeCalls"));}
    private static Object site(ConcreteHostProbe.Site site){return Json.map("class",site.className(),"method",site.methodName(),"descriptor",site.descriptor(),"bci",site.bytecodeIndex(),"line",site.line());}
    private static List<Object> frames(List<ConcreteHostProbe.Site> frames){List<Object> result=new ArrayList<>();for(var frame:frames)result.add(site(frame));return List.copyOf(result);}
    private record Tuple(String owner,String descriptor,int bci,String leaf,String nativeDescriptor){
        String subject(){return owner.replace('.','/')+"#<init>"+descriptor;}
        String siteId(){String target=bci==67?"android/widget/EditText#getText()Landroid/text/Editable;":bci==145?"android/widget/TextView#getText()Landroid/text/Editable;":bci==222?"android/view/View#getLocationInWindow([I)V":bci==184?"android/widget/FrameLayout#getWidth()I":"android/widget/FrameLayout#getHeight()I";return subject()+"@"+bci+":invokevirtual:"+target;}
        boolean matches(List<ConcreteHostProbe.Site> selected){return selected.stream().anyMatch(s->s.className().equals(owner)&&s.methodName().equals("<init>")&&s.descriptor().equals(descriptor)&&s.bytecodeIndex()==bci);}
        boolean matches(ConcreteHostProbe.Event event,Object receiver){return event.receiver==receiver&&event.method.equals(leaf)&&matches(event.productionFrames);}
        boolean matches(NativeOutcomeProbe.Outcome outcome,Object receiver){return outcome.receiver()==receiver&&outcome.method().equals(leaf)&&matches(outcome.productionFrames());}
    }
    private record FrozenSpan(Object reference,String type,int start,int end,int flags){
        Object json(){return Json.map("reference",id(reference),"type",type,"start",start,"end",end,"flags",flags);}
    }
    private record FrozenBuffer(Object reference,String text,List<FrozenSpan> spans,int selectionStart,int selectionEnd){
        FrozenBuffer{spans=List.copyOf(spans);}
        static FrozenBuffer capture(Object value,View receiver){
            List<FrozenSpan> spans=new ArrayList<>();
            if(value instanceof Spanned spanned)for(Object span:spanned.getSpans(0,spanned.length(),Object.class))spans.add(new FrozenSpan(span,span.getClass().getName(),spanned.getSpanStart(span),spanned.getSpanEnd(span),spanned.getSpanFlags(span)));
            return new FrozenBuffer(value,value==null?null:value.toString(),spans,receiver instanceof TextView?integer(receiver,"selectionStart"):-1,receiver instanceof TextView?integer(receiver,"selectionEnd"):-1);
        }
        Object json(){List<Object> saved=new ArrayList<>();for(var span:spans)saved.add(span.json());return Json.map("reference",id(reference),"type",reference==null?"null":reference.getClass().getName(),"text",text,"spans",saved,"selection_start",selectionStart,"selection_end",selectionEnd);}
    }
    private record FrozenState(Object reference,Object journalReference,int position,Object record,Object binding,Object geometry,Object nativeBuffer,String text,List<FrozenSpan> composition,List<Integer> drawable,List<Integer> window,
                               int left,int top,int right,int bottom,int measuredWidth,int measuredHeight,boolean enabled,int selectionStart,int selectionEnd,int scrollX,int scrollY,boolean active,boolean checked,boolean focused,boolean pressed,
                               boolean forwardPreserved,Object preservation,Object membership){
        FrozenState{composition=List.copyOf(composition);drawable=List.copyOf(drawable);window=List.copyOf(window);}
        static FrozenState capture(Object state){
            List<FrozenSpan> composition=new ArrayList<>();
            for(Object span:(List<?>)get(state,"composition")){Object reference=get(span,"object");composition.add(new FrozenSpan(reference,reference.getClass().getName(),integer(span,"start"),integer(span,"end"),integer(span,"flags")));}
            return new FrozenState(state,get(state,"journal"),integer(state,"position"),get(state,"record"),get(state,"binding"),get(state,"geometry"),get(state,"nativeBuffer"),(String)get(state,"text"),composition,ints(get(state,"drawableState")),ints(get(state,"windowPosition")),
                integer(state,"left"),integer(state,"top"),integer(state,"right"),integer(state,"bottom"),integer(state,"measuredWidth"),integer(state,"measuredHeight"),(Boolean)get(state,"enabled"),integer(state,"selectionStart"),integer(state,"selectionEnd"),integer(state,"scrollX"),integer(state,"scrollY"),(Boolean)get(state,"active"),(Boolean)get(state,"checked"),(Boolean)get(state,"focused"),(Boolean)get(state,"pressed"),(Boolean)get(state,"forwardPreserved"),get(state,"preservation"),get(state,"membership"));
        }
        Object json(){List<Object> spans=new ArrayList<>();for(var span:composition)spans.add(span.json());return Json.map("reference",id(reference),"journal",id(journalReference),"position",position,"record",id(record),"binding",id(binding),"geometry",id(geometry),"native_buffer",id(nativeBuffer),"text",text,"composition",spans,"drawable_state",drawable,"window_position",window,"frame",List.of(left,top,right,bottom),"measured",List.of(measuredWidth,measuredHeight),"enabled",enabled,"selection",List.of(selectionStart,selectionEnd),"scroll",List.of(scrollX,scrollY),"active",active,"checked",checked,"focused",focused,"pressed",pressed,"forward_preserved",forwardPreserved,"preservation",id(preservation),"membership",id(membership));}
    }
    private record Config(String name,View view,Editable buffer,List<FrozenSpan> spans,boolean active,boolean checked,boolean focused,boolean selectable,int selectionStart,int selectionEnd){
        Config{spans=List.copyOf(spans);}
        static Config setup(String branch,Changes changes){
            View view=branch.startsWith("field")?actualField:branch.startsWith("text")?new TextView(activity):branch.startsWith("switch")?new Switch(activity):new View(activity);
            boolean focused=branch.equals("field-focused"),composing=branch.equals("field-composing"),selectable=branch.equals("field-selectable")||branch.equals("text-selectable"),checked=branch.equals("switch-checked");
            int start=branch.equals("text-unselected")?-1:2,end=branch.equals("text-unselected")?-1:5;
            FrameLayout parent=new FrameLayout(activity);
            changes.set(parent,"left",100);changes.set(parent,"top",200);changes.set(parent,"scrollX",3);changes.set(parent,"scrollY",4);
            changes.set(view,"parent",parent);changes.set(view,"left",11);changes.set(view,"top",13);changes.set(view,"right",73);changes.set(view,"bottom",89);changes.set(view,"measuredWidth",61);changes.set(view,"measuredHeight",76);changes.set(view,"scrollX",5);changes.set(view,"scrollY",7);changes.set(view,"enabled",false);changes.set(view,"pressed",true);changes.set(view,"focused",focused);
            Editable buffer=null;List<FrozenSpan> spans=new ArrayList<>();
            if(view instanceof TextView){
                buffer=new android.text.SpannableStringBuilder("ctor-buffer");
                Object ordinary=new Object();buffer.setSpan(ordinary,0,2,17);spans.add(new FrozenSpan(ordinary,ordinary.getClass().getName(),0,2,17));
                if(composing){Object first=new Object(),second=new Object();buffer.setSpan(first,1,4,Spanned.SPAN_COMPOSING|17);buffer.setSpan(second,6,9,Spanned.SPAN_COMPOSING|33);spans.add(new FrozenSpan(first,first.getClass().getName(),1,4,Spanned.SPAN_COMPOSING|17));spans.add(new FrozenSpan(second,second.getClass().getName(),6,9,Spanned.SPAN_COMPOSING|33));}
                if(branch.equals("text-null-buffer")){buffer=null;spans.clear();}
                changes.set(view,"text",buffer);changes.set(view,"selectionStart",start);changes.set(view,"selectionEnd",end);changes.set(view,"selectable",selectable);
            }
            if(view instanceof Switch)changes.set(view,"checked",checked);
            boolean active=focused||composing||(selectable&&start>=0);
            return new Config(branch,view,buffer,spans,active,checked,focused,selectable,view instanceof TextView?start:-1,view instanceof TextView?end:-1);
        }
        void assertBuffer(FrozenBuffer observed){check(observed.reference==buffer,"native return exact Editable reference");check(java.util.Objects.equals(observed.text,buffer==null?null:"ctor-buffer"),"text copied at actual native return");check(observed.spans.equals(spans),"all returned span identities/types/order/ranges/flags copied at actual native return");check(observed.selectionStart==selectionStart&&observed.selectionEnd==selectionEnd,"selection copied at actual native return");}
        void assertState(FrozenState observed,Object expectedJournal,int expectedPosition,NativeAppearanceViewsV2.Record record,Object binding,Object geometry){
            check(observed.reference!=null&&observed.reference.getClass().getName().equals(STATE_CLASS),"actual typed normal NativeState object");
            check(observed.journalReference==expectedJournal&&observed.position==expectedPosition&&observed.record==record&&observed.binding==binding&&observed.geometry==geometry,"exact constructor argument and captured references");
            check(observed.nativeBuffer==buffer&&java.util.Objects.equals(observed.text,buffer==null?null:"ctor-buffer"),"captured buffer identity and immutable text value");
            check(observed.composition.equals(spans.stream().filter(s->(s.flags&Spanned.SPAN_COMPOSING)!=0).toList()),"only composing spans retained with identity/type/order/ranges/flags");
            List<Integer> expectedDrawable=focused?List.of(android.R.attr.state_pressed,android.R.attr.state_focused):List.of(android.R.attr.state_pressed);
            check(observed.drawable.equals(expectedDrawable)&&observed.window.equals(List.of(108,209)),"fresh copied drawable and exact output-array window values");
            check(observed.left==11&&observed.top==13&&observed.right==73&&observed.bottom==89&&observed.measuredWidth==61&&observed.measuredHeight==76,"finite unhooked frame and measurement getter values");
            check(!observed.enabled&&observed.selectionStart==selectionStart&&observed.selectionEnd==selectionEnd&&observed.scrollX==5&&observed.scrollY==7,"finite unhooked enabled/selection/scroll values");
            check(observed.active==active&&observed.checked==checked&&observed.focused==focused&&observed.pressed,"independent active/toggle/focus/pressed branch oracle");
            check(!observed.forwardPreserved&&observed.preservation==null&&observed.membership==null,"constructor grants no preservation membership");
        }
        Object expectedJson(){return Json.map("branch",name,"view",id(view),"buffer",id(buffer),"active",active,"checked",checked,"focused",focused,"selectable",selectable,"selection",List.of(selectionStart,selectionEnd),"text",buffer==null?null:"ctor-buffer","window",List.of(108,209),"frame",List.of(11,13,73,89),"measured",List.of(61,76),"scroll",List.of(5,7));}
    }
    private static List<String> childRefs(ViewGroup parent){return parent.hostChildren().stream().map(ConstructorControls::id).toList();}
    private record ParentExpected(Object parent,List<String> children){ParentExpected{children=List.copyOf(children);}}
    private record JournalSetup(List<NativeAppearanceViewsV2.Record> records,List<Config> configs,List<Object> bindings,List<Object> geometries,List<ParentExpected> parents,List<String> rootChildren,Object oldGate,int canvas){
        JournalSetup{records=List.copyOf(records);configs=List.copyOf(configs);bindings=List.copyOf(bindings);geometries=List.copyOf(geometries);parents=List.copyOf(parents);rootChildren=List.copyOf(rootChildren);}
    }
    private static JournalSetup configureJournal(Changes changes,String branch){
        @SuppressWarnings("unchecked") Map<String,NativeAppearanceViewsV2.Record> original=(Map<String,NativeAppearanceViewsV2.Record>)get(candidate,"baseRecords");
        List<NativeAppearanceViewsV2.Record> records=new ArrayList<>();List<Config> configs=new ArrayList<>();List<Object> bindings=new ArrayList<>(),geometries=new ArrayList<>();List<ParentExpected> parents=new ArrayList<>();
        LinkedHashMap<String,NativeAppearanceViewsV2.Record> ordered=new LinkedHashMap<>();
        String[] order=branch.equals("empty")?new String[0]:branch.equals("reverse-order")?new String[]{"b","root","a","c"}:new String[]{"c","a","root","b"};
        for(String key:order){NativeAppearanceViewsV2.Record record=original.get(key);check(record!=null,"original ordinary record "+key);String kind=key.equals("a")?"field-composing":key.equals("b")?"text-selectable":key.equals("c")?"switch-checked":"non-text";Config config=Config.setup(kind,changes);changes.set(record,"view",config.view);records.add(record);configs.add(config);bindings.add(record.binding);geometries.add(record.geometry);ordered.put(key,record);if(record.group!=null)parents.add(new ParentExpected(record.group,childRefs(record.group)));}
        changes.set(candidate,"baseRecords",ordered);
        changes.set(root,"left",41);changes.set(root,"top",43);changes.set(root,"right",1141);changes.set(root,"bottom",1643);
        Object oldGate=branch.equals("null-old-gate")?null:get(renderer,"v2Gate");
        if(oldGate==null)changes.set(renderer,"v2Gate",null);else{changes.set(oldGate,"canvasColor",0x1234abcd);parents.add(new ParentExpected(oldGate,childRefs((ViewGroup)oldGate)));}
        return new JournalSetup(records,configs,bindings,geometries,parents,childRefs(root),oldGate,oldGate==null?0:0x1234abcd);
    }
    private static Object assertJournal(Object result,JournalSetup expected){
        check(result!=null&&result.getClass().getName().equals(JOURNAL_CLASS),"actual normal AttachmentJournal object");
        check(get(result,"candidate")==candidate,"exact candidate reference");
        Object[] states=(Object[])get(result,"states");List<?> previous=(List<?>)get(result,"previous"),parents=(List<?>)get(result,"parents");
        check(states.length==expected.records.size()&&integer(result,"stateCount")==states.length&&previous.size()==states.length,"one frozen state per original map iteration value");
        List<Object> snapshots=new ArrayList<>();
        for(int i=0;i<states.length;i++){check(states[i]==previous.get(i),"previous and array share exact ordered state");FrozenState saved=FrozenState.capture(states[i]);expected.configs.get(i).assertState(saved,result,i,expected.records.get(i),expected.bindings.get(i),expected.geometries.get(i));snapshots.add(saved.json());}
        check(parents.size()==expected.parents.size(),"exact group/null-group and old-gate parent branch count");
        List<Object> parentSnapshots=new ArrayList<>();
        for(int i=0;i<parents.size();i++){Object parent=parents.get(i);List<String> children=refs(get(parent,"children"));check(get(parent,"parent")==expected.parents.get(i).parent&&children.equals(expected.parents.get(i).children),"exact ordered parent reference and child array values");parentSnapshots.add(Json.map("parent",id(get(parent,"parent")),"children",children));}
        List<String> children=refs(get(result,"rootChildren"));check(children.equals(expected.rootChildren),"root child immutable order/identity snapshot");
        check(integer(result,"rootWidth")==1100&&integer(result,"rootHeight")==1600,"independent configured width and height");
        check(get(result,"oldGate")==expected.oldGate&&integer(result,"oldCanvas")==expected.canvas,"old gate and finite canvas/null branch");
        check(integer(result,"completion")==0&&!(Boolean)get(result,"failedInvoked")&&!(Boolean)get(result,"complete"),"new journal OPEN incomplete has no completion authority");
        check(get(candidate,"journal")==journal,"new journal not published over actual candidate journal");
        return Json.map("reference",id(result),"candidate",id(candidate),"state_count",states.length,"ordered_records",expected.records.stream().map(ConstructorControls::id).toList(),"ordered_states",snapshots,"parents",parentSnapshots,"root_children",children,"root_width",1100,"root_height",1600,"old_gate",id(expected.oldGate),"old_canvas",expected.canvas,"completion",0,"complete",false,"failed_invoked",false,"candidate_journal_unchanged",true);
    }
    private static void test(String branch,Tuple tuple,String callbackState,boolean journalCase){
        List<Integer> before=counts();Object operation=get(fence,"operation"),presentation=get(fence,"presentation"),baseRecords=get(candidate,"baseRecords");Object originalPending=get(renderer,"v2Pending");
        int eventStart=ConcreteHostProbe.events().size();List<NativeOutcomeProbe.Outcome> outcomes=new ArrayList<>();List<Object> nativeResults=new ArrayList<>(),hooks=new ArrayList<>();
        Throwable original=callbackState.equals("fatal-throw-after-callback")?new Fatal("exact ctor fatal"):callbackState.equals("ordinary-throw-after-callback")?new IllegalStateException("exact ctor ordinary"):null;
        Object[] enclosing={null};Throwable[] escaped={null};int[] mutations={0};Object resultSnapshot=null;Object expectedSnapshot=null;
        try(Changes changes=new Changes()){
            Config config=null;JournalSetup setup=null;
            NativeAppearanceViewsV2.Record record=actualField.record;Object binding=record.binding,geometry=record.geometry;
            if(journalCase){setup=configureJournal(changes,branch);expectedSnapshot=Json.map("branch",branch,"ordered_records",setup.records.stream().map(ConstructorControls::id).toList(),"positions",java.util.stream.IntStream.range(0,setup.records.size()).boxed().toList(),"root_width",1100,"root_height",1600,"old_gate",id(setup.oldGate),"old_canvas",setup.canvas);}
            else{config=Config.setup(branch,changes);changes.set(record,"view",config.view);expectedSnapshot=config.expectedJson();}
            View receiver=journalCase?root:config.view;
            Config expectedConfig=config;
            long generation=(Long)get(environmentSource,"generation");
            boolean terminal=(Boolean)get(fence,"terminal");check(!terminal,"ordinary original fence starts nonterminal");
            Consumer<ConcreteHostProbe.Event> qualification=event->{
                if(tuple==null||!tuple.matches(event,receiver))return;
                hooks.add(Json.map("event_reference",id(event),"event_index",ConcreteHostProbe.events().size()-1,"phase",event.phase,"receiver",id(event.receiver),"original_own_receiver",id(receiver),"frames",frames(event.productionFrames),"counts",counts()));
                boolean phase=callbackState.endsWith("at-entry")?event.phase.equals("entry"):event.phase.equals("beforeReturn");
                if(!callbackState.equals("clean")&&phase){
                    mutations[0]++;
                    if(callbackState.startsWith("terminal")){changes.set(fence,"terminal",true);changes.set(fence,"drawAllowed",false);changes.set(fence,"inputAllowed",false);}
                    else changes.set(environmentSource,"generation",generation+1);
                    check(callbackState.startsWith("terminal")?(Boolean)get(fence,"terminal"):(Long)get(environmentSource,"generation")==generation+1,"actual callback mutation visible before original completion");
                    if(original!=null)rethrow(original);
                }
            };
            NativeOutcomeProbe.begin(outcome->{
                outcomes.add(outcome);
                if(tuple!=null&&tuple.matches(outcome,receiver)){
                    if(outcome.completion().equals("return")){
                        check(outcome.descriptor().equals(tuple.nativeDescriptor),"exact original native descriptor");
                        Object value;
                        if(outcome.value() instanceof Editable||outcome.value()==null){FrozenBuffer saved=FrozenBuffer.capture(outcome.value(),receiver);check(expectedConfig!=null,"text only state constructor");expectedConfig.assertBuffer(saved);value=saved.json();}
                        else{check(outcome.value() instanceof Integer,"actual native int");check(outcome.value().equals(tuple.bci==184?1100:1600),"literal configured native width/height result");value=Json.map("type","int","value",outcome.value());}
                        nativeResults.add(Json.map("completion","return","descriptor",outcome.descriptor(),"value",value,"frames",frames(outcome.productionFrames())));
                    }else{check(outcome.originalException()==original,"native observed exact original callback exception");nativeResults.add(Json.map("completion","exception","exception_reference",id(outcome.originalException()),"exception_type",outcome.originalException().getClass().getName(),"descriptor",outcome.descriptor(),"frames",frames(outcome.productionFrames())));}
                }
            });
            ConcreteHostProbe.installQualificationHook(qualification);
            try{enclosing[0]=journalCase?construct(journalConstructor,candidate):construct(stateConstructor,journal,17,record);}
            catch(RuntimeException|Error failure){escaped[0]=failure;}
            finally{ConcreteHostProbe.clearQualificationHook(qualification);NativeOutcomeProbe.end();}
            check(NativeOutcomeProbe.clean(),"passive observation clean, no swallowed evidence error or open hook");
            if(original==null){check(escaped[0]==null&&enclosing[0]!=null,"actual normal constructor completion");resultSnapshot=journalCase?assertJournal(enclosing[0],setup):FrozenState.capture(enclosing[0]).json();if(!journalCase){FrozenState saved=FrozenState.capture(enclosing[0]);config.assertState(saved,journal,17,record,binding,geometry);int[] output=(int[])get(enclosing[0],"windowPosition");output[0]=-777;check(saved.window.equals(List.of(108,209)),"copied immutable observed window array does not reread later mutable result");output[0]=108;}}
            else{check(escaped[0]==original&&enclosing[0]==null,"exact escaped original exception, no returned partially constructed object");resultSnapshot=Json.map("exception_reference",id(escaped[0]),"exception_type",escaped[0].getClass().getName(),"exact_original_identity",true,"partial_object_observable",false);}
            if(tuple!=null){
                long entry=hooks.stream().filter(h->((Map<?,?>)h).get("phase").equals("entry")).count(),returns=hooks.stream().filter(h->((Map<?,?>)h).get("phase").equals("beforeReturn")).count();
                check(entry==1&&returns==1,"exact tuple original entry/return hooks once");check(mutations[0]==(callbackState.equals("clean")?0:1),"exact bounded callback state injection");
                if(tuple.nativeDescriptor.equals("([I)V")){check(original==null?nativeResults.isEmpty():nativeResults.size()==1,"void leaf has no invented nonvoid return");}
                else check(nativeResults.size()==1,"actual native return or exact original hook exception once");
            }else{check(mutations[0]==0,"finite branches fabricate no callback");}
            check(counts().equals(before),"constructor callback states preserve all actual shared/held counts");
            check(get(fence,"operation")==operation&&get(fence,"presentation")==presentation&&get(renderer,"v2Pending")==originalPending&&get(candidate,"journal")==journal,"actual transaction/presentation/pending/candidate journal identities preserved");
        }
        check(counts().equals(before)&&get(candidate,"baseRecords")==baseRecords,"all exact original counts and base-record reference restored");
        List<Object> exactEvents=new ArrayList<>();for(var event:ConcreteHostProbe.events().subList(eventStart,ConcreteHostProbe.events().size()))if(tuple!=null&&tuple.matches(event,event.receiver))exactEvents.add(Json.map("method",event.method,"phase",event.phase,"receiver",id(event.receiver),"frames",frames(event.productionFrames)));
        rows.add(Json.map("subject_id",(journalCase?JOURNAL_CLASS:STATE_CLASS).replace('.','/')+"#<init>"+(journalCase?JOURNAL_DESC:STATE_DESC),"class_sha256",journalCase?"5a14150b3b0def507dc13d2a27b806f8b27924c96720fab9f6ca4dc0cd26ac47":"d9e071ab80fe835e152b3e760b735b1b6b7c93affcacc01d27363c7b8ba36af8","case_id",tuple==null?"renderer-finite-source-invariants":"renderer-native-bci-"+tuple.bci,"native_site_id",tuple==null?null:tuple.siteId(),"callback_state",tuple==null?"finite-no-fabricated-callback":callbackState,"branch",branch,"independent_expected_before_invocation",expectedSnapshot,"enclosing_completion",original==null?"normal-object":"exact-exception","actual_enclosing_snapshot",resultSnapshot,"actual_native_outcomes",nativeResults,"exact_tuple_hooks",hooks,"counts_before",before,"counts_after",counts(),"original_authority_references_preserved",true,"mutations_restored",true,"native_outcome_capture_clean",true,"no_membership_or_release_authority",true));
    }
    private static void matrix(){
        var oldHook=ConcreteHostProbe.hook;ConcreteHostProbe.hook=null;
        try{
            for(String branch:new String[]{"field-idle","field-focused","field-composing","field-selectable","text-selectable","text-unselected","text-nonselectable","text-null-buffer","non-text","switch-checked","switch-unchecked"})test(branch,null,"clean",false);
            for(String branch:new String[]{"mixed-order","reverse-order","null-old-gate","empty"})test(branch,null,"clean",true);
            for(Tuple tuple:List.of(new Tuple(STATE_CLASS,STATE_DESC,67,"TextView.getText","()Landroid/text/Editable;"),new Tuple(STATE_CLASS,STATE_DESC,145,"TextView.getText","()Landroid/text/Editable;"),new Tuple(STATE_CLASS,STATE_DESC,222,"View.getLocationInWindow","([I)V"),new Tuple(JOURNAL_CLASS,JOURNAL_DESC,184,"View.getWidth","()I"),new Tuple(JOURNAL_CLASS,JOURNAL_DESC,192,"View.getHeight","()I"))){
                List<String> branches=tuple.bci==67?List.of("field-composing"):tuple.bci==145?List.of("field-composing","text-selectable","switch-checked"):tuple.bci==222?List.of("field-composing","text-selectable","non-text","switch-checked"):List.of("mixed-order");
                for(String branch:branches)for(String state:STATES)test(branch,tuple,state,tuple.owner.equals(JOURNAL_CLASS));
            }
        }finally{ConcreteHostProbe.hook=oldHook;}
    }
    private static void write(StringBuilder out,Object value){
        if(value instanceof Map<?,?> values){out.append('{');boolean comma=false;for(var item:values.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,item.getKey());out.append(':');write(out,item.getValue());}out.append('}');}
        else if(value instanceof Iterable<?> values){out.append('[');boolean comma=false;for(var item:values){if(comma)out.append(',');comma=true;write(out,item);}out.append(']');}
        else if(value instanceof Number number)out.append(number);
        else Json.write(out,value);
    }
    private static void hash(Class<?> type,String expected)throws Exception{try(var stream=type.getResourceAsStream("/"+type.getName().replace('.','/')+".class")){check(stream!=null,"actual loaded class bytes");check(java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(stream.readAllBytes())).equals(expected),"exact selected loaded class identity");}}
    public static void main(String[] arguments)throws Exception{
        Class<?> fixtureClass=Class.forName("dev.mixer.android.SelectedIdentityMembershipReviewControls$Fixture");
        put(Class.forName("dev.mixer.android.SelectedIdentityMembershipReviewControls"),"descriptor",Files.readAllBytes(Path.of(arguments[0])));
        Class<?> stateClass=Class.forName(STATE_CLASS),journalClass=Class.forName(JOURNAL_CLASS),candidateClass=Class.forName("dev.mixer.android.NativeRenderer$Candidate");
        stateConstructor=stateClass.getDeclaredConstructor(journalClass,int.class,NativeAppearanceViewsV2.Record.class);stateConstructor.setAccessible(true);journalConstructor=journalClass.getDeclaredConstructor(candidateClass);journalConstructor.setAccessible(true);
        check(MethodType.methodType(void.class,stateConstructor.getParameterTypes()).toMethodDescriptorString().equals(STATE_DESC)&&MethodType.methodType(void.class,journalConstructor.getParameterTypes()).toMethodDescriptorString().equals(JOURNAL_DESC),"exact emitted constructor descriptors");
        hash(stateClass,"d9e071ab80fe835e152b3e760b735b1b6b7c93affcacc01d27363c7b8ba36af8");hash(journalClass,"5a14150b3b0def507dc13d2a27b806f8b27924c96720fab9f6ca4dc0cd26ac47");
        try{
            Constructor<?> fixtureConstructor=fixtureClass.getDeclaredConstructor(boolean.class,boolean.class);fixtureConstructor.setAccessible(true);fixture=construct(fixtureConstructor,true,true);
            renderer=(NativeRenderer)get(fixture,"renderer");actualField=(NativeAppearanceViewsV2.NativeField)get(fixture,"a");activity=(Activity)get(fixture,"activity");root=(FrameLayout)get(fixture,"root");fence=get(fixture,"fence");
            ConcreteHostProbe.hook=(method,phase)->{
                var event=ConcreteHostProbe.lastEvent();
                if(!entered&&method.equals("View.invalidate")&&phase.equals("entry")&&event.receiver==actualField&&actualField.record.fieldPreservation!=null){
                    entered=true;originalBoundary.addAll(frames(event.productionFrames));candidate=get(renderer,"v2Pending");journal=get(candidate,"journal");environmentSource=get(get(candidate,"environment"),"source");
                    check(counts().equals(List.of(2,2,3)),"ordinary initial held/shared callback counts");matrix();
                }
            };
            check(Boolean.TRUE.equals(invoke(fixture,"edit")),"actual original edit completes after every constructor control restore");ConcreteHostProbe.hook=null;
            check(entered&&counts().equals(List.of(0,0,0)),"original edit releases exact held/shared counts");
            check(actualField.record.fieldPreservation==null,"original field preservation registration cleared");
            long callbackRows=rows.stream().filter(o->!((Map<?,?>)o).get("callback_state").equals("finite-no-fabricated-callback")).count();check(callbackRows==70&&rows.size()==85,"bounded planned finite plus tuple-state-branch count");
            StringBuilder out=new StringBuilder();write(out,Json.map("schema",1,"scope","two exact constructors; finite typed host controls plus five exact hooked tuples; no constructor membership/release authority","source_context",CONTEXT,"invocations",rows.size(),"callback_rows",callbackRows,"finite_rows",15,"checks",checks,"original_fixture","exact SelectedIdentityMembershipReviewControls$Fixture(true,true)","original_boundary",originalBoundary,"original_boundary_counts",List.of(2,2,3),"original_edit_completed_after_restores",true,"original_final_counts",counts(),"rows",rows,"limits",List.of("Exceptional constructor receiver/partial fields/output-array identity are not observable through ordinary Java reflection.","Void getLocationInWindow normal evidence is actual completed enclosing object's copied output-array values; no nonvoid return is fabricated.","Internal getDrawableState source-array identity and runtime allocation failures remain unobserved.","These constructors do not authorize membership, release, completion or publication; enclosing original matrix joins remain pending.","Host leaves are finite models; native runtime, physical, UI and capture checks remain paused.")));
            Files.writeString(Path.of(arguments[1]),out+"\n");System.out.println("PASS exact NativeState/AttachmentJournal constructors: "+rows.size()+" invocations, "+callbackRows+" tuple/state/branch rows, "+checks+" checks; host only");
        }finally{ConcreteHostProbe.hook=null;if(fixture!=null)invoke(fixture,"close");}
    }
}
