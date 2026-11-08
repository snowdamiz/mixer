package dev.mixer.android;

import android.animation.ValueAnimator;
import android.os.Handler;
import android.os.Looper;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/** Independent schedules only: all product and existing platform-leaf bytes are unchanged. */
public final class MotionOrderingProbe {
    private static Object field(Object value, String name) throws ReflectiveOperationException {
        Field f=value.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(value);
    }
    private static void check(boolean condition, String message) {if(!condition)throw new AssertionError(message);}
    private static void call(Object value,String name) throws ReflectiveOperationException {
        Method m=value.getClass().getDeclaredMethod(name);m.setAccessible(true);m.invoke(value);
    }
    private static void schedule(boolean drainBeforeSecondCallback) throws Exception {
        ConcreteHostProbe.reset();
        Class<?> cls=Class.forName("dev.mixer.android.NativeOwnerV2ConcreteHostTests$Fixture");
        Constructor<?> ctor=cls.getDeclaredConstructor();ctor.setAccessible(true);
        Object fixture=ctor.newInstance();call(fixture,"ready");
        NativeOwnerV2 owner=(NativeOwnerV2)field(fixture,"owner");
        Handler ownerQueue=(Handler)field(fixture,"queue");
        NativeEnvironmentV2.Observer observer=(NativeEnvironmentV2.Observer)field(owner,"observer");
        Object motion=field(observer,"motion");Handler firstQueue=(Handler)field(motion,"main");
        ValueAnimator.DurationScaleChangeListener first=(ValueAnimator.DurationScaleChangeListener)field(motion,"listener");
        OwnerLifecycleV2 core=(OwnerLifecycleV2)field(owner,"core");
        OwnerLifecycleV2.Snapshot before=core.snapshot();long generation=(Long)field(observer,"generation");
        Object coordinator=field(owner,"coordinator");byte[] packet=(byte[])field(coordinator,"committedPacket");byte[] bytes=packet.clone();
        AtomicReference<OwnerLifecycleV2.Snapshot> atProbe=new AtomicReference<>();
        long[] probeGeneration={0};boolean[] main={false};
        NativeEnvironmentPlatformV2.Listener probe=NativeEnvironmentPlatformV2.motionListener(()->{
            atProbe.set(core.snapshot());main[0]=Looper.myLooper()==Looper.getMainLooper();
            try{probeGeneration[0]=(Long)field(observer,"generation");}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}
        });probe.add();
        Handler secondQueue=(Handler)field(probe,"main");
        ValueAnimator.DurationScaleChangeListener second=(ValueAnimator.DurationScaleChangeListener)field(probe,"listener");
        CountDownLatch firstPosted=new CountDownLatch(1), continueDispatch=new CountDownLatch(1);
        AtomicReference<Throwable> failure=new AtomicReference<>();
        ValueAnimator.effectiveScale=0;
        Thread binder=new Thread(()->{
            try{
                check(Looper.myLooper()!=Looper.getMainLooper(),"not a background callback");
                first.onChanged(Float.NaN);firstPosted.countDown();
                check(continueDispatch.await(2,TimeUnit.SECONDS),"schedule wait expired");
                second.onChanged(Float.NaN);
            }catch(Throwable caught){failure.set(caught);}
        },"review-binder-listener-loop");binder.setDaemon(true);binder.start();
        try {
            check(firstPosted.await(2,TimeUnit.SECONDS),"first post missing");
            check(core.snapshot().epoch()==before.epoch(),"background touched owner");
            if(drainBeforeSecondCallback){firstQueue.drainAll(4);ownerQueue.drainAll(4);}
            continueDispatch.countDown();binder.join(2000);
            check(!binder.isAlive()&&failure.get()==null,"bounded background failure: "+failure.get());
            if(!drainBeforeSecondCallback)firstQueue.drainAll(4);
            secondQueue.drainAll(4);
            OwnerLifecycleV2.Snapshot observed=atProbe.get();
            boolean line134=observed.dirty()&&observed.pendingDrain()!=null&&observed.operation()==null;
            check(main[0]&&probeGeneration[0]>generation&&observed.epoch()>before.epoch(),"callback/generation incorrect");
            ownerQueue.drainAll(4);
            check(owner.hasCommittedPresentation()&&!core.snapshot().dirty()&&core.snapshot().presentation()!=before.presentation(),"product did not refresh");
            check(field(coordinator,"committedPacket")==packet&&Arrays.equals(packet,bytes),"packet identity/bytes changed");
            NativeRenderer renderer=(NativeRenderer)field(coordinator,"renderer");
            NativeEnvironmentV2 committed=(NativeEnvironmentV2)field(renderer,"v2CommittedEnvironment");
            check(committed.value.accessibility().reduceMotion(),"effective getter not committed");
            check(line134!=drainBeforeSecondCallback,"unexpected oracle result");
            System.out.println("PASS schedule="+(drainBeforeSecondCallback?"owner-drains-before-sideband-post":"both-posts-before-owner-drain")
                +" native-line134-predicate="+line134+" productRefresh=true main=true generationAdvanced=true exactPacket=true");
        } finally {continueDispatch.countDown();binder.join(2000);probe.remove();call(fixture,"close");ValueAnimator.effectiveScale=1;ConcreteHostProbe.reset();}
    }
    public static void main(String[] args) throws Exception {
        Looper.getMainLooper();
        Field descriptor=NativeOwnerV2ConcreteHostTests.class.getDeclaredField("descriptor");descriptor.setAccessible(true);
        descriptor.set(null,Files.readAllBytes(Path.of(args[0])));
        schedule(false);schedule(true);
    }
}
