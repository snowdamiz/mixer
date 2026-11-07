package dev.mixer.android;

import android.app.Activity;
import android.graphics.Canvas;
import android.os.Handler;
import android.widget.FrameLayout;
import android.view.View;
import android.view.MotionEvent;
import android.view.KeyEvent;
import android.widget.EditText;
import android.widget.Switch;
import android.view.inputmethod.InputConnection;
import android.view.inputmethod.EditorInfo;
import android.os.Bundle;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Set;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Executes real owner/core/coordinator/observer/renderer/native-view bodies with controlled platform leaves. */
public final class NativeOwnerV2ConcreteHostTests {
    private static byte[] descriptor;
    private static int checks;
    private static Fixture activeFixture;
    private static String scenario;
    private static List<Barrier> barriers=List.of();
    private static final Map<String,String> witnesses=new LinkedHashMap<>();
    private static MatrixCase matrix;
    private static final class MatrixDone extends RuntimeException {private static final long serialVersionUID=1L;}
    private static final class Fatal extends Error {private static final long serialVersionUID=1L;Fatal(String message){super(message);}}
    private static String receiverId(Object receiver){
        if(receiver==null)return null;
        try{Field record=receiver.getClass().getDeclaredField("record");record.setAccessible(true);Object owner=record.get(receiver);if(owner instanceof NativeAppearanceViewsV2.Record value)return value.id;}catch(NoSuchFieldException ignored){}catch(IllegalAccessException failure){throw new AssertionError(failure);}
        if(receiver instanceof View view&&view.getTag() instanceof String tag)return tag;
        return null;
    }
    private record Barrier(String id,String className,int line,String entryMethod,String returnMethod,
                           String returnReceiverId,String returnReceiverClass,Integer returnFrameLine,String boundaryMode,String equivalence) {
        boolean matches(ConcreteHostProbe.Event event){
            boolean returning=event.phase.equals("beforeReturn");String target=returning?returnMethod:entryMethod;
            if(!target.equals("*")&&!(target.contains(".")?event.method.equals(target):event.method.endsWith("."+target)))return false;
            if(returning){
                if(returnReceiverId!=null&&!returnReceiverId.equals(receiverId(event.receiver)))return false;
                if(returnReceiverClass!=null&&(event.receiver==null||!event.receiver.getClass().getSimpleName().equals(returnReceiverClass)))return false;
                if(returnFrameLine!=null&&event.productionFrames.stream().noneMatch(frame->frame.line()==returnFrameLine&&frame.className().equals("dev.mixer.android.NativeAppearanceViewsV2")))return false;
            }
            for(var frame:event.productionFrames)if(frame.line()==line&&(frame.className().equals(className)||frame.className().startsWith(className+"$")))return true;
            return false;
        }
    }
    private static final class MatrixCase {
        final Barrier barrier;final String name;boolean fired,validated;Fixture fixture;int commits;ConcreteHostProbe.Event reached;
        final List<ConcreteHostProbe.Event> dynamic=new ArrayList<>();String traceKey,traceEnd;OwnerLifecycleV2.Token traceOperation,tracePresentation;
        final MatrixDone done=new MatrixDone();final Fatal fatal=new Fatal("matrix fatal");final RuntimeException ordinary=new IllegalStateException("matrix ordinary");
        MatrixCase(Barrier barrier,String name){this.barrier=barrier;this.name=name;}
        void hook(String method,String phase){
            var event=ConcreteHostProbe.lastEvent();String wanted=name.endsWith("entry")||name.equals("clean")?"entry":"beforeReturn";
            if(fired||activeFixture==null||!phase.equals(wanted)||!barrier.matches(event))return;
            fired=true;reached=event;fixture=activeFixture;ConcreteHostProbe.hook=null;commits=NativeBridge.commitCalls;
            NativeOwnerV2.Fence fence=fixture.fence();
            if(fence.operation!=null)assertGates(fixture,"transaction callback entry");
            if(name.startsWith("dirty"))fixture.owner.onPause();
            else if(!name.equals("clean")){
                if(fence.operation!=null||fence.terminal)fixture.owner.close();else fixture.renderer().retireV2();
            }
            if(!name.equals("clean"))assertGates(fixture,"callback returned to selected native call");
            check(fixture.queue.queued()<=1,"second owned runnable during reentry");
            validated=true;
            if(name.equals("clean")){
                var frame=event.productionFrames.stream().filter(site->site.line()==barrier.line()&&(site.className().equals(barrier.className())||site.className().startsWith(barrier.className()+"$"))).findFirst().orElseThrow();
                traceKey=frame.className()+"#"+frame.methodName()+frame.descriptor()+"@"+frame.bytecodeIndex();traceOperation=fence.operation;tracePresentation=fence.presentation;dynamic.add(event);ConcreteHostProbe.hook=this::trace;
            }
            if(name.equals("ordinary-throw-after-callback"))throw ordinary;
            if(name.equals("fatal-throw-after-callback"))throw fatal;
        }
        void trace(String method,String phase){
            if(traceEnd!=null)return;var event=ConcreteHostProbe.lastEvent();
            boolean same=fixture.fence().operation==traceOperation&&fixture.fence().presentation==tracePresentation;
            boolean frame=same&&event.productionFrames.stream().anyMatch(site->(site.className()+"#"+site.methodName()+site.descriptor()+"@"+site.bytecodeIndex()).equals(traceKey));
            boolean nextRecord=barrier.id().equals("NativeRenderer:L225:C51:1")&&method.equals("View.<init>")&&phase.equals("entry")&&event.receiver!=reached.receiver;
            if(!frame||nextRecord){traceEnd=nextRecord?"next Record construction at same loop callsite, different concrete receiver":"original invocation frame/operation left";return;}
            dynamic.add(event);
        }
    }
    private static void assertGates(Fixture f,String where){
        check(!f.fence().drawAllowed&&!f.fence().inputAllowed,where+": shared gates open");
        Object joined=field(f.owner,"opening");if(joined==null)joined=field(f.owner,"coordinator");
        if(joined==null)return;NativeRenderer renderer=(NativeRenderer)field(joined,"renderer");
        Object gate=field(renderer,"v2Gate");if(gate!=null)check(!(Boolean)field(gate,"open"),where+": current gate open");
        Object pending=field(renderer,"v2Pending");if(pending!=null)check(!(Boolean)field(field(pending,"gate"),"open"),where+": pending gate open");
    }
    private static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    private static Object field(Object value,String name){try{Field f=value.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(value);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static Map<String,Object> node(String id,String kind,Map<String,Object> props,List<Object> children){
        List<Object> actions=switch(kind){case "button"->List.of(Json.map("id",id+"Action","event","activate"));case "toggle"->List.of(Json.map("id",id+"Change","event","valueChange"));case "textField"->List.of(Json.map("id",id+"Change","event","textChange"),Json.map("id",id+"Submit","event","submit"));default->List.of();};
        return Json.map("id",id,"kind",kind,"properties",props,"children",children,"actions",actions);
    }
    private static void write(StringBuilder out,Object value){if(value instanceof List<?> values){out.append('[');for(int i=0;i<values.size();i++){if(i>0)out.append(',');write(out,values.get(i));}out.append(']');}else if(value instanceof Map<?,?> values){out.append('{');boolean comma=false;for(var e:values.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,e.getKey());out.append(':');write(out,e.getValue());}out.append('}');}else Json.write(out,value);}
    private static void identities(Object raw,List<Object> out){Map<String,Object> n=Json.object(raw);out.add(Json.map("id",n.get("id"),"generation",new Json.Num(Integer.toString(out.size()+1))));for(Object child:Json.array(n.get("children")))identities(child,out);}
    private static byte[] packet(long revision){return packet(revision,"controls");}
    private static byte[] packet(long revision,String scene){return packet(revision,scene,"hello");}
    private static byte[] packet(long revision,String scene,String fieldValue){
        Object text=node("text","text",Json.map("text","Independent host text","style","body"),List.of());
        Object button=node("button","button",Json.map("label","Do action"),List.of());
        Object field=node("field","textField",Json.map("label","Entry","value",fieldValue),List.of());
        Object toggle=node("toggle","toggle",Json.map("label","Enable","value",false),List.of());
        Object h=node("horizontal","hStack",Json.map("alignment","center"),List.of(node("short","text",Json.map("text","Short"),List.of()),node("long","text",Json.map("text","Long text"),List.of())));
        Object z=node("overlay","zStack",Json.map("alignment","bottomTrailing"),List.of(node("back","text",Json.map("text","Back"),List.of()),node("front","text",Json.map("text","Front"),List.of())));
        Object section=node("section","section",Json.map("title","Details"),List.of(text,h,z,button,field,toggle));
        Object root=node("root","vStack",Json.map("alignment","leading"),List.of(section));
        if(scene.equals("navigation")){
            List<Object> rows=new ArrayList<>();rows.add(node("group","section",Json.map("title","Group"),List.of(text,h,z)));
            for(int i=0;i<30;i++)rows.add(node("row"+i,"text",Json.map("text","Scrolling text row "+i),List.of()));
            root=node("nav","navigation",Json.map("title","Navigation"),List.of(node("list","list",Map.of(),rows)));
        } else if(scene.equals("toggles"))root=node("root","vStack",Map.of(),List.of(node("first","toggle",Json.map("label","First","value",false),List.of()),node("middle","toggle",Json.map("label","Middle","value",false),List.of()),node("last","toggle",Json.map("label","Last","value",false),List.of())));
        else if(scene.equals("field"))root=field;
        else if(scene.equals("replace"))root=node("replacement","zStack",Map.of(),List.of(section));
        List<Object> ids=new ArrayList<>();identities(root,ids);
        StringBuilder out=new StringBuilder();write(out,Json.map("schemaVersion",new Json.Num("1"),"document",Json.map("schemaVersion",new Json.Num("1"),"revision",new Json.Num(Long.toString(revision)),"root",root),"identities",ids));return out.toString().getBytes(StandardCharsets.UTF_8);
    }
    private static final class Fixture implements AutoCloseable {
        final Activity activity=new Activity();final FrameLayout root=new FrameLayout(activity);final NativeOwnerV2 owner;
        final Handler queue;
        Fixture(){this("controls");}
        Fixture(String scene){this(scene,null);}
        Fixture(String scene,Runnable completionFault){
            activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);
            root.hostAttach(new Object());NativeBridge.reset();NativeBridge.preparedPacket=packet(1,scene);
            owner=new NativeOwnerV2(activity,root,completionFault);activeFixture=this;queue=(Handler)field(owner,"handler");owner.onResume();if(owner.cleanupLedger().primary()!=null)throw new AssertionError("fixture resume failed",owner.cleanupLedger().primary());owner.start();
        }
        void ready(){queue.drainAll(4);check(owner.hasCommittedPresentation(),"owner did not publish: "+owner.cleanupLedger().cause()+" / "+owner.cleanupLedger().primary());}
        NativeRenderer renderer(){return (NativeRenderer)field(field(owner,"coordinator"),"renderer");}
        NativeOwnerV2.Fence fence(){return (NativeOwnerV2.Fence)field(owner,"fence");}
        @Override public void close(){owner.close();queue.drainAll(4);if(matrix!=null&&matrix.fired&&matrix.fixture==this)throw matrix.done;}
    }
    private static final Map<String,Integer> sites=new LinkedHashMap<>();
    private static void collect(){for(var event:ConcreteHostProbe.events())if(event.phase.equals("entry")){
        if(matrix==null)for(Barrier barrier:barriers)if(barrier.matches(event))witnesses.putIfAbsent(barrier.id(),scenario);
        for(var site:event.productionFrames){String key=site.className()+"|"+site.methodName()+"|"+site.line()+"|"+event.method;sites.merge(key,1,Integer::sum);}
    }ConcreteHostProbe.reset();if(matrix!=null&&!matrix.fired)ConcreteHostProbe.hook=matrix::hook;}
    private static void safe(Runnable action){try{action.run();}catch(RuntimeException expected){/* Individual native failure policies are asserted in focused controls below. */}}
    private static void callback(Object target,String method,Class<?>[] types,Object... args){try{var declared=target.getClass().getDeclaredMethod(method,types);declared.setAccessible(true);declared.invoke(target,args);}catch(java.lang.reflect.InvocationTargetException failure){if(failure.getCause() instanceof RuntimeException ordinary)throw ordinary;if(failure.getCause() instanceof Error fatal)throw fatal;throw new AssertionError(failure.getCause());}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static void positiveCallbacks(){
        try(Fixture f=new Fixture()){
            f.ready();NativeRenderer renderer=f.renderer();EditText edit=(EditText)renderer.view("field");Switch toggle=(Switch)renderer.view("toggle");
            edit.requestFocus();InputConnection connection=edit.onCreateInputConnection(new EditorInfo());check(connection!=null,"live IME acquisition");
            safe(()->connection.setComposingRegion(0,1));safe(()->connection.setComposingRegion(0,1,new android.view.inputmethod.TextAttribute()));
            safe(connection::finishComposingText);safe(()->connection.setSelection(1,1));safe(()->connection.setImeConsumesInput(true));
            NativeBridge.preparedPacket=packet(2);safe(()->connection.setComposingText("",1));NativeBridge.preparedPacket=packet(3);safe(()->connection.setComposingText("",1,new android.view.inputmethod.TextAttribute()));
            safe(connection::beginBatchEdit);safe(connection::endBatchEdit);safe(()->connection.clearMetaKeyStates(1));
            safe(()->edit.onKeyDown(KeyEvent.KEYCODE_ENTER,new KeyEvent(KeyEvent.ACTION_DOWN,KeyEvent.KEYCODE_ENTER)));
            safe(()->edit.performAccessibilityAction(0,new Bundle()));
            safe(()->edit.onTextContextMenuItem(0));
            if(edit.cursorDrawable!=null)edit.cursorDrawable.draw(new Canvas());
            if(edit.selectHandle!=null)edit.selectHandle.draw(new Canvas());
            edit.clearFocus();
            toggle.setVisibility(View.VISIBLE);toggle.hostWindowVisibility(View.VISIBLE);toggle.onWindowFocusChanged(true);toggle.requestFocus();toggle.hostDetach();toggle.hostAttach(f.root.getWindowToken());
            safe(()->f.root.dispatchTouchEvent(MotionEvent.obtain(0,1,MotionEvent.ACTION_CANCEL,0,0,0)));
            safe(()->f.root.getChildAt(0).dispatchKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN,0)));
            NativeBridge.preparedPacket=packet(4,"controls");safe(toggle::performClick);
            long down=10;safe(()->toggle.onTouchEvent(MotionEvent.obtain(down,down,MotionEvent.ACTION_DOWN,toggle.getWidth()-5,toggle.getHeight()/2f,0)));
            safe(()->toggle.onTouchEvent(MotionEvent.obtain(down,down+10,MotionEvent.ACTION_MOVE,10,toggle.getHeight()/2f,0)));
            safe(()->toggle.onTouchEvent(MotionEvent.obtain(down,down+20,MotionEvent.ACTION_CANCEL,10,toggle.getHeight()/2f,0)));
            safe(()->toggle.dispatchKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN,KeyEvent.KEYCODE_ENTER)));
            safe(()->toggle.performAccessibilityAction(0,new Bundle()));
            f.root.draw(new Canvas());
            NativeBridge.preparedPacket=packet(5,"replace");safe(()->renderer.view("button").performClick());
            check(NativeBridge.prepareCalls>=2,"native input was not synchronous");
        }collect();
        try(Fixture f=new Fixture("navigation")){
            f.ready();f.root.draw(new Canvas());safe(()->f.renderer().view("list").scrollTo(0,500));f.root.draw(new Canvas());
            check(f.fence().operation==null,"ordinary scroll invented operation");
        }collect();
    }
    private static void hierarchyControls(){
        try(Fixture f=new Fixture()){
            // Concrete root membership was changed by the fixture before the real refresh capture.
            f.root.addView(new View(f.activity));f.ready();
            NativeRenderer renderer=f.renderer();android.view.ViewGroup gate=(android.view.ViewGroup)field(renderer,"v2Gate");
            View desired=renderer.view("root");FrameLayout foreign=new FrameLayout(f.activity);foreign.layout(0,0,1000,1500);foreign.hostAttach(f.root.getWindowToken());
            gate.addView(new View(f.activity));
            NativeAppearanceViewsV2.Record section=renderer.inspectV2().get("section");section.group.addView(new View(f.activity));
            View body=renderer.view("text");section.group.removeView(body);foreign.addView(body);
            gate.removeView(desired);foreign.addView(desired);f.owner.onPause();f.queue.drainAll(4);
            check(desired.getParent()==gate,"concrete desired child was not reattached");
            f.root.removeView(gate);foreign.addView(gate);f.owner.onResume();f.queue.drainAll(4);check(gate.getParent()==f.root,"concrete gate not reattached");
        }collect();
    }
    private static void rollbackControls(){
        for(int step:new int[]{0,2,4,6,8,24})try(Fixture f=new Fixture()){
            f.ready();NativeRenderer renderer=f.renderer();renderer.testFaultV2(step,false);NativeBridge.preparedPacket=packet(2,"replace");safe(()->renderer.view("button").performClick());
            check(f.fence().terminal,"failed transaction did not retire");
        }
        collect();
    }
    private static void rollbackStateControls(){
        for(String scene:List.of("controls","navigation"))try(Fixture f=new Fixture(scene)){
            f.ready();NativeRenderer renderer=f.renderer();View selected=renderer.view(scene.equals("controls")?"field":"list");
            if(scene.equals("controls"))selected.requestFocus();
            renderer.testFaultV2(renderer.inspectV2().size()*2,false);
            f.owner.onPause();
            final boolean[] fired={false};
            java.util.function.BiConsumer<String,String> previousHook=ConcreteHostProbe.hook;
            ConcreteHostProbe.hook=(method,phase)->{if(previousHook!=null)previousHook.accept(method,phase);var event=ConcreteHostProbe.lastEvent();if(!f.fence().terminal&&!fired[0]&&phase.equals("entry")&&method.equals("View.setTag")&&event.productionFrames.stream().anyMatch(site->site.className().equals("dev.mixer.android.NativeRenderer")&&site.methodName().equals("attachV2"))){fired[0]=true;ConcreteHostProbe.hook=previousHook;if(scene.equals("controls"))selected.clearFocus();else selected.scrollTo(0,10);}};
            safe(()->f.queue.drainAll(4));ConcreteHostProbe.hook=previousHook;
            check(fired[0],"rollback native state mutation hook missed");check(f.fence().terminal,"rollback failure did not retire lifetime");
        }collect();
        try(Fixture f=new Fixture()){
            java.util.function.BiConsumer<String,String> previousHook=ConcreteHostProbe.hook;
            ConcreteHostProbe.hook=(method,phase)->{if(previousHook!=null)previousHook.accept(method,phase);if(method.equals("NativeBridge.commitV2")&&phase.equals("entry")){ConcreteHostProbe.hook=previousHook;f.owner.close();}};
            safe(()->f.queue.drainAll(4));ConcreteHostProbe.hook=previousHook;
            check(f.fence().terminal&&!f.owner.hasCommittedPresentation(),"commit reentry published a live presentation");
        }collect();
    }
    private static void imeSuccessor(){
        try(Fixture f=new Fixture("field")){
            f.ready();EditText editor=(EditText)f.renderer().view("field");editor.requestFocus();
            InputConnection connection=editor.onCreateInputConnection(new EditorInfo());
            NativeAppearanceViewsV2.Mutation original=NativeAppearanceViewsV2.Mutation.live(f.fence());
            OwnerLifecycleV2.Token before=f.fence().presentation;NativeBridge.preparedPacket=packet(2,"field","helloz");
            boolean committed=connection.commitText("z",1);if(!committed&&f.owner.cleanupLedger().primary()!=null)f.owner.cleanupLedger().primary().printStackTrace();
            check(committed,"completed IME delegate rejected after accepted successor: "+f.owner.cleanupLedger().cause()+" / "+f.owner.cleanupLedger().primary());
            check(editor.getText().toString().equals("helloz"),"real editor buffer not changed");
            check(f.fence().presentation!=before&&!f.fence().terminal,"IME successor not published");
            check(NativeBridge.prepareCalls==2&&NativeBridge.lastInput!=null,"ordinary edit not synchronous");
            boolean previousWouldFail=false;try{original.require();}catch(IllegalStateException expected){previousWouldFail=true;}
            check(previousWouldFail,"pre-fix old-scope postcheck witness missing");
            f.owner.onPause();int forwarded=ConcreteHostProbe.count("InputConnectionWrapper.commitText","entry");
            check(!connection.commitText("!",1),"retained sealed IME committed");
            check(editor.onCreateInputConnection(new EditorInfo())==null,"sealed new IME acquired native delegate");
            check(ConcreteHostProbe.count("InputConnectionWrapper.commitText","entry")==forwarded,"sealed edit reached native wrapper");
        }collect();
    }
    private static Throwable captureFailure(Runnable call){try{call.run();return null;}catch(RuntimeException|Error failure){return failure;}}
    private static void cancellationControls(){
        for(String selected:List.of("first","middle","last")){
            Fixture f=new Fixture("toggles");NativeRenderer renderer=null;Fatal fatal=new Fatal("independent cancel fatal");RuntimeException ordinary=new IllegalStateException("cancel pressed");
            try{
                f.ready();renderer=f.renderer();List<Switch> toggles=new ArrayList<>();
                for(String id:List.of("first","middle","last")){
                    Switch toggle=(Switch)renderer.view(id);toggles.add(toggle);NativeAppearanceViewsV2.Record record=renderer.inspectV2().get(id);var recipe=(AppearanceResolverV2.ToggleRecipe)record.binding.node().recipe();var metrics=recipe.metrics();
                    var g=AuthoredToggleInputV2.geometry(toggle.getWidth(),toggle.getHeight(),record.binding.density(),false,metrics.trackWidth64(),metrics.trackHeight64(),metrics.thumbWidth64(),metrics.thumbHeight64());
                    check(g!=null,"real toggle geometry missing");float y=toggle.getHeight()/2f;long time=100;
                    check(toggle.onTouchEvent(MotionEvent.obtain(time,time,MotionEvent.ACTION_DOWN,(float)g.offCenter(),y,0)),"toggle DOWN not owned");
                    check(toggle.onTouchEvent(MotionEvent.obtain(time,time+10,MotionEvent.ACTION_MOVE,(float)g.onCenter(),y,0)),"toggle drag not owned");
                    check(field(toggle,"disallowedParent")!=null,"drag did not own native interception");
                }
                Switch target=(Switch)renderer.view(selected);Set<Object> released=java.util.Collections.newSetFromMap(new java.util.IdentityHashMap<>());boolean[] recursed={false};
                ConcreteHostProbe.hook=(method,phase)->{
                    if(!phase.equals("entry"))return;var event=ConcreteHostProbe.lastEvent();
                    if(method.equals("View.requestDisallowInterceptTouchEvent"))released.add(event.receiver);
                    if(event.receiver==target&&method.equals("View.setPressed")){
                        assertGates(f,"cancel callback");check(field(target,"downParent")==null&&field(target,"disallowedParent")==null,"cancel ownership not consumed before native callback");
                        if(!recursed[0]){recursed[0]=true;f.owner.onPause();}throw ordinary;
                    }
                    if(event.receiver==target&&method.equals("View.invalidate"))throw fatal;
                };
                Throwable escaped=captureFailure(f.owner::onPause);ConcreteHostProbe.hook=null;
                check(escaped==fatal&&f.owner.cleanupLedger().firstFatal()==fatal,"cancellation independent fatal demoted");
                check(renderer.cleanupLedger().primary()==ordinary&&renderer.cleanupLedger().firstFatal()==fatal,"cancellation primary/fatal identity lost");
                for(Switch toggle:toggles){AuthoredToggleInputV2 touch=(AuthoredToggleInputV2)field(toggle,"touch");check(!touch.active()&&touch.binding()==null&&field(toggle,"downParent")==null&&field(toggle,"disallowedParent")==null,"later roster member retained ownership");}
                check(recursed[0]&&released.contains(target.getParent()),"independent parent release skipped");
                check(renderer.cleanupLedger().consumedSerial()==f.fence().sealSerial,"recursive newer serial not consumed");
                check(NativeBridge.prepareCalls==1&&NativeBridge.commitCalls==1,"cancellation invented engine work");
            }finally{ConcreteHostProbe.hook=null;captureFailure(f.owner::close);captureFailure(()->f.queue.drainAll(4));}
            check(NativeBridge.destroyCalls==1,"cancellation session not disposed once");collect();
        }collect();
    }
    private static void rendererReportControls(){
        for(NativeEnvironmentV2.RendererCause selected:NativeEnvironmentV2.RendererCause.values()){
            Fixture f=new Fixture();NativeRenderer renderer=null;Throwable primary=null;Fatal fatal=new Fatal("renderer current fatal");
            try{
                f.ready();renderer=f.renderer();
                switch(selected){
                    case INTERACTION_EXHAUSTED -> {renderer.testExhaustInteractionV2();renderer.view("button").performClick();}
                    case TERMINAL_VALIDATION_FAILED -> renderer.retireV2();
                    case CURRENT_CHECK_FATAL -> {ConcreteHostProbe.hook=(method,phase)->{if(method.equals("Resources.getConfiguration")&&phase.equals("entry")){ConcreteHostProbe.hook=null;throw fatal;}};check(captureFailure(renderer::presentationCurrentV2)==fatal,"current fatal not propagated");primary=fatal;}
                    case CAPTURE_FAILED -> {primary=new IllegalStateException("installed capture");Throwable failure=primary;f.owner.onPause();ConcreteHostProbe.hook=(method,phase)->{if(method.equals("AssetManager.open")&&phase.equals("entry")){ConcreteHostProbe.hook=null;throw (RuntimeException)failure;}};f.queue.drainAll(4);}
                    case ROLLBACK_FAILED -> {renderer.testFaultV2(0,true);f.owner.onPause();f.queue.drainAll(4);}
                    case CANCELLATION_FAILED -> {Switch toggle=(Switch)renderer.view("toggle");toggle.setPressed(true);primary=new IllegalStateException("cancel native setter");Throwable failure=primary;ConcreteHostProbe.hook=(method,phase)->{if(method.equals("View.setPressed")&&phase.equals("entry")&&ConcreteHostProbe.lastEvent().receiver==toggle){ConcreteHostProbe.hook=null;throw (RuntimeException)failure;}};f.owner.onPause();}
                }
                ConcreteHostProbe.hook=null;check(f.fence().terminal,"renderer cause did not close fence "+selected);check(f.owner.cleanupLedger().rendererCause()==selected,"renderer typed cause lost "+selected+" / "+f.owner.cleanupLedger().rendererCause());
                if(primary!=null)check(f.owner.cleanupLedger().primary()==primary,"renderer primary lost "+selected);
                if(selected==NativeEnvironmentV2.RendererCause.CURRENT_CHECK_FATAL)check(f.owner.cleanupLedger().firstFatal()==fatal,"current firstFatal lost");
                NativeEnvironmentV2.Observer observer=(NativeEnvironmentV2.Observer)field(f.owner,"observer");observer.rendererTerminal(null,null,new IllegalStateException("late"),new Fatal("late"));
                int destroyed=NativeBridge.destroyCalls;captureFailure(renderer::retireV2);check(NativeBridge.destroyCalls==destroyed,"late renderer report repeated disposal");
            }finally{ConcreteHostProbe.hook=null;captureFailure(f.owner::close);captureFailure(()->f.queue.drainAll(4));}
            check(NativeBridge.destroyCalls==1,"renderer report disposal not once "+selected);collect();
        }collect();
    }
    private static void reportTailControls(){
        for(boolean throwing:new boolean[]{false,true})try(Fixture f=new Fixture()){
            f.ready();NativeRenderer renderer=f.renderer();NativeEnvironmentV2.Observer observer=(NativeEnvironmentV2.Observer)field(f.owner,"observer");
            NativeRenderer foreign=new NativeRenderer(f.activity,ignored->{},observer,f.fence());
            check(captureFailure(()->observer.rendererTerminal(foreign,NativeEnvironmentV2.RendererCause.CAPTURE_FAILED,null,null)) instanceof IllegalArgumentException,"foreign renderer terminal source accepted");check(!f.fence().terminal,"foreign report retired owner");
            if(throwing)f.queue.postFailure=new IllegalStateException("tail post");else f.queue.postResult=false;
            boolean[] reached={false};ConcreteHostProbe.hook=(method,phase)->{if(method.equals("Handler.post")&&phase.equals("entry")){
                reached[0]=true;ConcreteHostProbe.hook=null;NativeCoordinatorV2 coordinator=(NativeCoordinatorV2)field(f.owner,"coordinator");check(f.fence().rendererReportActive&&f.owner.cleanupLedger().input()==NativeOwnerV2.Outcome.RETURNED&&!coordinator.inputCancellationInProgress(),"real report frame mislabeled completed cancellation");check(coordinator.busyForOwnerDisposal()&&f.owner.cleanupLedger().coordinator()==NativeOwnerV2.Outcome.DEFERRED,"real report did not defer disposal independently");}};
            renderer.retireV2();ConcreteHostProbe.hook=null;check(reached[0],"real report tail callback missed");check(f.fence().terminal&&NativeBridge.destroyCalls==0&&f.queue.queued()==0,"failed tail post disposed active report or invented delivery");
            check(field(f.owner,"pendingCloseResource")!=null&&f.owner.cleanupLedger().coordinator()==NativeOwnerV2.Outcome.DEFERRED,"failed tail post forgot exact close disposition");
            f.owner.close();check(NativeBridge.destroyCalls==1&&f.owner.cleanupLedger().coordinator()==NativeOwnerV2.Outcome.RETURNED,"idle owner tail failed to consume retained close");
            android.os.Looper.hostSetMain(false);try{
                check(captureFailure(()->observer.rendererTerminal(null,null,null,new Fatal("stale wrong thread"))) instanceof IllegalStateException,"stale observer report skipped main first");
                check(captureFailure(renderer::retireV2) instanceof IllegalStateException,"stale renderer skipped main first");
            }finally{android.os.Looper.hostReset();}
        }collect();
    }
    private static void pendingRosterControls(){
        for(boolean terminal:new boolean[]{false,true})try(Fixture f=new Fixture()){
            f.ready();NativeRenderer renderer=f.renderer();boolean[] reached={false};NativeBridge.preparedPacket=packet(2,"replace");
            ConcreteHostProbe.hook=(method,phase)->{
                var event=ConcreteHostProbe.lastEvent();if(reached[0]||!method.equals("View.setTag")||!phase.equals("entry")||event.productionFrames.stream().noneMatch(frame->frame.className().equals("dev.mixer.android.NativeRenderer")&&frame.methodName().equals("attachV2")))return;
                reached[0]=true;Object pending=field(renderer,"v2Pending");check(pending!=null,"pending roster absent at selected attach call");
                Set<NativeAppearanceViewsV2.Record> unique=java.util.Collections.newSetFromMap(new java.util.IdentityHashMap<>());int total=0;
                Object[][] lists={(Object[])field(renderer,"v2Roster"),(Object[])field(pending,"targetRoster"),(Object[])field(pending,"detachedRoster")};int[] counts={(Integer)field(renderer,"v2RosterCount"),(Integer)field(pending,"targetCount"),(Integer)field(pending,"detachedCount")};
                for(int row=0;row<lists.length;row++)for(int i=0;i<counts[row];i++){total++;unique.add((NativeAppearanceViewsV2.Record)lists[row][i]);}
                check(unique.size()<total,"fixture did not create duplicate identities across real rosters");int attempted=renderer.cleanupLedger().attempts();
                if(terminal)f.owner.close();else f.owner.onPause();
                check(renderer.cleanupLedger().attempts()==attempted+unique.size(),"same record cancelled more than once per pass");
                for(var record:unique)check(record.cancelClaim==f.fence().sealSerial,"real roster record claim missing");
                check(NativeBridge.destroyCalls==0&&f.fence().operation!=null,"active coordinator disposed before native call returned");check(f.owner.cleanupLedger().input()==NativeOwnerV2.Outcome.RETURNED&&!((NativeCoordinatorV2)field(f.owner,"coordinator")).inputCancellationInProgress(),"completed active cancellation mislabeled as ongoing");assertGates(f,"pending/current/targets cancellation");
            };
            captureFailure(()->renderer.view("button").performClick());ConcreteHostProbe.hook=null;check(reached[0],"pending roster callback missed");
            if(terminal)check(f.fence().terminal&&NativeBridge.destroyCalls==1,"terminal pending roster did not retire after return");
            else{check(!f.fence().terminal&&f.queue.queued()==1,"dirty pending roster did not coalesce");f.queue.drainAll(4);check(f.owner.hasCommittedPresentation()&&NativeBridge.prepareCalls==2&&NativeBridge.commitCalls==2,"dirty roster refresh performed engine work");}
        }collect();
    }
    private static void concreteFatalAndDeferredControls(){
        for(String surface:List.of("draw","input")){
            Fatal fatal=new Fatal("current "+surface);Fixture f=new Fixture();
            try{f.ready();NativeRenderer renderer=f.renderer();ConcreteHostProbe.hook=(method,phase)->{if(method.equals("Resources.getConfiguration")&&phase.equals("entry")){ConcreteHostProbe.hook=null;throw fatal;}};
                check(captureFailure(surface.equals("draw")?()->f.root.draw(new Canvas()):()->renderer.view("button").performClick())==fatal,"actual current fatal swallowed on "+surface);
                check(f.fence().terminal&&f.owner.cleanupLedger().rendererCause()==NativeEnvironmentV2.RendererCause.CURRENT_CHECK_FATAL&&f.owner.cleanupLedger().firstFatal()==fatal,"actual current fatal route "+surface);
            }finally{ConcreteHostProbe.hook=null;captureFailure(f.owner::close);captureFailure(()->f.queue.drainAll(4));}check(NativeBridge.destroyCalls==1,"current fatal disposition repeated");collect();
        }
        for(boolean error:new boolean[]{false,true}){
            Fatal fatal=new Fatal("environment capture fatal");Throwable selected=error?fatal:new IllegalStateException("environment capture ordinary");Fixture f=new Fixture();
            try{f.ready();f.owner.onPause();ConcreteHostProbe.hook=(method,phase)->{if(method.equals("Resources.getConfiguration")&&phase.equals("entry")){ConcreteHostProbe.hook=null;ConcreteHostProbe.fail(selected);}};captureFailure(()->f.queue.drainAll(4));
                check(f.fence().terminal&&f.owner.cleanupLedger().rendererCause()==NativeEnvironmentV2.RendererCause.CAPTURE_FAILED&&f.owner.cleanupLedger().primary()==selected,"environment capture typed route lost");if(error)check(f.owner.cleanupLedger().firstFatal()==fatal,"environment capture fatal demoted");
            }finally{ConcreteHostProbe.hook=null;captureFailure(f.owner::close);captureFailure(()->f.queue.drainAll(4));}collect();
        }
        try(Fixture f=new Fixture()){
            boolean[] reached={false};ConcreteHostProbe.hook=(method,phase)->{if(!reached[0]&&method.equals("NativeBridge.commitV2")&&phase.equals("beforeReturn")){
                reached[0]=true;ConcreteHostProbe.hook=null;NativeRenderer renderer=(NativeRenderer)field(field(f.owner,"opening"),"renderer");NativeEnvironmentV2.Observer observer=(NativeEnvironmentV2.Observer)field(f.owner,"observer");
                check(f.fence().commitFinish,"commit interval flag absent");renderer.retireV2();check(!(Boolean)field(observer,"retired")&&!(Boolean)field(renderer,"v2ReportClaimed"),"renderer reported inside successful commit/finish interval");
                check(field(field(renderer,"v2Cleanup"),"deferredCause")==NativeEnvironmentV2.RendererCause.TERMINAL_VALIDATION_FAILED,"deferred cause lost");
            }};f.queue.drainAll(4);ConcreteHostProbe.hook=null;check(reached[0]&&f.fence().terminal&&f.owner.cleanupLedger().rendererCause()==NativeEnvironmentV2.RendererCause.TERMINAL_VALIDATION_FAILED,"deferred real renderer route missed");check(NativeBridge.commitCalls==1&&NativeBridge.destroyCalls==1&&!f.owner.hasCommittedPresentation(),"deferred terminal finish published or leaked");
        }collect();
    }
    private static void cancellationLedgerControls(){
        try(Fixture f=new Fixture()){
            f.ready();boolean[] reached={false};ConcreteHostProbe.hook=(method,phase)->{
                var event=ConcreteHostProbe.lastEvent();if(!reached[0]&&method.equals("View.invalidate")&&phase.equals("entry")&&event.receiver!=null&&event.receiver.getClass().getSimpleName().equals("Gate")&&event.productionFrames.stream().anyMatch(frame->frame.className().equals("dev.mixer.android.NativeRenderer")&&frame.methodName().equals("cancelInputV2"))){
                    reached[0]=true;ConcreteHostProbe.hook=null;f.owner.onPause();NativeCoordinatorV2 coordinator=(NativeCoordinatorV2)field(f.owner,"coordinator");check(f.owner.cleanupLedger().input()==NativeOwnerV2.Outcome.IN_PROGRESS&&coordinator.inputCancellationInProgress(),"real recursive cancellation status missing");check(coordinator.busyForOwnerDisposal()&&NativeBridge.destroyCalls==0,"recursive cancellation disposed coordinator");
                }};
            f.owner.onPause();ConcreteHostProbe.hook=null;NativeCoordinatorV2 coordinator=(NativeCoordinatorV2)field(f.owner,"coordinator");check(reached[0]&&f.owner.cleanupLedger().input()==NativeOwnerV2.Outcome.RETURNED&&!coordinator.inputCancellationInProgress(),"real outer pass did not replace recursive status");check(!coordinator.busyForOwnerDisposal()&&NativeBridge.destroyCalls==0,"returned real cancellation conflated disposal");
            f.queue.drainAll(4);check(f.owner.hasCommittedPresentation()&&f.owner.cleanupLedger().input()==NativeOwnerV2.Outcome.RETURNED,"real dirty drain cancellation result lost");
            f.owner.close();android.os.Looper.hostSetMain(false);try{check(captureFailure(coordinator::inputCancellationInProgress) instanceof IllegalStateException,"stale real cancellation status skipped main first");check(captureFailure(f.renderer()::cancellationInProgressV2) instanceof IllegalStateException,"stale renderer status skipped main first");}finally{android.os.Looper.hostReset();}
        }collect();
    }
    private static void assertPublished(Fixture f,String where){
        OwnerLifecycleV2 core=(OwnerLifecycleV2)field(f.owner,"core");var state=core.snapshot();
        check(state.phase()==OwnerLifecycleV2.Phase.LIVE&&!state.dirty()&&state.presentation()==f.fence().presentation&&state.operation()==null&&state.pendingDrain()==null&&state.resource()==field(f.owner,"coordinator"),where+": real clean completion missing");
        check(f.fence().drawAllowed&&(Boolean)field(f.renderer(),"v2Open")&&(Boolean)field(field(f.renderer(),"v2Gate"),"open"),where+": clean concrete publication missing");
    }
    private static void completionPublicationControls(){
        for(String operation:List.of("initial","input","refresh"))for(String action:List.of("clean","prepare-dirty","hook-dirty","hook-terminal","hook-ordinary","hook-fatal")){
            int target=operation.equals("initial")?1:2;int[] completions={0},posts={0};boolean[] reached={false},dirtied={false};RuntimeException ordinary=new IllegalStateException("completion ordinary");Fatal fatal=new Fatal("completion fatal");
            Runnable hook=()->{
                completions[0]++;if(completions[0]!=target)return;Fixture f=activeFixture;reached[0]=true;assertGates(f,"successful finish before completion hook");
                check(!f.fence().commitFinish&&f.fence().operation!=null&&((OwnerLifecycleV2)field(f.owner,"core")).snapshot().operation()==f.fence().operation,"completion hook escaped real uncompleted operation or commit interval");
                if(action.equals("hook-dirty"))f.owner.onPause();else if(action.equals("hook-terminal"))f.owner.close();else if(action.equals("hook-ordinary"))throw ordinary;else if(action.equals("hook-fatal"))throw fatal;
                assertGates(f,"completion hook returned");
            };
            try(Fixture f=new Fixture("controls",hook)){
                if(!operation.equals("initial"))f.ready();OwnerLifecycleV2.Token previous=f.fence().presentation;int prepared=NativeBridge.prepareCalls,committed=NativeBridge.commitCalls;
                ConcreteHostProbe.hook=(method,phase)->{
                    var event=ConcreteHostProbe.lastEvent();if(action.equals("prepare-dirty")&&!dirtied[0]&&phase.equals("entry")&&((!operation.equals("refresh")&&method.equals("NativeBridge.prepareV2"))||(operation.equals("refresh")&&method.equals("View.<init>")&&event.productionFrames.stream().anyMatch(frame->frame.className().equals("dev.mixer.android.NativeRenderer")&&frame.methodName().equals("prepareV2"))))){dirtied[0]=true;f.owner.onPause();}
                    if(method.equals("Handler.post")&&phase.equals("entry")&&f.fence().operation!=null){var state=((OwnerLifecycleV2)field(f.owner,"core")).snapshot();if(state.phase()==OwnerLifecycleV2.Phase.LIVE&&state.dirty()){posts[0]++;assertGates(f,"dirty core completion Handler.post entry");}}
                };
                Runnable perform;if(operation.equals("initial"))perform=f.queue::drainOne;else if(operation.equals("input")){NativeBridge.preparedPacket=packet(2);perform=()->f.renderer().view("button").performClick();}else {f.owner.onPause();perform=f.queue::drainOne;}
                Throwable escaped=captureFailure(perform);ConcreteHostProbe.hook=null;check(reached[0],"completion family hook missed "+operation+"/"+action);int transactions=operation.equals("refresh")?0:1;
                check(NativeBridge.prepareCalls==prepared+transactions&&NativeBridge.commitCalls==committed+transactions,"successful completion changed engine outcome "+operation+"/"+action);
                if(action.equals("prepare-dirty")||action.equals("hook-dirty")){
                    check(escaped==null&&(!action.equals("prepare-dirty")||dirtied[0])&&posts[0]==1&&f.queue.queued()==1,"dirty successful completion did not own exactly one drain "+operation);assertGates(f,"dirty completion returned to caller");
                    var state=((OwnerLifecycleV2)field(f.owner,"core")).snapshot();check(state.phase()==OwnerLifecycleV2.Phase.LIVE&&state.dirty()&&state.operation()==null&&state.presentation()!=previous&&!f.fence().terminal,"dirty successful completion was retired or fabricated");
                    byte[] retained=(byte[])field(field(f.owner,"coordinator"),"committedPacket");f.queue.drainAll(4);assertPublished(f,"dirty follow-up refresh");check(field(field(f.owner,"coordinator"),"committedPacket")==retained&&NativeBridge.prepareCalls==prepared+transactions&&NativeBridge.commitCalls==committed+transactions&&!f.fence().inputAllowed,"dirty follow-up changed retained packet/engine or reopened background input");
                }else if(action.equals("clean")){
                    check(escaped==null&&posts[0]==0&&f.fence().presentation!=previous,"clean completion did not publish fresh actual token");assertPublished(f,"clean family completion");
                    if(!f.fence().inputAllowed){f.owner.onResume();f.queue.drainAll(4);}OwnerLifecycleV2.Token before=f.fence().presentation;NativeBridge.preparedPacket=packet(operation.equals("input")?3:2);f.renderer().view("button").performClick();assertPublished(f,"clean native successor");check(f.fence().presentation!=before&&NativeBridge.prepareCalls==prepared+transactions+1&&NativeBridge.commitCalls==committed+transactions+1,"clean completed successor was blocked");
                    check(captureFailure(()->f.renderer().publishScalarV2(before)) instanceof IllegalArgumentException,"stale scalar publication token accepted");
                }else {
                    assertGates(f,"failed/retired completion returned");check(f.fence().terminal&&NativeBridge.destroyCalls==1,"completion callback reopened or leaked retired owner");
                    if(action.equals("hook-fatal"))check(escaped==fatal&&f.owner.cleanupLedger().firstFatal()==fatal&&f.owner.cleanupLedger().primary()==fatal,"completion fatal lost");
                    else if(action.equals("hook-ordinary"))check(escaped==null&&f.owner.cleanupLedger().primary()==ordinary&&f.owner.cleanupLedger().coreCompletionUnreported(),"completion ordinary failure lost or fabricated completion");
                    else check(escaped==null&&!f.owner.cleanupLedger().coreCompletionUnreported(),"completion retirement invented failure");
                }
            }catch(Fatal expected){check(expected==fatal,"wrong completion fatal");}finally{ConcreteHostProbe.hook=null;}collect();
        }
    }
    private interface ImeCall {boolean call(InputConnection connection);}
    private static void explicitHelper(String name,Class<?>[] types,Object... args){try{var method=NativeAppearanceViewsV2.class.getDeclaredMethod(name,types);method.setAccessible(true);method.invoke(null,args);}catch(java.lang.reflect.InvocationTargetException failure){if(failure.getCause() instanceof RuntimeException ordinary)throw ordinary;if(failure.getCause() instanceof Error fatal)throw fatal;throw new AssertionError(failure.getCause());}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static void explicitScopeControls(){
        try(Fixture f=new Fixture("navigation")){
            f.ready();Map<String,NativeAppearanceViewsV2.Record> records=f.renderer().inspectV2();NativeAppearanceViewsV2.Record root=records.get("nav"),list=records.get("list");NativeAppearanceViewsV2.Mutation captured=NativeAppearanceViewsV2.Mutation.live(f.fence());int[] reached={0};
            ConcreteHostProbe.hook=(method,phase)->{var event=ConcreteHostProbe.lastEvent();if(method.equals("View.measure")&&phase.equals("entry"))for(var record:records.values())if(event.receiver==record.view){reached[0]++;check(field(record,"scoped")==captured,"recursive native layout recaptured mutation scope");}};
            NativeAppearanceViewsV2.layoutRoot(root,f.root.getWidth(),f.root.getHeight(),root.binding.plan().environment.safeArea64(),captured);ConcreteHostProbe.hook=null;check(reached[0]>2,"explicit live recursive layout path missing");for(var record:records.values())check(field(record,"scoped")==null,"native layout scope was retained after synchronous return");
            f.owner.onPause();f.queue.drainAll(4);check(captured.token!=f.fence().presentation&&!captured.current(),"real refresh did not supersede old helper scope");
            f.owner.onPause();NativeAppearanceViewsV2.Mutation cleanup=NativeAppearanceViewsV2.Mutation.cleanup(f.fence());cleanup.require();check(cleanup.current(),"dedicated cleanup scope was not sealed");
            var nav=(AppearanceResolverV2.NavigationRecipe)root.binding.node().recipe();var ink=((AppearanceResolverV2.NavigationPaints)root.binding.plan().style(root.id,false,false).paints()).expanded();
            for(NativeAppearanceViewsV2.Mutation rejected:List.of(captured,cleanup)){
            List<Runnable> calls=List.of(
                ()->new NativeAppearanceViewsV2.Record(f.activity,root.binding.source(),root.input,rejected),
                ()->root.bind(root.binding,root.geometry,false,rejected),
                ()->NativeAppearanceViewsV2.measure(root,records,64000,96000,rejected),
                ()->NativeAppearanceViewsV2.installChildren(root,records,rejected),
                ()->NativeAppearanceViewsV2.layoutRoot(root,1000,1500,root.binding.plan().environment.safeArea64(),rejected),
                ()->explicitHelper("measureList",new Class<?>[]{NativeAppearanceViewsV2.Record.class,Map.class,AppearanceResolverV2.ListRecipe.class,long.class,long.class,NativeAppearanceViewsV2.Mutation.class},list,records,list.binding.node().recipe(),64000L,96000L,rejected),
                ()->explicitHelper("layout",new Class<?>[]{NativeAppearanceViewsV2.Record.class,long.class,long.class,long.class,long.class,NativeAppearanceViewsV2.Mutation.class},root,0L,0L,0L,0L,rejected),
                ()->root.group.onLayout(true,0,0,1000,1500,rejected),
                ()->callback(root.group,"titleLayout",new Class<?>[]{android.widget.TextView.class,NativeAppearanceViewsV2.Box.class,NativeAppearanceViewsV2.Binding.class,NativeAppearanceViewsV2.Mutation.class},root.header,root.geometry.header,root.binding,rejected),
                ()->explicitHelper("defaults",new Class<?>[]{android.widget.TextView.class,NativeAppearanceViewsV2.Mutation.class},root.header,rejected),
                ()->explicitHelper("text",new Class<?>[]{android.widget.TextView.class,AppearanceResolverV2.Text.class,NativeAppearanceViewsV2.Binding.class,NativeAppearanceViewsV2.Mutation.class},root.header,nav.expandedTitle(),root.binding,rejected),
                ()->explicitHelper("bindTitle",new Class<?>[]{android.widget.TextView.class,AppearanceResolverV2.Text.class,NativeAppearanceViewsV2.Binding.class,AppearanceDescriptorV2.Color.class,NativeAppearanceViewsV2.Mutation.class},root.header,nav.expandedTitle(),root.binding,ink,rejected),
                ()->explicitHelper("title",new Class<?>[]{android.widget.TextView.class,AppearanceResolverV2.Text.class,long.class,AppearanceDescriptorV2.Insets.class,NativeAppearanceViewsV2.Binding.class,NativeAppearanceViewsV2.Mutation.class},root.header,nav.expandedTitle(),64000L,nav.metrics().expandedInsets64(),root.binding,rejected));
            for(Runnable call:calls){int before=ConcreteHostProbe.events().size();check(captureFailure(call) instanceof IllegalStateException,"explicit stale helper scope was replaced by current input scope");check(ConcreteHostProbe.events().size()==before,"stale explicit helper performed native work");}
            }
        }collect();
    }
    private static void terminalContinuationControls(){
        for(String path:List.of("start","resume","drain")){
            boolean[] reached={false};int[] readiness={0};
            java.util.function.BiConsumer<String,String> hook=(method,phase)->{
                var event=ConcreteHostProbe.lastEvent();if(!reached[0]&&phase.equals("entry")&&((path.equals("start")&&method.equals("Context.registerComponentCallbacks"))||(!path.equals("start")&&method.equals("View.invalidate")&&event.receiver!=null&&event.receiver.getClass().getSimpleName().equals("Gate")&&event.productionFrames.stream().anyMatch(frame->frame.className().equals("dev.mixer.android.NativeRenderer")&&frame.methodName().equals("cancelInputV2"))))){reached[0]=true;activeFixture.owner.close();}
                if(reached[0]&&phase.equals("entry")&&event.productionFrames.stream().anyMatch(frame->frame.className().equals("dev.mixer.android.NativeOwnerV2")&&(frame.methodName().equals("seedFocus")||frame.methodName().equals("probeWindow"))))readiness[0]++;
            };
            if(path.equals("start"))ConcreteHostProbe.hook=hook;
            try(Fixture f=new Fixture()){
                if(!path.equals("start")){f.ready();if(path.equals("drain"))f.owner.onPause();ConcreteHostProbe.hook=hook;if(path.equals("resume"))f.owner.onResume();else f.queue.drainAll(4);}
                ConcreteHostProbe.hook=null;check(reached[0]&&readiness[0]==0,"terminal "+path+" continued ordinary readiness reads: "+readiness[0]);check(f.fence().terminal&&((OwnerLifecycleV2)field(f.owner,"core")).snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED,"terminal continuation changed real core state");check(NativeBridge.prepareCalls==(path.equals("start")?0:1),"terminal continuation advanced engine");
            }finally{ConcreteHostProbe.hook=null;}collect();
        }
    }
    private static void latePostControls(){
        for(String phase:List.of("entry","beforeReturn"))for(boolean terminal:new boolean[]{false,true}){
            RuntimeException primary=new IllegalStateException("actual post "+phase);boolean[] reached={false};ConcreteHostProbe.hook=(method,at)->{if(!reached[0]&&method.equals("Handler.post")&&at.equals(phase)){reached[0]=true;if(terminal){activeFixture.owner.close();check(activeFixture.owner.cleanupLedger().handler()==NativeOwnerV2.Outcome.DEFERRED,"actual inflight post claimed removed");}else throw primary;}};
            try(Fixture f=new Fixture()){
                ConcreteHostProbe.hook=null;check(reached[0]&&f.fence().terminal&&f.queue.removeCalls==1&&f.queue.queued()==0&&f.owner.cleanupLedger().handler()==NativeOwnerV2.Outcome.RETURNED,"actual late post cleanup missing");check(NativeBridge.createCalls==0&&(terminal||f.owner.cleanupLedger().primary()==primary),"actual post cleanup acquired engine or changed primary");
            }finally{ConcreteHostProbe.hook=null;}collect();
        }
    }
    private static void focusAdmissionControls(){
        for(String state:List.of("focusLoss","dirty","terminal","fatal")){
            Fatal fatal=new Fatal("actual IME fresh focus fatal");
            try(Fixture f=new Fixture("field")){
                f.ready();EditText editor=(EditText)f.renderer().view("field");editor.requestFocus();InputConnection connection=editor.onCreateInputConnection(new EditorInfo());int prepared=NativeBridge.prepareCalls,committed=NativeBridge.commitCalls;int[] eventFocus={0};boolean[] reached={false,false};
                ConcreteHostProbe.hook=(method,phase)->{
                    var event=ConcreteHostProbe.lastEvent();boolean fresh=event.productionFrames.stream().anyMatch(frame->frame.className().equals("dev.mixer.android.NativeOwnerV2")&&frame.methodName().equals("seedFocus"));
                    if(!fresh&&method.equals("View.hasWindowFocus")&&phase.equals("beforeReturn")&&event.receiver==f.root&&event.productionFrames.stream().anyMatch(frame->frame.className().equals("dev.mixer.android.NativeRenderer$2")&&frame.methodName().equals("event"))&&++eventFocus[0]==2)f.root.windowFocus=false;
                    if(!reached[0]&&fresh&&method.equals("View.hasWindowFocus")&&phase.equals("entry")&&event.receiver==f.root){
                        reached[0]=true;assertGates(f,"actual IME fresh focus callback entry");int delegates=ConcreteHostProbe.count("BaseInputConnection.commitText","entry");check(!connection.commitText("reentrant",1)&&ConcreteHostProbe.count("BaseInputConnection.commitText","entry")==delegates,"fresh focus callback forwarded reentrant IME");
                        if(state.equals("terminal"))f.owner.close();else if(!state.equals("focusLoss"))f.owner.onPause();if(state.equals("fatal"))throw fatal;
                    }
                    if(fresh&&method.equals("Handler.post")&&phase.equals("entry")){reached[1]=true;assertGates(f,"actual IME fresh focus Handler.post");}
                };
                Throwable escaped=null;boolean result=false;try{result=connection.commitText("z",1);}catch(RuntimeException|Error failure){escaped=failure;}finally{ConcreteHostProbe.hook=null;}
                check(eventFocus[0]==2&&reached[0]&&!result&&NativeBridge.prepareCalls==prepared&&NativeBridge.commitCalls==committed,"actual IME focus change dispatched transaction or missed exact path: "+state+" eventFocus="+eventFocus[0]+" reached="+reached[0]+" result="+result+" escaped="+escaped+" prepare="+NativeBridge.prepareCalls+" commit="+NativeBridge.commitCalls);
                if(state.equals("fatal"))check(escaped==fatal&&f.fence().terminal,"actual IME fresh focus fatal swallowed");
                else if(state.equals("terminal"))check(escaped==null&&f.fence().terminal,"actual IME terminal callback reopened input");
                else {
                    OwnerLifecycleV2 core=(OwnerLifecycleV2)field(f.owner,"core");check(escaped==null&&reached[1]&&core.snapshot().dirty()&&!core.snapshot().focused()&&f.queue.queued()==1,"actual IME focus dirty mapping did not coalesce");
                    f.queue.drainAll(4);check(f.fence().drawAllowed&&!f.fence().inputAllowed&&NativeBridge.prepareCalls==prepared&&NativeBridge.commitCalls==committed,"actual focus refresh advanced engine or reopened input");
                    f.root.hostWindowFocus(true);if(state.equals("dirty"))f.owner.onResume();f.queue.drainAll(4);check(f.fence().inputAllowed,"focused input did not recover after real lifecycle drain");
                    ConcreteHostProbe.hook=(method,phase)->{if(method.equals("NativeBridge.prepareV2")&&phase.equals("entry"))NativeBridge.preparedPacket=packet(2,"field",editor.getText().toString());};
                    check(connection.commitText("y",1)&&NativeBridge.prepareCalls==prepared+1&&NativeBridge.commitCalls==committed+1,"recovered actual IME completed successor rejected");ConcreteHostProbe.hook=null;
                }
            }catch(Fatal expected){check(expected==fatal,"wrong actual focus fatal");}finally{ConcreteHostProbe.hook=null;}collect();
        }
    }
    private record ImeFamily(String name,String leaf,ImeCall call) {}
    private static List<ImeFamily> imeFamilies(){return List.of(
        new ImeFamily("beginBatchEdit","beginBatchEdit",InputConnection::beginBatchEdit),
        new ImeFamily("endBatchEdit","endBatchEdit",InputConnection::endBatchEdit),
        new ImeFamily("clearMetaKeyStates","clearMetaKeyStates",c->c.clearMetaKeyStates(1)),
        new ImeFamily("commitText","commitText",c->c.commitText("z",1)),
        new ImeFamily("commitTextWithAttributes","commitTextWithAttributes",c->c.commitText("z",1,new android.view.inputmethod.TextAttribute())),
        new ImeFamily("setComposingText","setComposingText",c->c.setComposingText("z",1)),
        new ImeFamily("setComposingTextWithAttributes","setComposingTextWithAttributes",c->c.setComposingText("z",1,new android.view.inputmethod.TextAttribute())),
        new ImeFamily("setComposingRegion","setComposingRegion",c->c.setComposingRegion(0,1)),
        new ImeFamily("setComposingRegionWithAttributes","setComposingRegion",c->c.setComposingRegion(0,1,new android.view.inputmethod.TextAttribute())),
        new ImeFamily("finishComposingText","finishComposingText",InputConnection::finishComposingText),
        new ImeFamily("deleteSurroundingText","deleteSurroundingText",c->c.deleteSurroundingText(1,0)),
        new ImeFamily("deleteSurroundingTextInCodePoints","deleteSurroundingTextInCodePoints",c->c.deleteSurroundingTextInCodePoints(1,0)),
        new ImeFamily("setSelection","setSelection",c->c.setSelection(0,1)),
        new ImeFamily("performEditorAction","performEditorAction",c->c.performEditorAction(EditorInfo.IME_ACTION_DONE)),
        new ImeFamily("sendKeyEvent","sendKeyEvent",c->c.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN,KeyEvent.KEYCODE_SPACE))),
        new ImeFamily("setImeConsumesInput","setImeConsumesInput",c->c.setImeConsumesInput(true)),
        new ImeFamily("commitCompletion","commitCompletion",c->c.commitCompletion(new android.view.inputmethod.CompletionInfo(1,0,"z"))));}
    private static void imeControls(){
        for(ImeFamily family:imeFamilies())for(String state:List.of("current","successor","terminal","dirty","stale","fatal")){
            try(Fixture f=new Fixture("field")){
                f.ready();EditText editor=(EditText)f.renderer().view("field");editor.requestFocus();InputConnection connection=editor.onCreateInputConnection(new EditorInfo());
                NativeAppearanceViewsV2.Record record=f.renderer().inspectV2().get("field");
                // Controlled native delegates can complete without notifying a feature callback. Keep the real binding guard.
                record.changing=!state.equals("successor");if(!state.equals("successor"))editor.editorListener=null;
                OwnerLifecycleV2.Token captured=f.fence().presentation;NativeAppearanceViewsV2.Mutation old=NativeAppearanceViewsV2.Mutation.live(f.fence());
                String nativeMethod="BaseInputConnection."+family.leaf();int before=ConcreteHostProbe.count(nativeMethod,"entry");Fatal fatal=new Fatal("IME "+family.name());boolean[] reached={false};
                java.util.function.BiConsumer<String,String> previous=ConcreteHostProbe.hook;
                if(state.equals("successor")||state.equals("fatal"))ConcreteHostProbe.hook=(method,phase)->{
                    if(previous!=null)previous.accept(method,phase);
                    if(state.equals("successor")&&method.equals("NativeBridge.prepareV2")&&phase.equals("entry"))NativeBridge.preparedPacket=packet(2,"field",editor.getText().toString());
                    if(!reached[0]&&method.equals(nativeMethod)&&phase.equals("beforeReturn")){
                        reached[0]=true;ConcreteHostProbe.hook=previous;
                        if(state.equals("fatal"))throw fatal;
                        if(f.fence().presentation==captured){record.changing=false;NativeBridge.preparedPacket=packet(2,"field",editor.getText().toString());editor.hostReplace(0,editor.getText().length(),editor.getText().toString());}
                    }};
                if(state.equals("terminal"))f.owner.close();else if(state.equals("dirty"))f.owner.onPause();else if(state.equals("stale"))f.activity.getResources().configuration.uiMode=android.content.res.Configuration.UI_MODE_NIGHT_YES;
                Throwable escaped=null;boolean returned=false;try{returned=family.call().call(connection);}catch(RuntimeException|Error failure){escaped=failure;}finally{ConcreteHostProbe.hook=previous;record.changing=false;}
                if(state.equals("current"))check(returned!=family.name().equals("performEditorAction")&&escaped==null&&f.fence().presentation==captured,"IME exact current "+family.name());
                else if(state.equals("successor")){
                    check(reached[0]&&returned&&escaped==null&&f.fence().presentation!=captured&&!f.fence().terminal,"IME completed successor "+family.name());
                    boolean rejects=false;try{old.require();}catch(IllegalStateException expected){rejects=true;}check(rejects,"pre-fix stale scope witness "+family.name());
                }else if(state.equals("fatal"))check(reached[0]&&escaped==fatal,"IME fatal swallowed "+family.name());
                else check(!returned&&escaped==null&&ConcreteHostProbe.count(nativeMethod,"entry")==before,"sealed/stale IME forwarded "+state+" / "+family.name());
            }collect();
        }
        for(String state:List.of("current","terminal","dirty","stale"))try(Fixture f=new Fixture("field")){
            f.ready();EditText editor=(EditText)f.renderer().view("field");editor.requestFocus();InputConnection connection=editor.onCreateInputConnection(new EditorInfo());
            if(state.equals("terminal"))f.owner.close();else if(state.equals("dirty"))f.owner.onPause();else if(state.equals("stale"))f.activity.getResources().configuration.uiMode=android.content.res.Configuration.UI_MODE_NIGHT_YES;
            int before=ConcreteHostProbe.events().size();
            check(!connection.replaceText(0,1,"x",1,null)&&!connection.performPrivateCommand("private",new Bundle())&&!connection.previewHandwritingGesture(null,null)&&!connection.commitCorrection(null)&&!connection.commitContent(null,0,null),"IME refusal override accepted "+state);
            int[] result={-1};connection.performHandwritingGesture(null,Runnable::run,value->result[0]=value);
            check(result[0]==InputConnection.HANDWRITING_GESTURE_RESULT_UNSUPPORTED,"handwriting refusal result");
            check(ConcreteHostProbe.events().subList(before,ConcreteHostProbe.events().size()).stream().noneMatch(event->event.method.startsWith("InputConnectionWrapper.")||event.method.startsWith("BaseInputConnection.")),"refusal forwarded native "+state);
        }
        try(Fixture f=new Fixture("field")){
            f.ready();EditText editor=(EditText)f.renderer().view("field");editor.requestFocus();InputConnection connection=editor.onCreateInputConnection(new EditorInfo());connection.closeConnection();
            check(((android.view.inputmethod.BaseInputConnection)editor.lastConnection).closed,"closeConnection delegate not reached");
            check(ConcreteHostProbe.events().stream().anyMatch(event->event.method.equals("BaseInputConnection.closeConnection")&&event.productionFrames.stream().anyMatch(frame->frame.methodName().equals("closeConnection")&&frame.descriptor().equals("()V")&&frame.bytecodeIndex()>=0)),"closeConnection product descriptor/BCI missing");
        }collect();
    }
    private static void actualObserverControls(){
        for(String phase:List.of("before-capture","after-capture","attach","commit-after-last-validation","refresh","input"))try(Fixture f=new Fixture()){
            if(phase.equals("refresh")||phase.equals("input"))f.ready();int prepared=NativeBridge.prepareCalls;boolean[] reached={false};NativeEnvironmentV2.Observer observer=(NativeEnvironmentV2.Observer)field(f.owner,"observer");
            ConcreteHostProbe.hook=(method,at)->{
                var event=ConcreteHostProbe.lastEvent();boolean point=switch(phase){
                    case "before-capture"->method.equals("NativeBridge.create")&&at.equals("beforeReturn");
                    case "after-capture","input"->method.equals("NativeBridge.prepareV2")&&at.equals("entry");
                    case "commit-after-last-validation"->method.equals("NativeBridge.commitV2")&&at.equals("entry");
                    default->method.equals("View.setEnabled")&&at.equals("beforeReturn")&&event.productionFrames.stream().anyMatch(frame->frame.className().equals("dev.mixer.android.NativeAppearanceViewsV2$Record")&&frame.methodName().equals("bind"));};
                if(!reached[0]&&point){reached[0]=true;ConcreteHostProbe.hook=null;observer.invalidate();assertGates(f,"actual observer invalidation");}
            };
            if(phase.equals("refresh"))f.owner.onPause();else if(phase.equals("input")){NativeBridge.preparedPacket=packet(2);f.renderer().view("button").performClick();}
            f.queue.drainAll(4);ConcreteHostProbe.hook=null;check(reached[0],"actual observer timing missed "+phase);
            boolean succeeds=phase.equals("before-capture")||phase.equals("commit-after-last-validation");
            check(f.owner.hasCommittedPresentation()==succeeds&&f.fence().terminal!=succeeds,"actual observer disposition "+phase);
            if(succeeds)check(NativeBridge.prepareCalls==1&&NativeBridge.commitCalls==1&&f.queue.postCalls==2,"actual observer dirty coalescing "+phase);
            if(phase.equals("refresh"))check(NativeBridge.prepareCalls==prepared&&NativeBridge.abortCalls==0,"actual observer refresh engine work");
            collect();
        }collect();
        try(Fixture f=new Fixture("field")){
            f.ready();EditText editor=(EditText)f.renderer().view("field");editor.requestFocus();InputConnection connection=editor.onCreateInputConnection(new EditorInfo());NativeBridge.preparedPacket=packet(2,"field","helloz");NativeBridge.commitStatus=1;
            check(!connection.commitText("z",1),"rejected edit returned authority");check(f.fence().terminal&&editor.getText().toString().equals("helloz"),"rejected native buffer was synthesized back");
        }collect();
        try(Fixture f=new Fixture()){
            f.ready();f.fence().sealSerial=Long.MAX_VALUE;f.owner.onPause();check(f.fence().terminal&&f.fence().sealSerial==Long.MAX_VALUE&&f.owner.cleanupLedger().cause()==NativeOwnerV2.Cause.SEAL_SERIAL_EXHAUSTED,"actual renderer serial exhaustion wrapped or invented failure");
        }collect();
    }
    private static void imeClose(){
        try(Fixture f=new Fixture("field")){
            f.ready();EditText editor=(EditText)f.renderer().view("field");editor.requestFocus();InputConnection connection=editor.onCreateInputConnection(new EditorInfo());connection.closeConnection();
            check(((android.view.inputmethod.BaseInputConnection)editor.lastConnection).closed,"closeConnection delegate not reached");
            check(ConcreteHostProbe.events().stream().anyMatch(event->event.method.equals("BaseInputConnection.closeConnection")&&event.productionFrames.stream().anyMatch(frame->frame.methodName().equals("closeConnection")&&frame.descriptor().equals("()V")&&frame.bytecodeIndex()>=0)),"closeConnection product descriptor/BCI missing");
        }collect();
    }
    private static void v1Baselines(){
        Activity activity=new Activity();List<byte[]> events=new ArrayList<>();NativeRenderer renderer=new NativeRenderer(activity,events::add);
        UiPacket first=UiPacket.decode(packet(1));View root=renderer.apply(first);check(root==renderer.view("root")&&renderer.packet==first,"V1 initial apply");
        ((android.view.ViewGroup)root).addView(new View(activity));View text=renderer.view("text");renderer.apply(UiPacket.decode(packet(2)));check(renderer.view("text")==text,"V1 exact generation reuse");
        renderer.view("button").performClick();check(events.size()==1&&Json.object(Json.parse(events.get(0))).get("revision")!=null,"V1 native button event");
        ((Switch)renderer.view("toggle")).performClick();check(events.size()==2,"V1 native toggle event");
        EditText editor=(EditText)renderer.view("field");editor.hostReplace(0,editor.getText().length(),"legacy");check(events.size()==3,"V1 native field event");
        renderer.apply(UiPacket.decode(packet(3,"replace")));check(renderer.view("replacement")!=root,"V1 hierarchy replacement");
        for(String method:List.of("ViewGroup.removeViewAt","ViewGroup.addView","MarginLayoutParams.setMarginEnd"))check(ConcreteHostProbe.events().stream().anyMatch(event->event.method.equals(method)&&event.phase.equals("entry")&&event.productionFrames.stream().anyMatch(frame->frame.className().equals("dev.mixer.android.NativeRenderer")&&frame.methodName().equals("children"))),"V1 explicit baseline not reached "+method);
        Set<Integer> layoutBci=new LinkedHashSet<>();for(var event:ConcreteHostProbe.events())if(event.method.equals("View.setLayoutParams")&&event.phase.equals("entry"))for(var frame:event.productionFrames)if(frame.className().equals("dev.mixer.android.NativeRenderer")&&frame.methodName().equals("children"))layoutBci.add(frame.bytecodeIndex());check(layoutBci.size()==2,"V1 two layout branches collapsed");collect();
    }
    private static void smoke(){
        try(Fixture f=new Fixture()){
            f.ready();check(NativeBridge.createCalls==1&&NativeBridge.prepareCalls==1&&NativeBridge.commitCalls==1,"initial exact engine calls");
            check(f.fence().operation==null&&f.fence().drawAllowed&&f.fence().inputAllowed,"publication after operation");
            f.root.draw(new Canvas());
            byte[] retained=(byte[])field(field(f.owner,"coordinator"),"committedPacket");
            f.owner.onPause();check(!f.fence().inputAllowed&&!f.fence().drawAllowed,"pause seals");f.queue.drainAll(4);
            check(field(field(f.owner,"coordinator"),"committedPacket")==retained,"refresh replaced retained array");
            check(NativeBridge.prepareCalls==1&&NativeBridge.commitCalls==1&&NativeBridge.abortCalls==0,"refresh engine work");
            f.owner.onResume();f.queue.drainAll(4);check(f.fence().inputAllowed,"resume/focus mapping");
        }
        check(NativeBridge.destroyCalls==1,"session exactly once");collect();
    }
    private static void runScenario(String selected){scenario=selected;switch(selected){case "smoke"->smoke();case "positive"->positiveCallbacks();case "hierarchy"->hierarchyControls();case "rollback"->rollbackControls();case "rollbackState"->rollbackStateControls();case "imeSuccessor"->imeSuccessor();case "imeControls"->imeControls();case "imeClose"->imeClose();default->throw new AssertionError(selected);}}
    private static void loadBarriers(Path path)throws Exception{
        var root=Json.object(Json.parse(Files.readAllBytes(path)));List<Barrier> selected=new ArrayList<>();
        for(Object value:Json.array(root.get("records"))){
            var record=Json.object(value);var candidate=Json.object(Json.array(record.get("candidates")).get(0));var boundary=Json.object(record.get("boundary"));
            selected.add(new Barrier(Json.string(record.get("baseline")),"dev.mixer.android."+Json.string(record.get("class")),Integer.parseInt(((Json.Num)candidate.get("line")).raw),
                Json.string(boundary.get("entry_native_suffix")),Json.string(boundary.get("return_native_suffix")),
                (String)boundary.get("return_receiver_id"),(String)boundary.get("return_receiver_class"),boundary.get("return_frame_line")==null?null:Integer.valueOf(((Json.Num)boundary.get("return_frame_line")).raw),
                Json.string(boundary.get("mode")),Json.string(boundary.get("equivalence"))));
        }
        barriers=List.copyOf(selected);
    }
    private static void runMatrix(Path output)throws Exception{
        List<Object> results=new ArrayList<>();List<String> missed=new ArrayList<>();Map<String,String> distinctSites=new LinkedHashMap<>();
        for(Barrier barrier:barriers){String witness=witnesses.get(barrier.id());if(witness==null){missed.add(barrier.id());continue;}
            for(String name:List.of("clean","terminal-at-entry","terminal-before-return","dirty-at-entry","dirty-before-return","ordinary-throw-after-callback","fatal-throw-after-callback")){
                matrix=new MatrixCase(barrier,name);ConcreteHostProbe.reset();ConcreteHostProbe.hook=matrix::hook;Throwable escaped=null;
                try{runScenario(witness);}catch(RuntimeException|Error failure){escaped=failure;}
                finally{ConcreteHostProbe.hook=null;}
                if(!matrix.fired)throw new AssertionError("matrix site missed "+barrier.id()+" / "+witness+" / "+name);
                check(matrix.validated,"selected callback invariant failed "+barrier.id()+" / "+name);
                if(name.startsWith("terminal")||name.endsWith("throw-after-callback")){
                    assertGates(matrix.fixture,"after selected callback stack");check(matrix.fixture.fence().terminal,"terminal stimulus did not retire fence");
                    check(NativeBridge.commitCalls==matrix.commits,"commit after selected terminal callback "+barrier.id()+" / "+name);
                }
                if(name.equals("fatal-throw-after-callback"))check(escaped==matrix.fatal||matrix.fixture.owner.cleanupLedger().firstFatal()==matrix.fatal,"fatal demoted "+barrier.id());
                if(escaped instanceof AssertionError failure&&!name.startsWith("clean")&&matrix.fired){
                    // The original positive scenario is expected to reject live publication after deliberate reentry.
                }else if(name.equals("clean")&&escaped!=null&&escaped!=matrix.done)throw new AssertionError("clean scenario failed "+barrier.id(),escaped);
                var selectedFrames=matrix.reached.productionFrames.stream().filter(frame->frame.line()==barrier.line()&&(frame.className().equals(barrier.className())||frame.className().startsWith(barrier.className()+"$"))).toList();
                check(selectedFrames.size()==1,"ambiguous runtime caller frame "+barrier.id()+" / "+selectedFrames);
                var exact=selectedFrames.get(0);String exactKey=exact.className()+"#"+exact.methodName()+exact.descriptor()+"@"+exact.bytecodeIndex();
                if(name.equals("clean")){String previous=distinctSites.putIfAbsent(exactKey,barrier.id());check(previous==null||previous.equals(barrier.id()),"two selected sites collapsed to one actual descriptor/BCI: "+previous+" / "+barrier.id());}
                List<Object> helperSequence=new ArrayList<>();
                if(name.equals("clean")&&(barrier.boundaryMode().contains("helper")||barrier.boundaryMode().contains("constructor"))){
                    ConcreteHostProbe.Event last=null;
                    for(var event:matrix.dynamic){
                        helperSequence.add(Json.map("nativeMethod",event.method,"phase",event.phase));last=event;
                    }
                    check(last!=null&&last.phase.equals("beforeReturn")&&barrier.matches(last),"helper final native return anchor is not final dynamic boundary "+barrier.id()+" / "+last);
                }
                results.add(Json.map("site",barrier.id(),"case",name,"stimulus",name.startsWith("dirty")?"actual owner onPause lifecycle invalidation":"selected concrete callback", "scenario",witness,"hit",true,"boundaryMode",barrier.boundaryMode(),"boundaryEquivalence",barrier.equivalence(),"nativeMethod",matrix.reached.method,"nativePhase",matrix.reached.phase,"exactCaller",exactKey,"helperNativeSequence",helperSequence,"helperSequenceEnd",matrix.traceEnd,"selectedFrames",matrix.reached.productionFrames.stream().filter(frame->frame.line()==barrier.line()&&(frame.className().equals(barrier.className())||frame.className().startsWith(barrier.className()+"$"))).map(frame->Json.map("class",frame.className(),"method",frame.methodName(),"descriptor",frame.descriptor(),"bytecodeIndex",new Json.Num(Integer.toString(frame.bytecodeIndex())),"line",new Json.Num(Integer.toString(frame.line())))).toList(),"escaped",escaped==null?null:escaped.getClass().getName()));
                matrix=null;collect();
            }
        }
        StringBuilder report=new StringBuilder();write(report,Json.map("scope","actual fourteen product subjects with explicit mechanical leaves; lifecycle dirty is separate from actual observer invalidation","baselineSites",new Json.Num("184"),"introducedSites",new Json.Num(Integer.toString(barriers.size()-184)),"missing",missed,"cases",results));Files.writeString(output,report);
        check(missed.isEmpty(),"missing actual baseline sites "+missed);
    }
    public static void main(String[] args)throws Exception{
        descriptor=Files.readAllBytes(Path.of(args[0]));if(args.length>2)loadBarriers(Path.of(args[2]));
        for(String selected:List.of("smoke","positive","hierarchy","rollback","rollbackState","imeSuccessor","imeClose"))runScenario(selected);
        scenario="imeControls";imeControls();scenario="v1";v1Baselines();scenario="cancellation";cancellationControls();scenario="rendererReports";rendererReportControls();scenario="actualObserver";actualObserverControls();scenario="reportTail";reportTailControls();scenario="pendingRosters";pendingRosterControls();scenario="fatalDeferred";concreteFatalAndDeferredControls();scenario="cancellationLedger";cancellationLedgerControls();scenario="focusAdmission";focusAdmissionControls();scenario="explicitScopes";explicitScopeControls();scenario="terminalContinuation";terminalContinuationControls();scenario="latePost";latePostControls();scenario="completionPublication";completionPublicationControls();collect();
        if(args.length>3)runMatrix(Path.of(args[3]));

        if(args.length>1){StringBuilder report=new StringBuilder();for(var e:sites.entrySet())report.append(e.getKey()).append('|').append(e.getValue()).append('\n');Files.writeString(Path.of(args[1]),report);}

        System.out.println("PASS concrete actual14 host checks="+checks+"; platform/JNI leaves, native runtime pending");
    }
}
