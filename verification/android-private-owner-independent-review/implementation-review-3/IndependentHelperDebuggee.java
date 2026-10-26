package dev.mixer.android;
import android.app.Activity;
import android.os.Handler;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;

/** Actual unmodified product debuggee for exactly the three selected helper calls. */
public final class IndependentHelperDebuggee {
    private IndependentHelperDebuggee(){}
    static NativeOwnerV2 owner;
    static final RuntimeException ordinary=new IllegalStateException("independent direct helper ordinary");
    static final Error fatal=new AssertionError("independent direct helper fatal");
    private static OwnerLifecycleV2 core;
    private static NativeOwnerV2.Fence fence;
    private static Handler handler;
    private static boolean afterCallback;
    private static int prepareAtCallback,commitAtCallback,assertions;
    private static final IndependentTraceEncoding trace=new IndependentTraceEncoding();
    private static void check(boolean value,String text){assertions++;if(!value)throw new AssertionError(text);}
    private static Object get(Object target,String name){try{Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(target);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static Object renderer(){Object held=get(owner,"opening");if(held==null)held=get(owner,"coordinator");return held==null?null:get(held,"renderer");}
    static void record(String point){
        if(point.equals("afterCallback")){afterCallback=true;prepareAtCallback=NativeBridge.prepareCalls;commitAtCallback=NativeBridge.commitCalls;check(!fence.drawAllowed&&!fence.inputAllowed,"direct actual callback closes shared flags");Object r=renderer();if(r!=null){Object gate=get(r,"v2Gate"),pending=get(r,"v2Pending");if(gate!=null)check(!(Boolean)get(gate,"open"),"direct actual callback closes current gate");if(pending!=null)check(!(Boolean)get(get(pending,"gate"),"open"),"direct actual callback closes pending gate");}}
        System.out.println("{\"point\":\""+point+"\",\"terminal\":"+fence.terminal+",\"draw\":"+fence.drawAllowed+",\"input\":"+fence.inputAllowed+",\"serial\":"+fence.sealSerial+",\"corePhase\":\""+core.snapshot().phase()+"\",\"coreDirty\":"+core.snapshot().dirty()+",\"queued\":"+handler.queued()+",\"prepareCalls\":"+NativeBridge.prepareCalls+",\"commitCalls\":"+NativeBridge.commitCalls+"}");
    }
    private static void run(String[] args)throws Exception{
        Path inputs=Path.of(args[0]);int site=Integer.parseInt(args[1]);String variant=args[2];
        ConcreteHostProbe.reset();NativeBridge.reset();Activity activity=new Activity();FrameLayout root=new FrameLayout(activity);root.layout(0,0,320,480);root.hostAttach(new Object());
        activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,Files.readAllBytes(inputs.resolve("independent-descriptor.json")));NativeBridge.preparedPacket=Files.readAllBytes(inputs.resolve("matrix-packet-base.json"));owner=new NativeOwnerV2(activity,root);core=(OwnerLifecycleV2)get(owner,"core");fence=(NativeOwnerV2.Fence)get(owner,"fence");handler=(Handler)get(owner,"handler");
        ConcreteHostProbe.hook=(method,phase)->{if(afterCallback){var frames=new ArrayList<String>();for(var frame:ConcreteHostProbe.lastEvent().productionFrames)frames.add(frame.className()+"#"+frame.methodName()+frame.descriptor()+"@"+frame.bytecodeIndex()+":"+frame.line());trace.add(method,phase,frames);}};
        Throwable escaped=null,cleanup=null;
        try{owner.start();owner.onResume();check(handler.drainOne(),"real initial handler work delivered");if(site==1){check(owner.hasCommittedPresentation()&&fence.operation==null,"live scroll starts with authentic clean presentation");((NativeRenderer)renderer()).view("list").scrollTo(0,10000);}}
        catch(RuntimeException|Error failure){escaped=failure;}
        finally{ConcreteHostProbe.hook=null;}
        if(variant.equals("clean"))check(escaped==null&&core.snapshot().phase()==OwnerLifecycleV2.Phase.LIVE&&!core.snapshot().dirty()&&fence.drawAllowed&&fence.inputAllowed,"clean authentic helper path completes");
        else {
            check(afterCallback&&!fence.drawAllowed&&!fence.inputAllowed,"callback was actual and authority remains sealed");
            if(variant.startsWith("terminal"))check(fence.terminal&&core.snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED,"terminal direct helper callback retires real owner");
            else if(variant.startsWith("dirty")){
                check(!fence.terminal&&core.snapshot().phase()==OwnerLifecycleV2.Phase.LIVE&&core.snapshot().dirty()&&handler.queued()==1,"direct lifecycle dirty keeps one later drain without terminal retirement");
                check(site==1?escaped instanceof IllegalStateException:escaped==null,"expired live scope refuses; unchanged transaction may finish");
            }
            if(variant.contains("throw")){
                check(variant.startsWith("fatal")?escaped==fatal:site==1?escaped==ordinary:owner.cleanupLedger().primary()==ordinary,"direct helper originating throwable identity and policy");
                check(site==1?!fence.terminal&&core.snapshot().dirty():fence.terminal,"outside-operation and joined-operation failure dispositions remain distinct");
            }
            if(variant.startsWith("terminal")||variant.contains("throw"))check(NativeBridge.prepareCalls==prepareAtCallback&&NativeBridge.commitCalls==commitAtCallback,"no new prepare or commit after terminal/fault callback");
        }
        record("afterOperation");String traceJson=trace.json();
        try{owner.close();}catch(RuntimeException|Error failure){cleanup=failure;}
        check(cleanup==null||cleanup==fatal,"cleanup preserves selected first fatal identity");check(fence.terminal&&NativeBridge.destroyCalls==1,"exclusive actual session independently closes once");
        System.out.println("{\"scope\":\"independent exact helper invoke/return witness\",\"site\":"+site+",\"variant\":\""+variant+"\",\"assertions\":"+assertions+",\"ordinaryIdentityEscaped\":"+(escaped==ordinary)+",\"fatalIdentityEscaped\":"+(escaped==fatal)+",\"orderedTrace\":"+traceJson+"}");ConcreteHostProbe.reset();NativeBridge.reset();
    }
    public static void main(String[] args)throws Exception{try{run(args);}finally{ConcreteHostProbe.hook=null;if(owner!=null)try{owner.close();}catch(RuntimeException|Error retained){System.err.println("retained final helper cleanup: "+retained.getClass().getName());}ConcreteHostProbe.reset();NativeBridge.reset();}}
}
