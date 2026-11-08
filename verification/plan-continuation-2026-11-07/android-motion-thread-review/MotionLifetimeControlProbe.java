package dev.mixer.android;
import android.animation.ValueAnimator;
import android.os.Handler;
import android.os.Looper;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.atomic.AtomicReference;

public final class MotionLifetimeControlProbe {
    private static Object field(Object target,String name)throws Exception {Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(target);}
    private static Object call(Object target,String name)throws Exception {Method m=target.getClass().getDeclaredMethod(name);m.setAccessible(true);return m.invoke(target);}
    private static void check(boolean ok,String label){if(!ok)throw new AssertionError(label);}
    private static Object fixture()throws Exception {
        ConcreteHostProbe.reset();Class<?> cls=Class.forName("dev.mixer.android.NativeOwnerV2ConcreteHostTests$Fixture");
        Constructor<?> c=cls.getDeclaredConstructor();c.setAccessible(true);Object f=c.newInstance();call(f,"ready");return f;
    }
    private static Throwable callback(ValueAnimator.DurationScaleChangeListener listener)throws Exception {
        AtomicReference<Throwable> failure=new AtomicReference<>();
        Thread t=new Thread(()->{try{check(Looper.myLooper()!=Looper.getMainLooper(),"real background required");listener.onChanged(Float.NaN);}catch(Throwable caught){failure.set(caught);}},"review-lifetime-binder");
        t.setDaemon(true);t.start();t.join(2000);check(!t.isAlive(),"callback bound");return failure.get();
    }
    private static void retention()throws Exception {
        Object f=fixture();NativeOwnerV2 owner=(NativeOwnerV2)field(f,"owner");
        Object observer=field(owner,"observer"),motion=field(observer,"motion");
        Handler delivery=(Handler)field(motion,"main"),ownerQueue=(Handler)field(f,"queue");
        ValueAnimator.DurationScaleChangeListener listener=(ValueAnimator.DurationScaleChangeListener)field(motion,"listener");
        OwnerLifecycleV2 core=(OwnerLifecycleV2)field(owner,"core");
        check(callback(listener)==null&&delivery.queued()==1,"initial callback absent");
        owner.close();long closedEpoch=core.snapshot().epoch();
        check(delivery.queued()==1,"control must retain already queued callback");
        check(field(motion,"phase").toString().equals("CLOSED"),"adapter not retired");
        delivery.drainAll(4);check(callback(listener)==null,"late callback threw");delivery.drainAll(4);
        check(core.snapshot().epoch()==closedEpoch&&delivery.queued()==0&&ownerQueue.queued()==0,"closed owner changed or requeued");
        check(!owner.hasCommittedPresentation(),"closed presentation resurrected");
        System.out.println("PASS retainedQueuedEntryAfterClose=1 afterDrain=0 latePost=0 closedOwnerEpochUnchanged=true noPresentationResurrection=true; no GC timing claim");
        call(f,"close");ConcreteHostProbe.reset();
    }
    private static void rejectedPost()throws Exception {
        Object f=fixture();NativeOwnerV2 owner=(NativeOwnerV2)field(f,"owner");
        Object observer=field(owner,"observer"),motion=field(observer,"motion");
        Handler delivery=(Handler)field(motion,"main"),ownerQueue=(Handler)field(f,"queue");
        ValueAnimator.DurationScaleChangeListener listener=(ValueAnimator.DurationScaleChangeListener)field(motion,"listener");
        NativeRenderer renderer=(NativeRenderer)call(f,"renderer");
        OwnerLifecycleV2 core=(OwnerLifecycleV2)field(owner,"core");long epoch=core.snapshot().epoch();
        delivery.postResult=false;ValueAnimator.effectiveScale=0;
        Throwable rejected=callback(listener);
        check(rejected instanceof IllegalStateException,"false post not reported");
        check(core.snapshot().epoch()==epoch&&delivery.queued()==0,"Binder touched owner or queued falsely");
        check(!renderer.presentationCurrentV2(),"changed getter authorized stale presentation");
        check(core.snapshot().epoch()>epoch&&core.snapshot().dirty(),"current-check did not seal/invalidate");
        ownerQueue.drainAll(4);check(owner.hasCommittedPresentation()&&renderer.presentationCurrentV2(),"owning main recovery failed");
        System.out.println("PASS injectedPostFalseEscapedOnBinder=true queueReservationReleased=true noBinderOwnerMutation=true mainCurrentCheckRejectsStale=true freshOwnerDrainRecovered=true; injected fault, not native false-return reachability");
        call(f,"close");ValueAnimator.effectiveScale=1;ConcreteHostProbe.reset();
    }
    public static void main(String[] args)throws Exception {
        Looper.getMainLooper();Field d=NativeOwnerV2ConcreteHostTests.class.getDeclaredField("descriptor");d.setAccessible(true);d.set(null,Files.readAllBytes(Path.of(args[0])));
        retention();rejectedPost();
    }
}
