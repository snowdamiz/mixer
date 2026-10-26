package dev.mixer.android;

import android.app.Activity;
import android.graphics.Canvas;
import android.os.Handler;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.view.inputmethod.TextAttribute;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ScrollView;
import android.widget.Switch;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Independent actual-owner scenario discovery and site controls. No product overlays/models. */
public final class IndependentMatrixReview {
    private IndependentMatrixReview() {}
    private static int assertions;
    private static Fixture ownedFixture;
    private static void check(boolean value,String message){assertions++;if(!value)throw new AssertionError(message);}
    private static Object field(Object target,String name){
        try{Class<?> type=target.getClass();while(type!=null){try{Field f=type.getDeclaredField(name);f.setAccessible(true);return f.get(target);}catch(NoSuchFieldException absent){type=type.getSuperclass();}}throw new NoSuchFieldException(name);}
        catch(ReflectiveOperationException failure){throw new AssertionError(failure);}
    }
    private static void nativeFact(Object target,String name,int value){
        try{Field f=View.class.getDeclaredField(name);f.setAccessible(true);f.setInt(target,value);}
        catch(ReflectiveOperationException failure){throw new AssertionError(failure);}
    }
    private static Object invoke(Object target,String name,Class<?>[] types,Object...args){
        try{Class<?> type=target.getClass();Method found=null;while(type!=null){try{found=type.getDeclaredMethod(name,types);break;}catch(NoSuchMethodException absent){type=type.getSuperclass();}}if(found==null)throw new NoSuchMethodException(name);found.setAccessible(true);return found.invoke(target,args);}
        catch(InvocationTargetException failure){Throwable original=failure.getCause();if(original instanceof Error fatal)throw fatal;if(original instanceof RuntimeException ordinary)throw ordinary;throw new AssertionError(original);}
        catch(ReflectiveOperationException failure){throw new AssertionError(failure);}
    }
    private static String q(String value){return "\""+value.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n")+"\"";}
    private record Site(String id,String file,int line,int column,String callee,String kind,String classes,String methods,String select){}
    private record Reached(Site site,String phase,String leaf,ConcreteHostProbe.Site frame){}
    private static boolean matches(Site site,ConcreteHostProbe.Event event,ConcreteHostProbe.Site frame){
        String top=frame.className().substring(frame.className().lastIndexOf('.')+1).split("\\$",2)[0]+".java";
        if(!top.equals(site.file())||frame.line()!=site.line())return false;
        if(site.kind().equals("constructor"))return event.method.equals("View.<init>");
        if(site.kind().equals("helper-forward"))return frame.className().equals("dev.mixer.android.NativeAppearanceViewsV2$Group")&&frame.methodName().equals("onLayout")&&frame.descriptor().equals("(ZIIII)V");
        if(site.select().equals("group.onLayout"))return frame.className().equals("dev.mixer.android.NativeAppearanceViewsV2$NativeScroll")&&frame.methodName().equals("onScrollChanged");
        if(site.select().startsWith("super.")&&!site.callee().equals("closeConnection")&&(event.receiver==null||!event.receiver.getClass().getName().equals(frame.className())))return false;
        return event.method.substring(event.method.lastIndexOf('.')+1).equals(site.callee());
    }
    private static final class Fixture implements AutoCloseable {
        final Path inputs;
        final Activity activity=new Activity();
        final FrameLayout root=new FrameLayout(activity);
        final NativeOwnerV2 owner;
        final Handler handler;
        final NativeOwnerV2.Fence fence;
        final OwnerLifecycleV2 core;
        NativeCoordinatorV2 coordinator;
        NativeRenderer renderer;
        Fixture(Path inputs,String scenario)throws Exception {
            this.inputs=inputs;root.layout(0,0,320,480);root.hostAttach(new Object());
            activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,Files.readAllBytes(inputs.resolve("independent-descriptor.json")));
            NativeBridge.preparedPacket=packet(scenario.equals("initial-section")?"section":"base");owner=new NativeOwnerV2(activity,root);
            handler=(Handler)field(owner,"handler");fence=(NativeOwnerV2.Fence)field(owner,"fence");core=(OwnerLifecycleV2)field(owner,"core");
        }
        byte[] packet(String name)throws Exception{return Files.readAllBytes(inputs.resolve("matrix-packet-"+name+".json"));}
        void initialize(boolean expectedFailure){initialize(expectedFailure,true);}
        void initialize(boolean expectedFailure,boolean requirePublication){
            owner.start();owner.onResume();check(handler.drainOne(),"actual initial work exists");
            coordinator=(NativeCoordinatorV2)field(owner,"coordinator");
            if(coordinator!=null)renderer=(NativeRenderer)field(coordinator,"renderer");
            if(!requirePublication)return;
            if(!expectedFailure){
                if(!owner.hasCommittedPresentation()&&owner.cleanupLedger().primary()!=null)owner.cleanupLedger().primary().printStackTrace(System.out);
                check(owner.hasCommittedPresentation(),"independent rich packet must publish through actual owner");
                check(core.snapshot().phase()==OwnerLifecycleV2.Phase.LIVE&&!core.snapshot().dirty()&&fence.operation==null,"actual clean core publication");
            }else check(core.snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED,"controlled initial commit failure retires");
        }
        View view(String id){return renderer.view(id);}
        NativeAppearanceViewsV2.Record record(String id){return renderer.inspectV2().get(id);}
        EditText editor(){return (EditText)view("field");}
        Switch toggle(){return (Switch)view("toggle");}
        InputConnection connection(){EditText edit=editor();edit.requestFocus();edit.setSelection(0,edit.getText().length());InputConnection result=edit.onCreateInputConnection(new EditorInfo());check(result!=null,"actual native field connection");return result;}
        void gesture(boolean pause){
            Switch toggle=toggle();var geometry=(AuthoredToggleInputV2.Geometry)invoke(toggle,"authoredGeometry",new Class<?>[0]);check(geometry!=null,"actual authored geometry");
            float x=(float)geometry.offCenter(),y=geometry.trackY()+geometry.trackHeight()/2;
            check(toggle.onTouchEvent(MotionEvent.obtain(100,100,MotionEvent.ACTION_DOWN,x,y,0)),"actual toggle owns valid DOWN");
            check(toggle.onTouchEvent(MotionEvent.obtain(100,120,MotionEvent.ACTION_MOVE,x+20,y,0)),"actual toggle samples drag");
            if(pause)owner.onPause();else toggle.onTouchEvent(MotionEvent.obtain(100,140,MotionEvent.ACTION_CANCEL,x+20,y,0));
        }
        @Override public void close(){owner.close();}
    }
    private record Target(String id,String scenario,String leaf,String owner,String method,String descriptor,int bci){}
    private static final class OrdinaryMarker extends RuntimeException {private static final long serialVersionUID=1L;OrdinaryMarker(){super("independent per-site ordinary marker");}}
    private static final class FatalMarker extends Error {private static final long serialVersionUID=1L;FatalMarker(){super("independent per-site fatal marker");}}
    private static String state(Fixture fixture){
        Object active=field(fixture.owner,"opening");if(active==null)active=field(fixture.owner,"coordinator");
        Object renderer=active==null?null:field(active,"renderer");
        Object current=renderer==null?null:field(renderer,"v2Gate"),pending=renderer==null?null:field(renderer,"v2Pending");
        Object candidateGate=pending==null?null:field(pending,"gate");
        return "{\"terminal\":"+fixture.fence.terminal+",\"draw\":"+fixture.fence.drawAllowed+",\"input\":"+fixture.fence.inputAllowed+",\"commitFinish\":"+fixture.fence.commitFinish+",\"serial\":"+fixture.fence.sealSerial+",\"operationPresent\":"+(fixture.fence.operation!=null)+",\"currentGate\":"+(current==null?"null":field(current,"open"))+",\"pendingGate\":"+(candidateGate==null?"null":field(candidateGate,"open"))+",\"corePhase\":"+q(fixture.core.snapshot().phase().name())+",\"coreDirty\":"+fixture.core.snapshot().dirty()+"}";
    }
    private static void checkSealed(Fixture fixture){
        check(!fixture.fence.drawAllowed&&!fixture.fence.inputAllowed,"callback scalar authority remains closed");
        Object active=field(fixture.owner,"opening");if(active==null)active=field(fixture.owner,"coordinator");
        Object renderer=active==null?null:field(active,"renderer");
        if(renderer!=null){Object current=field(renderer,"v2Gate"),pending=field(renderer,"v2Pending");
            if(current!=null)check(!(Boolean)field(current,"open"),"actual current renderer gate remains closed");
            if(pending!=null)check(!(Boolean)field(field(pending,"gate"),"open"),"actual pending renderer gate remains closed");
        }
    }
    private static void row(Path inputs,Target target,String variant)throws Exception {
        ConcreteHostProbe.reset();NativeBridge.reset();assertions=0;Fixture fixture=new Fixture(inputs,target.scenario());ownedFixture=fixture;
        boolean[] reached={false},injecting={false},after={false};String[] before={"null"},sealed={"null"};
        int[] callCounts={-1,-1};IndependentTraceEncoding trace=new IndependentTraceEncoding();
        OrdinaryMarker ordinary=new OrdinaryMarker();FatalMarker fatal=new FatalMarker();Throwable escaped=null,cleanupEscaped=null;
        String phase=variant.equals("terminal-before-return")||variant.equals("dirty-before-return")?"beforeReturn":"entry";
        var hook=(java.util.function.BiConsumer<String,String>)(method,position)->{
            if(injecting[0])return;
            var event=ConcreteHostProbe.lastEvent();
            if(after[0]){
                List<String> frames=new ArrayList<>();for(var frame:event.productionFrames)frames.add(frame.className()+"#"+frame.methodName()+frame.descriptor()+"@"+frame.bytecodeIndex()+":"+frame.line());
                trace.add(method,position,frames);
            }
            if(reached[0]||!method.equals(target.leaf())||!position.equals(phase))return;
            boolean exact=false;for(var frame:event.productionFrames)if(frame.className().equals(target.owner())&&frame.methodName().equals(target.method())&&frame.descriptor().equals(target.descriptor())&&frame.bytecodeIndex()==target.bci()){exact=true;break;}
            if(!exact)return;reached[0]=true;before[0]=state(fixture);
            if(variant.equals("clean"))return;
            injecting[0]=true;
            try{if(variant.startsWith("terminal"))fixture.owner.close();else fixture.owner.onPause();}
            finally{injecting[0]=false;sealed[0]=state(fixture);checkSealed(fixture);callCounts[0]=NativeBridge.prepareCalls;callCounts[1]=NativeBridge.commitCalls;after[0]=true;}
            if(variant.equals("ordinary-throw-after-callback"))throw ordinary;
            if(variant.equals("fatal-throw-after-callback"))throw fatal;
        };
        boolean initial=target.scenario().equals("initial")||target.scenario().startsWith("initial-");
        try {
            if(initial)ConcreteHostProbe.hook=hook;
            if(target.scenario().equals("initial-commit-failure"))NativeBridge.commitFailure=new IllegalStateException("independent initial commit boundary failure");
            fixture.initialize(target.scenario().equals("initial-commit-failure"),!initial||variant.equals("clean"));
            if(!initial){ConcreteHostProbe.reset();ConcreteHostProbe.hook=hook;action(fixture,target.scenario());}
        }catch(RuntimeException|Error failure){escaped=failure;}
        finally{ConcreteHostProbe.hook=null;}
        check(reached[0],"exact selected class/descriptor/BCI/leaf/phase must be reached: "+target.id()+"/"+variant);
        String afterState=state(fixture);
        if(!variant.equals("clean")){
            checkSealed(fixture);
            if(variant.startsWith("terminal"))check(fixture.fence.terminal&&fixture.core.snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED,"terminal callback reaches actual retired core");
            if(variant.startsWith("terminal")||variant.contains("throw")){
                check(NativeBridge.prepareCalls==callCounts[0],"no new prepare after terminal/fault boundary");
                check(NativeBridge.commitCalls==callCounts[1],"no new commit after terminal/fault boundary");
            }
            if(variant.equals("fatal-throw-after-callback"))check(escaped==fatal,"actual first fatal identity retained or escaped");
        }else check(escaped==null,"clean exact-site scenario returns without failure");
        int prepares=NativeBridge.prepareCalls,commits=NativeBridge.commitCalls;
        try{fixture.close();}catch(RuntimeException|Error failure){cleanupEscaped=failure;}
        if(variant.equals("fatal-throw-after-callback")&&cleanupEscaped!=null)check(cleanupEscaped==fatal,"cleanup preserves first fatal identity");
        check(fixture.fence.terminal&&!fixture.fence.drawAllowed&&!fixture.fence.inputAllowed,"owned row fixture closes sealed");
        check(NativeBridge.destroyCalls<=1,"owned session destroy attempted at most once");
        System.out.println("{\"scope\":\"independent seven-case actual callback control; tail source classification separate\",\"id\":"+q(target.id())+",\"variant\":"+q(variant)+",\"scenario\":"+q(target.scenario())+",\"leaf\":"+q(target.leaf())+",\"class\":"+q(target.owner())+",\"method\":"+q(target.method())+",\"descriptor\":"+q(target.descriptor())+",\"bci\":"+target.bci()+",\"phase\":"+q(phase)+",\"assertions\":"+assertions+",\"before\":"+before[0]+",\"afterCallback\":"+sealed[0]+",\"afterOperation\":"+afterState+",\"prepareCalls\":"+prepares+",\"commitCalls\":"+commits+",\"escaped\":"+(escaped==null?"null":q(escaped.getClass().getName()))+",\"ordinaryIdentityEscaped\":"+(escaped==ordinary)+",\"fatalIdentityEscaped\":"+(escaped==fatal)+",\"orderedTrace\":"+trace.json()+"}");
        ConcreteHostProbe.reset();NativeBridge.reset();
    }
    private static void action(Fixture f,String scenario)throws Exception {
        if(scenario.equals("initial"))return;
        if(scenario.equals("draw")){((NativeAppearanceViewsV2.Gate)field(f.renderer,"v2Gate")).draw(new Canvas());return;}
        if(scenario.equals("scroll")){var nav=f.record("navigation");System.out.println("{\"scrollDiagnostic\":true,\"overflow\":"+nav.geometry.overflow+",\"collapsed\":"+nav.geometry.collapsed+",\"inputOpen\":"+f.record("list").input.open(f.record("list"))+",\"oldScroll\":"+f.view("list").getScrollY()+"}");f.view("list").scrollTo(0,10000);return;}
        if(scenario.equals("gate-touch")){((View)field(f.renderer,"v2Gate")).dispatchTouchEvent(MotionEvent.obtain(100,100,MotionEvent.ACTION_CANCEL,0,0,0));return;}
        if(scenario.equals("gate-key")){((View)field(f.renderer,"v2Gate")).dispatchKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN,21,0));return;}
        if(scenario.equals("draw-focused")){f.editor().requestFocus();((View)field(f.renderer,"v2Gate")).draw(new Canvas());return;}
        if(scenario.equals("draw-cursor")){f.editor().cursorDrawable.draw(new Canvas());return;}
        if(scenario.equals("draw-handle")){f.editor().selectHandle.draw(new Canvas());return;}
        if(scenario.startsWith("hierarchy-")){
            android.view.ViewGroup gate=(android.view.ViewGroup)field(f.renderer,"v2Gate");
            if(scenario.equals("hierarchy-desired")){View desired=f.view("navigation");FrameLayout foreign=new FrameLayout(f.activity);gate.addView(foreign);gate.removeView(desired);foreign.addView(desired);}
            if(scenario.equals("hierarchy-gate-extra"))gate.addView(new View(f.activity));
            if(scenario.equals("hierarchy-gate-parent")){FrameLayout foreign=new FrameLayout(f.activity);f.root.addView(foreign);f.root.removeView(gate);foreign.addView(gate);}
            if(scenario.equals("hierarchy-root-extra"))f.root.addView(new View(f.activity));
            if(scenario.equals("hierarchy-group-extra"))f.record("section").group.addView(new View(f.activity));
            NativeBridge.preparedPacket=f.packet("echo");f.view("button").performClick();return;
        }
        if(scenario.equals("gesture")){f.gesture(false);return;}
        if(scenario.equals("gesture-pause")){f.gesture(true);return;}
        if(scenario.equals("close")){f.owner.close();return;}
        if(scenario.startsWith("rollback")){
            f.editor().clearFocus();f.view("button").requestFocus();NativeBridge.preparedPacket=f.packet(scenario.equals("rollback-reorder")?"reorder":"changed");NativeBridge.commitStatus=1;
            var prior=ConcreteHostProbe.hook;
            ConcreteHostProbe.hook=(method,phase)->{
                if(method.equals("NativeBridge.commitV2")&&phase.equals("entry")){
                    if(scenario.equals("rollback-focus"))f.view("button").clearFocus();
                    if(scenario.equals("rollback-scroll"))nativeFact(f.view("list"),"scrollY",30);
                    if(scenario.equals("rollback-extra"))f.record("section").group.addView(new View(f.activity));
                }
                if(prior!=null)prior.accept(method,phase);
            };
            f.view("button").performClick();return;
        }
        if(scenario.startsWith("toggle-")){
            Switch toggle=f.toggle();NativeBridge.preparedPacket=f.packet("toggle");
            switch(scenario){
                case "toggle-click"->toggle.performClick();
                case "toggle-key"->toggle.dispatchKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN,21,0));
                case "toggle-accessibility"->toggle.performAccessibilityAction(0,null);
                case "toggle-enabled"->toggle.setEnabled(true);
                case "toggle-frame"->toggle.layout(toggle.getLeft(),toggle.getTop(),toggle.getRight(),toggle.getBottom());
                case "toggle-focus"->toggle.requestFocus();
                case "toggle-window-focus"->toggle.onWindowFocusChanged(true);
                case "toggle-visible"->toggle.setVisibility(View.VISIBLE);
                case "toggle-window-visible"->invoke(toggle,"onWindowVisibilityChanged",new Class<?>[]{int.class},View.VISIBLE);
                case "toggle-rtl"->toggle.onRtlPropertiesChanged(View.LAYOUT_DIRECTION_LTR);
                case "toggle-attach"->invoke(toggle,"onAttachedToWindow",new Class<?>[0]);
                case "toggle-detach"->invoke(toggle,"onDetachedFromWindow",new Class<?>[0]);
                case "toggle-state"->invoke(toggle,"drawableStateChanged",new Class<?>[0]);
                case "toggle-restore"->((AuthoredToggleInputV2.CheckedBinding)toggle).restoreChecked(false);
                default->throw new IllegalArgumentException(scenario);
            }return;
        }
        if(scenario.startsWith("field-")){
            EditText editor=f.editor();editor.requestFocus();
            switch(scenario){
                case "field-state"->invoke(editor,"drawableStateChanged",new Class<?>[0]);
                case "field-selection"->editor.setSelection(0,editor.getText().length());
                case "field-key"->editor.onKeyDown(21,new KeyEvent(KeyEvent.ACTION_DOWN,21,0));
                case "field-accessibility"->editor.performAccessibilityAction(0,null);
                case "field-context"->editor.onTextContextMenuItem(0);
                case "field-connection"->f.connection();
                default->throw new IllegalArgumentException(scenario);
            }return;
        }
        if(scenario.startsWith("ime-")){
            InputConnection connection=f.connection();NativeBridge.preparedPacket=f.packet(scenario.startsWith("ime-delete")?"empty":"echo");
            switch(scenario){
                case "ime-commit"->connection.commitText("alpha",1);
                case "ime-compose"->connection.setComposingText("alpha",1);
                case "ime-commit-attributes"->connection.commitText("alpha",1,new TextAttribute());
                case "ime-compose-attributes"->connection.setComposingText("alpha",1,new TextAttribute());
                case "ime-region"->connection.setComposingRegion(0,1);
                case "ime-region-attributes"->connection.setComposingRegion(0,1,new TextAttribute());
                case "ime-finish"->connection.finishComposingText();
                case "ime-delete"->connection.deleteSurroundingText(0,0);
                case "ime-delete-codepoints"->connection.deleteSurroundingTextInCodePoints(0,0);
                case "ime-selection"->connection.setSelection(0,1);
                case "ime-editor"->connection.performEditorAction(EditorInfo.IME_ACTION_DONE);
                case "ime-key"->connection.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN,21,0));
                case "ime-consumes"->connection.setImeConsumesInput(true);
                case "ime-completion"->connection.commitCompletion(new android.view.inputmethod.CompletionInfo(1,0,"alpha"));
                case "ime-begin"->connection.beginBatchEdit();
                case "ime-end"->connection.endBatchEdit();
                case "ime-clear"->connection.clearMetaKeyStates(0);
                case "ime-close"->connection.closeConnection();
                default->throw new IllegalArgumentException(scenario);
            }return;
        }
        throw new IllegalArgumentException(scenario);
    }
    public static void main(String[] args)throws Exception {
        Path inputs=Path.of(args[0]);String mode=args[1],scenario=args[2];
        if(mode.equals("matrix")){
            String[] columns=Files.readAllLines(inputs.resolve("matrix-targets.tsv")).get(Integer.parseInt(scenario)).split("\t",-1);
            Target target=new Target(columns[0],columns[1],columns[2],columns[3],columns[4],columns[5],Integer.parseInt(columns[6]));
            String[] variants=args[3].equals("all")?new String[]{"clean","terminal-at-entry","terminal-before-return","dirty-at-entry","dirty-before-return","ordinary-throw-after-callback","fatal-throw-after-callback"}:new String[]{args[3]};
            int failures=0;
            for(String variant:variants){
                try{row(inputs,target,variant);}
                catch(RuntimeException|Error failure){failures++;System.err.println("independent failed row "+target.id()+"/"+variant);failure.printStackTrace(System.err);}
                finally{ConcreteHostProbe.hook=null;try{if(ownedFixture!=null)ownedFixture.close();}catch(RuntimeException|Error cleanup){System.err.println("retained final cleanup disposition: "+cleanup.getClass().getName());}finally{ownedFixture=null;ConcreteHostProbe.reset();NativeBridge.reset();}}
            }
            if(failures!=0)throw new AssertionError("independent failed rows: "+failures);
            return;
        }
        check(mode.equals("discover"),"explicit discovery mode");
        List<Site> sites=new ArrayList<>();for(String line:Files.readAllLines(inputs.resolve("matrix-sites.tsv"))){String[] c=line.split("\t",-1);sites.add(new Site(c[0],c[1],Integer.parseInt(c[2]),Integer.parseInt(c[3]),c[4],c[5],c[6],c[7],c[8]));}
        check(sites.size()==189,"exact selected source inventory input");ConcreteHostProbe.reset();NativeBridge.reset();
        Map<String,List<Site>> byLine=new LinkedHashMap<>();for(Site site:sites)byLine.computeIfAbsent(site.file()+":"+site.line(),ignored->new ArrayList<>()).add(site);
        Map<String,Reached> reached=new LinkedHashMap<>();
        try(Fixture fixture=new Fixture(inputs,scenario)){
            var observe=(java.util.function.BiConsumer<String,String>)(method,phase)->{
                var event=ConcreteHostProbe.lastEvent();
                for(var frame:event.productionFrames){String name=frame.className().substring(frame.className().lastIndexOf('.')+1);int nested=name.indexOf('$');if(nested>=0)name=name.substring(0,nested);
                    List<Site> candidates=byLine.get(name+".java:"+frame.line());if(candidates==null)continue;
                    for(Site site:candidates)if(matches(site,event,frame))reached.putIfAbsent(site.id()+"/"+phase,new Reached(site,phase,method,frame));
                }
            };
            boolean initial=scenario.equals("initial")||scenario.startsWith("initial-");
            if(initial)ConcreteHostProbe.hook=observe;
            if(scenario.equals("initial-commit-failure"))NativeBridge.commitFailure=new IllegalStateException("independent initial commit boundary failure");
            fixture.initialize(scenario.equals("initial-commit-failure"));
            if(!initial){ConcreteHostProbe.reset();ConcreteHostProbe.hook=observe;action(fixture,scenario);}
            ConcreteHostProbe.hook=null;
            if(scenario.startsWith("rollback")||scenario.equals("initial-commit-failure")||scenario.equals("close"))check(fixture.core.snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED,"controlled disposition scenario retires real owner");
            else check(!fixture.fence.terminal,"clean discovery scenario cannot unexpectedly retire");
            StringBuilder rows=new StringBuilder("[");
            for(Reached reach:reached.values()){
                if(rows.length()>1)rows.append(',');var frame=reach.frame();
                rows.append("{\"id\":").append(q(reach.site().id())).append(",\"phase\":").append(q(reach.phase())).append(",\"leaf\":").append(q(reach.leaf()))
                    .append(",\"class\":").append(q(frame.className())).append(",\"method\":").append(q(frame.methodName())).append(",\"descriptor\":").append(q(frame.descriptor()))
                    .append(",\"bci\":").append(frame.bytecodeIndex()).append(",\"line\":").append(frame.line()).append('}');
            }
            System.out.println("{\"scope\":\"independent actual-owner scenario discovery; not seven-case qualification\",\"scenario\":"+q(scenario)+",\"assertions\":"+assertions+",\"actualPrepareCalls\":"+NativeBridge.prepareCalls+",\"actualCommitCalls\":"+NativeBridge.commitCalls+",\"reached\":"+rows.append(']')+"}");
        }finally{ConcreteHostProbe.hook=null;ConcreteHostProbe.reset();NativeBridge.reset();}
    }
}
