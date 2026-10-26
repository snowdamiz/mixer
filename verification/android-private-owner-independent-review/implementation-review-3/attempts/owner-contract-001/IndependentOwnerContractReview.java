package dev.mixer.android;
import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import android.view.Window;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/** Independent contract cases against actual owner/core/Observer; no producer harness or model. */
public final class IndependentOwnerContractReview {
    private IndependentOwnerContractReview(){}
    private static int assertions,cases;
    private static final String[] ADDS={"Context.registerComponentCallbacks","View.addOnLayoutChangeListener","View.addOnAttachStateChangeListener","ViewTreeObserver.addOnWindowFocusChangeListener","View.setOnApplyWindowInsetsListener","UiModeManager.addContrastChangeListener","AccessibilityManager.addHighContrastTextStateChangeListener","ContentResolver.registerContentObserver"};
    private static final String[] REMOVES={"Context.unregisterComponentCallbacks","View.removeOnLayoutChangeListener","View.removeOnAttachStateChangeListener","ViewTreeObserver.removeOnWindowFocusChangeListener","View.setOnApplyWindowInsetsListener","UiModeManager.removeContrastChangeListener","AccessibilityManager.removeHighContrastTextStateChangeListener","ContentResolver.unregisterContentObserver"};
    private static void check(boolean value,String message){assertions++;if(!value)throw new AssertionError(message);}
    private static Object get(Object target,String name){try{Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(target);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static void counter(Object target,String name,long value){try{Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);f.setLong(target,value);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static Throwable call(Runnable action){try{action.run();return null;}catch(RuntimeException|Error failure){return failure;}}
    private static final class Ordinary extends RuntimeException{private static final long serialVersionUID=1L;Ordinary(){super("independent owner contract ordinary");}}
    private static final class Fatal extends Error{private static final long serialVersionUID=1L;Fatal(){super("independent owner contract fatal");}}
    private static final class Fixture implements AutoCloseable {
        final Activity activity=new Activity();final FrameLayout root=new FrameLayout(activity);
        final NativeOwnerV2 owner;final OwnerLifecycleV2 core;final NativeOwnerV2.Fence fence;final Handler handler;
        Fixture(Path inputs,boolean attached)throws Exception{
            ConcreteHostProbe.reset();NativeBridge.reset();root.layout(0,0,320,480);if(attached)root.hostAttach(new Object());
            activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,Files.readAllBytes(inputs.resolve("independent-descriptor.json")));NativeBridge.preparedPacket=Files.readAllBytes(inputs.resolve("matrix-packet-base.json"));
            owner=new NativeOwnerV2(activity,root);core=(OwnerLifecycleV2)get(owner,"core");fence=(NativeOwnerV2.Fence)get(owner,"fence");handler=(Handler)get(owner,"handler");
        }
        NativeEnvironmentV2.Observer observer(){return (NativeEnvironmentV2.Observer)get(owner,"observer");}
        void live(){owner.start();owner.onResume();check(handler.drainOne(),"actual owner queued initial drain");check(owner.hasCommittedPresentation()&&core.snapshot().phase()==OwnerLifecycleV2.Phase.LIVE&&!core.snapshot().dirty(),"actual initial clean publication");}
        @Override public void close(){ConcreteHostProbe.hook=null;Throwable failure=call(owner::close);if(failure!=null)check(failure==owner.cleanupLedger().firstFatal(),"final repeated close retains first fatal");ConcreteHostProbe.reset();NativeBridge.reset();}
    }
    private static void registration(Path inputs)throws Exception {
        for(int slot=0;slot<8;slot++)for(String phase:new String[]{"entry","beforeReturn"})for(boolean fatal:new boolean[]{false,true}){
            try(Fixture f=new Fixture(inputs,false)){
                int selected=slot;Ordinary ordinary=new Ordinary();Fatal marker=new Fatal();boolean[] fired={false};
                ConcreteHostProbe.hook=(method,position)->{if(!fired[0]&&method.equals(ADDS[selected])&&position.equals(phase)){fired[0]=true;if(fatal)throw marker;throw ordinary;}};
                Throwable escaped=call(f.owner::start);ConcreteHostProbe.hook=null;
                check(fired[0],"exact observer acquisition boundary reached");check(f.core.snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED,"actual owner retires registration failure");
                check(!f.fence.drawAllowed&&!f.fence.inputAllowed&&NativeBridge.createCalls==0,"registration cannot acquire engine after failure");
                check(fatal?escaped==marker:escaped==null,"registration originating owner fatal policy");
                var ledger=f.observer().cleanupLedger();for(int i=0;i<8;i++)check(ledger.state(i)==(i<=slot?NativeEnvironmentV2.Observer.RETURNED:NativeEnvironmentV2.Observer.UNATTEMPTED),"exact possibly-owned acquisition prefix unwinds independently");
                check(ledger.primary()==(fatal?marker:ordinary),"observer first primary identity");
                for(int i=slot+1;i<8;i++)check(ConcreteHostProbe.count(ADDS[i],"entry")==0,"no later listener acquisition");cases++;
            }
        }
    }
    private static void registrationReentry(Path inputs)throws Exception{
        for(int slot=0;slot<8;slot++)for(String phase:new String[]{"entry","beforeReturn"})try(Fixture f=new Fixture(inputs,false)){
            int selected=slot;boolean[] fired={false};ConcreteHostProbe.hook=(method,position)->{if(!fired[0]&&method.equals(ADDS[selected])&&position.equals(phase)){fired[0]=true;f.owner.close();check(f.owner.cleanupLedger().unregister()==NativeOwnerV2.Outcome.DEFERRED,"owner unregister remains deferred inside actual add");check(f.observer().cleanupLedger().state(selected)==NativeEnvironmentV2.Observer.POSSIBLY_OWNED,"acquiring native slot not falsely returned");}};
            f.owner.start();ConcreteHostProbe.hook=null;check(fired[0],"exact add reentry reached");check(f.core.snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED&&NativeBridge.createCalls==0,"terminal add reentry never opens owner");
            for(int i=0;i<8;i++)check(f.observer().cleanupLedger().state(i)==(i<=slot?NativeEnvironmentV2.Observer.RETURNED:NativeEnvironmentV2.Observer.UNATTEMPTED),"reentry add unwind exact slots");cases++;
        }
    }
    private static void removal(Path inputs)throws Exception{
        for(int slot=0;slot<8;slot++)for(String phase:new String[]{"entry","beforeReturn"})for(boolean fatal:new boolean[]{false,true})try(Fixture f=new Fixture(inputs,false)){
            f.owner.start();ConcreteHostProbe.reset();int selected=slot;Ordinary ordinary=new Ordinary();Fatal marker=new Fatal();boolean[] fired={false};
            ConcreteHostProbe.hook=(method,position)->{if(!fired[0]&&method.equals(REMOVES[selected])&&position.equals(phase)){fired[0]=true;check(f.fence.terminal&&!f.fence.drawAllowed&&!f.fence.inputAllowed,"removal callback sees scalar terminal barrier");if(fatal)throw marker;throw ordinary;}};
            Throwable escaped=call(f.owner::close);ConcreteHostProbe.hook=null;check(fired[0],"exact native removal boundary reached");check(fatal?escaped==marker:escaped==null,"first fatal removal escapes after independent attempts");
            var ledger=f.observer().cleanupLedger();for(int i=0;i<8;i++){check(ConcreteHostProbe.count(REMOVES[i],"entry")==1,"every independent remove attempted once");check(ledger.state(i)==(i==slot?NativeEnvironmentV2.Observer.FAILED_UNCERTAIN:NativeEnvironmentV2.Observer.RETURNED),"truthful eight-slot returned versus uncertain ledger");}
            check(ledger.primary()==(fatal?marker:ordinary),"observer retains exact removal primary");if(fatal)check(ledger.firstFatal()==marker,"observer retains exact first fatal");
            int before=ConcreteHostProbe.events().size();call(f.owner::close);check(ConcreteHostProbe.events().size()==before,"consumed observer slots do not retry");cases++;
        }
    }
    private static void readiness(Path inputs)throws Exception{
        for(int kind=0;kind<6;kind++)try(Fixture f=new Fixture(inputs,true)){
            Window window=f.activity.window;Object token=f.root.windowToken;var insets=f.root.rootInsets;
            switch(kind){case 0->f.root.attached=false;case 1->f.activity.window=null;case 2->f.root.windowToken=null;case 3->f.root.layout(0,0,0,480);case 4->f.root.layout(0,0,320,0);case 5->f.root.rootInsets=null;default->throw new AssertionError();}
            f.owner.start();f.owner.onResume();check(NativeBridge.createCalls==0&&f.handler.queued()==0,"not-ready actual root never creates or polls");
            f.root.attached=true;f.root.windowToken=token;f.root.rootInsets=insets;f.activity.window=window;f.root.layout(0,0,320,480);f.observer().invalidate();
            check(f.handler.queued()==1,"actual ready notification leaves one work identity");check(f.handler.drainOne(),"actual ready work delivered");check(f.owner.hasCommittedPresentation()&&NativeBridge.createCalls==1,"fresh ready delivery publishes actual session");cases++;
        }
        try(Fixture f=new Fixture(inputs,false)){f.owner.start();f.root.treeObserver.alive=false;ConcreteHostProbe.reset();f.owner.close();check(f.observer().cleanupLedger().state(3)==NativeEnvironmentV2.Observer.DEAD_TARGET_UNCERTAIN,"dead original focus target is uncertain");check(ConcreteHostProbe.count(REMOVES[3],"entry")==0,"dead focus target removal is not fabricated");for(int i=0;i<8;i++)if(i!=3)check(ConcreteHostProbe.count(REMOVES[i],"entry")==1,"dead focus target does not skip later removes");cases++;}
    }
    private static void mainAndExhaustion(Path inputs)throws Exception{
        try(Fixture f=new Fixture(inputs,true)){
            f.live();var owned=(NativeCoordinatorV2)get(f.owner,"coordinator");var renderer=(NativeRenderer)get(owned,"renderer");var observer=f.observer();f.owner.close();ConcreteHostProbe.reset();
            List<Runnable> entries=List.of(f.owner::onResume,f.owner::onPause,f.owner::onStop,f.owner::close,()->f.owner.hasCommittedPresentation(),()->f.owner.cleanupLedger(),observer::register,observer::invalidate,observer::close,observer::ready,observer::capture,observer::onLowMemory,()->observer.bindRenderer(renderer),renderer::retireV2,renderer::inspectV2,renderer::cleanupLedger,renderer::testRetiredV2,owned::renderInitial,owned::refreshEnvironment,()->owned.dispatchInput(null),owned::closeFromOwner,owned::cleanupLedger,owned::isRetired,owned::hasCommittedPresentation,owned::busyForOwnerDisposal,owned::inputCancellationInProgress,()->owned.cancelInputFromOwner(1),()->f.core.snapshot(),()->f.core.lifetime());
            Looper.hostSetMain(false);try{for(Runnable entry:entries)check(call(entry) instanceof IllegalStateException,"actual main Looper check precedes retired/stale return");}finally{Looper.hostReset();}
            check(ConcreteHostProbe.events().isEmpty(),"off-main entries perform no native leaf work");cases++;
        }
        try(Fixture f=new Fixture(inputs,true)){f.live();counter(f.fence,"sealSerial",Long.MAX_VALUE);f.owner.onPause();check(f.fence.sealSerial==Long.MAX_VALUE&&f.fence.terminal,"seal serial exhausts without wrap");check(f.owner.cleanupLedger().cause()==NativeOwnerV2.Cause.SEAL_SERIAL_EXHAUSTED&&f.core.snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED,"actual core retires exact serial cause");check(NativeBridge.destroyCalls==1,"serial exhaustion independently disposes engine");cases++;}
        try(Fixture f=new Fixture(inputs,true)){f.live();NativeCoordinatorV2 coordinator=(NativeCoordinatorV2)get(f.owner,"coordinator");NativeRenderer renderer=(NativeRenderer)get(coordinator,"renderer");renderer.testExhaustInteractionV2();int prepares=NativeBridge.prepareCalls;renderer.view("button").performClick();check(f.fence.terminal&&f.core.snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED,"actual interaction exhaustion retires owner");check(f.owner.cleanupLedger().rendererCause()==NativeEnvironmentV2.RendererCause.INTERACTION_EXHAUSTED&&NativeBridge.prepareCalls==prepares,"exact typed report precedes feature input");cases++;}
    }
    private static final class Core {
        final Object activity=new Object(),root=new Object(),window=new Object(),resource=new Object();
        final OwnerLifecycleV2 actual;final OwnerLifecycleV2.Token lifetime;
        Core(){this(0);}Core(long epoch){actual=new OwnerLifecycleV2(NativeOwnerV2::requireMain,activity,root,epoch);lifetime=actual.lifetime();}
        OwnerLifecycleV2.WindowFacts facts(){return new OwnerLifecycleV2.WindowFacts(activity,root,false,true,window,320,480,true);}
        List<OwnerLifecycleV2.Decision> bounded(List<OwnerLifecycleV2.Decision> result){check(result.size()<=OwnerLifecycleV2.MAX_DECISIONS,"real core decisions bounded");return result;}
        OwnerLifecycleV2.Decision one(List<OwnerLifecycleV2.Decision> result,OwnerLifecycleV2.Kind kind){bounded(result);return result.stream().filter(d->d.kind()==kind).findFirst().orElseThrow(()->new AssertionError("missing real decision "+kind));}
        OwnerLifecycleV2.Decision opening(){one(actual.windowChanged(lifetime,facts()),OwnerLifecycleV2.Kind.QUEUE_DRAIN);return one(actual.drain(lifetime,actual.snapshot().pendingDrain(),facts()),OwnerLifecycleV2.Kind.OPEN_INITIAL);}
        void live(){var open=opening();bounded(actual.complete(open.token(),resource,true,null));check(actual.snapshot().phase()==OwnerLifecycleV2.Phase.LIVE&&!actual.snapshot().dirty(),"actual core clean initial completion");}
        void refresh(){var drain=actual.snapshot().pendingDrain();check(drain!=null,"real pending drain exists");var op=one(actual.drain(lifetime,drain,facts()),OwnerLifecycleV2.Kind.REFRESH_COMMITTED);bounded(actual.complete(op.token(),resource,true,null));}
    }
    private static void actualCore(){
        Core c=new Core();var open=c.opening();for(int i=0;i<7;i++)c.bounded(c.actual.invalidate(c.lifetime));check(c.actual.snapshot().pendingDrain()==null&&c.actual.permits(open.token()),"busy real operation retains immutable identity without queued drain");c.bounded(c.actual.complete(open.token(),c.resource,true,null));check(c.actual.snapshot().dirty()&&c.actual.snapshot().pendingDrain()!=null,"committed dirty real operation leaves one drain");c.refresh();check(!c.actual.snapshot().dirty(),"actual later refresh clears dirty");cases++;
        c.bounded(c.actual.resume(c.lifetime));c.refresh();c.bounded(c.actual.focusChanged(c.lifetime,true));c.refresh();var p=c.actual.snapshot().presentation();check(c.actual.admitsInput(c.lifetime,p),"real foreground focused presentation admits input");var input=c.one(c.actual.dispatchInput(c.lifetime,p),OwnerLifecycleV2.Kind.DISPATCH_INPUT);check(c.actual.dispatchInput(c.lifetime,p).isEmpty(),"real core serializes input");c.bounded(c.actual.pause(c.lifetime));c.bounded(c.actual.complete(input.token(),c.resource,true,null));check(!c.actual.admitsInput(c.lifetime,p)&&c.actual.snapshot().dirty(),"stale presentation cannot regain input");c.refresh();check(!c.actual.admitsInput(c.lifetime,c.actual.snapshot().presentation()),"background clean presentation remains noninteractive");cases++;
        Core foreign=new Core();var before=c.actual.snapshot();check(c.actual.complete(foreign.lifetime,new Object(),true,null).isEmpty()&&c.actual.snapshot().equals(before),"foreign real token completion inert");check(c.actual.invalidate(foreign.lifetime).isEmpty(),"foreign lifetime cannot dirty owner");cases++;
        for(int kind=0;kind<6;kind++){Core x=new Core();x.live();Object activity=kind==0?new Object():x.activity,root=kind==1?new Object():x.root,window=kind==5?new Object():kind==4?null:x.window;var f=new OwnerLifecycleV2.WindowFacts(activity,root,kind==2,kind!=3,window,320,480,true);var effects=x.bounded(x.actual.windowChanged(x.lifetime,f));check(x.actual.snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED&&effects.get(0).kind()==OwnerLifecycleV2.Kind.SEAL,"foreign/destroyed/lost actual window seals first");check(effects.stream().anyMatch(d->d.kind()==OwnerLifecycleV2.Kind.CLOSE&&d.resource()==x.resource),"exact actual resource receives terminal close");cases++;}
        for(int kind=0;kind<3;kind++){Core x=new Core();x.live();x.bounded(x.actual.windowChanged(x.lifetime,new OwnerLifecycleV2.WindowFacts(x.activity,x.root,false,true,x.window,kind==0?0:320,kind==1?0:480,kind!=2)));check(x.actual.snapshot().phase()==OwnerLifecycleV2.Phase.LIVE&&x.actual.snapshot().dirty()&&x.actual.snapshot().pendingDrain()==null,"temporary size/insets loss preserves resource without polling");x.bounded(x.actual.windowChanged(x.lifetime,x.facts()));check(x.actual.snapshot().pendingDrain()!=null,"ready restoration queues once");cases++;}
        for(boolean committed:new boolean[]{false,true}){Core x=new Core();var operation=x.opening();var close=x.bounded(x.actual.close(x.lifetime));check(close.stream().noneMatch(d->d.kind()==OwnerLifecycleV2.Kind.CLOSE),"actual busy open close defers resource release");var late=x.bounded(x.actual.complete(operation.token(),x.resource,committed,null));check(x.actual.snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED&&late.stream().filter(d->d.kind()==OwnerLifecycleV2.Kind.CLOSE).count()==1,"late acquired real resource closes exactly once");check(x.actual.complete(operation.token(),x.resource,true,null).isEmpty(),"duplicate actual completion inert");cases++;}
        Core failed=new Core();failed.live();var original=failed.actual.snapshot().resource();failed.bounded(failed.actual.invalidate(failed.lifetime));var refresh=failed.one(failed.actual.drain(failed.lifetime,failed.actual.snapshot().pendingDrain(),failed.facts()),OwnerLifecycleV2.Kind.REFRESH_COMMITTED);failed.bounded(failed.actual.complete(refresh.token(),new Object(),true,null));check(failed.actual.snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED&&failed.actual.snapshot().resource()==original,"actual refresh completion cannot replace resource");cases++;
        Core cleanup=new Core();cleanup.live();var effects=cleanup.bounded(cleanup.actual.close(cleanup.lifetime));Object first=new Object(),later=new Object();for(var effect:effects)if(effect.kind()==OwnerLifecycleV2.Kind.CANCEL_QUEUED||effect.kind()==OwnerLifecycleV2.Kind.UNREGISTER||effect.kind()==OwnerLifecycleV2.Kind.CLOSE){cleanup.actual.cleanupComplete(effect.token(),first);cleanup.actual.cleanupComplete(effect.token(),later);}var end=cleanup.actual.snapshot();check(!end.cancelPending()&&!end.unregisterPending()&&!end.closePending()&&end.resource()==null,"independent actual cleanup completion consumes all slots");check(end.cancelFailure()==first&&end.unregisterFailure()==first&&end.closeFailure()==first,"actual cleanup token keeps first identity");cases++;
        Core overflow=new Core(Long.MAX_VALUE);overflow.bounded(overflow.actual.invalidate(overflow.lifetime));check(overflow.actual.snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED&&overflow.actual.snapshot().terminalReason()==OwnerLifecycleV2.Reason.EPOCH_EXHAUSTED&&overflow.actual.snapshot().epoch()==Long.MAX_VALUE,"actual core epoch does not wrap");cases++;
    }
    public static void main(String[] args)throws Exception{
        Path inputs=Path.of(args[0]);registration(inputs);registrationReentry(inputs);removal(inputs);readiness(inputs);mainAndExhaustion(inputs);actualCore();
        System.out.println("{\"scope\":\"independent actual owner/core/Observer contract controls; historical vector mapping separate\",\"cases\":"+cases+",\"assertions\":"+assertions+"}");
    }
}
