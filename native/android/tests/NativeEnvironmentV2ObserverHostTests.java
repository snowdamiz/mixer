package dev.mixer.android;

import android.app.Activity;
import android.content.ComponentCallbacks;
import android.content.res.Configuration;
import android.animation.ValueAnimator;
import android.os.Looper;
import android.os.Handler;
import android.view.View;
import android.view.ViewTreeObserver;
import android.view.WindowInsets;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;

/** Faulting leaves exercise the production source; they do not establish Android behavior. */
public final class NativeEnvironmentV2ObserverHostTests {
    private static int cases;
    private static final class Fatal extends Error {
        private static final long serialVersionUID = 1L;
        Fatal(String message) { super(message); }
    }
    private record Fixture(Activity activity, FrameLayout root, NativeRenderer renderer) {
        Fixture() { this(new Activity()); }
        private Fixture(Activity activity) { this(activity, new FrameLayout(activity), new NativeRenderer()); }
        NativeEnvironmentV2.Observer allocate() {
            renderer.context=activity;
            return new NativeEnvironmentV2.Observer(activity,root,(source,change,cause,primary,fatal)->{
                renderer.environmentInvalidatedV2();
                if(change!=NativeEnvironmentV2.Change.INVALIDATED)source.close();
            });
        }
        NativeEnvironmentV2.Observer open() { NativeEnvironmentV2.Observer observer=allocate();observer.register();observer.bindRenderer(renderer);return observer; }
    }
    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
    private static Object field(Object object, String name) {
        try { Field field = object.getClass().getDeclaredField(name); field.setAccessible(true); return field.get(object); }
        catch (ReflectiveOperationException failure) { throw new AssertionError(failure); }
    }
    private static void generation(NativeEnvironmentV2.Observer observer, long value) {
        try { Field field = observer.getClass().getDeclaredField("generation"); field.setAccessible(true); field.setLong(observer,value); }
        catch (ReflectiveOperationException failure) { throw new AssertionError(failure); }
    }
    private static NativeEnvironmentV2.Observer current() { return (NativeEnvironmentV2.Observer)ObserverHostProbe.last[0]; }
    private static Throwable thrown(Runnable action) {
        try { action.run(); } catch (RuntimeException | Error failure) { return failure; }
        throw new AssertionError("expected terminal failure");
    }
    private static void unsupported(Runnable action) { check(thrown(action) instanceof AppearanceDescriptorV2.Failure,"capture was published or wrong failure"); }
    private static List<String> sequence(String verb, int last) {
        List<String> result = new ArrayList<>(); for (int i=0;i<=last;i++) result.add(verb+i); return result;
    }
    private static void calls(List<String> expected) { check(ObserverHostProbe.calls.equals(expected),"calls " + ObserverHostProbe.calls + " expected " + expected); }
    private static void removed(int last) {
        for (int i=0;i<8;i++) check(java.util.Collections.frequency(ObserverHostProbe.calls,"remove"+i) == (i<=last?1:0),"removal count " + i);
    }
    private static void retired(NativeEnvironmentV2.Observer observer) { check((Boolean)field(observer,"retired"),"not retired"); unsupported(observer::capture); }
    private static Throwable fault(boolean fatal, String label) { return fatal ? new Fatal(label) : new IllegalStateException(label); }
    private static void detach(NativeEnvironmentV2.Observer observer) {
        ((View.OnAttachStateChangeListener)field(observer,"attachment")).onViewDetachedFromWindow(observer.root);
    }
    private static List<Runnable> callbacks(NativeEnvironmentV2.Observer observer) {
        View.OnLayoutChangeListener layout = (View.OnLayoutChangeListener)field(observer,"layout");
        View.OnAttachStateChangeListener attach = (View.OnAttachStateChangeListener)field(observer,"attachment");
        ViewTreeObserver.OnWindowFocusChangeListener focus = (ViewTreeObserver.OnWindowFocusChangeListener)field(observer,"windowFocus");
        View.OnApplyWindowInsetsListener insets = (View.OnApplyWindowInsetsListener)field(observer,"insets");
        android.app.UiModeManager.ContrastChangeListener contrast = (android.app.UiModeManager.ContrastChangeListener)field(field(observer,"contrast"),"listener");
        android.view.accessibility.AccessibilityManager.HighContrastTextStateChangeListener high = (android.view.accessibility.AccessibilityManager.HighContrastTextStateChangeListener)field(field(observer,"highContrast"),"listener");
        ValueAnimator.DurationScaleChangeListener motion = (ValueAnimator.DurationScaleChangeListener)field(field(observer,"motion"),"listener");
        return List.of(() -> observer.onConfigurationChanged(new Configuration()), observer::onLowMemory,
            () -> layout.onLayoutChange(observer.root,1,0,0,0,0,0,0,0),
            () -> layout.onLayoutChange(observer.root,0,0,0,0,0,0,0,0),
            () -> attach.onViewAttachedToWindow(observer.root), () -> attach.onViewDetachedFromWindow(observer.root),
            () -> focus.onWindowFocusChanged(false), () -> insets.onApplyWindowInsets(observer.root,new WindowInsets()),
            () -> contrast.onContrastChanged(1), () -> high.onHighContrastTextStateChanged(true), () -> motion.onChanged(0), observer::invalidate);
    }
    private static void twoPhase() {
        ObserverHostProbe.reset();Fixture f=new Fixture();NativeEnvironmentV2.Observer o=f.allocate();
        check(ObserverHostProbe.calls.isEmpty(),"constructor acquired listeners");unsupported(o::capture);
        check(thrown(()->o.bindRenderer(f.renderer)) instanceof IllegalStateException,"premature binding");
        o.register();unsupported(o::capture);check(thrown(o::register) instanceof IllegalStateException,"repeat registration");
        o.bindRenderer(f.renderer);check(o.capture().current(f.renderer),"bound capture");
        check(thrown(()->o.bindRenderer(f.renderer)) instanceof IllegalStateException,"same renderer rebound");
        NativeRenderer foreign=new NativeRenderer();foreign.context=new Activity();
        check(thrown(()->o.rendererTerminal(foreign,NativeEnvironmentV2.RendererCause.CAPTURE_FAILED,null,null)) instanceof IllegalArgumentException,"foreign terminal report");
        check(o.capture().current(f.renderer),"foreign report changed authority");o.close();cases++;
    }
    private static void clean() {
        ObserverHostProbe.reset(); Fixture f = new Fixture(); NativeEnvironmentV2.Observer o=f.open();
        calls(sequence("add",7)); NativeEnvironmentV2 capture=o.capture(); check(capture.current(f.renderer),"fresh capture");
        o.invalidate(); check(!capture.current(f.renderer),"old generation admitted");
        check(f.renderer.invalidations==1,"notification count");
        o.close(); retired(o); removed(7); check(f.root.insetListener==null,"owned inset listener still set");
        List<String> expected=sequence("add",7); expected.addAll(sequence("remove",7)); calls(expected);
        int[] status=(int[])field(o,"cleanup"); for (int value:status) check(value==NativeEnvironmentV2.Observer.RETURNED,"cleanup outcome");
        List<String> before=List.copyOf(ObserverHostProbe.calls);o.close();calls(before);
        cases++;
    }
    private static void acquisitionFailures() {
        for (int slot=0;slot<8;slot++) for(int phase=0;phase<2;phase++) for(boolean fatal:new boolean[]{false,true}) {
            ObserverHostProbe.reset();Fixture f=new Fixture();Throwable failure=fault(fatal,"acquire"+slot+":"+phase);
            ObserverHostProbe.faults[phase][slot]=failure;
            check(thrown(f::open)==failure,"primary acquisition failure changed");
            NativeEnvironmentV2.Observer o=current();retired(o);removed(slot);
            List<String> expected=sequence("add",slot);expected.addAll(sequence("remove",slot));calls(expected);
            for(Object listener:ObserverHostProbe.live)check(listener==null,"rollback left known live listener");
            List<String> before=List.copyOf(ObserverHostProbe.calls);check(thrown(o::close)==failure,"repeat failure changed");calls(before);cases++;
        }
    }
    private static void cleanupFailures() {
        for(int slot=0;slot<8;slot++)for(int phase=2;phase<4;phase++)for(boolean fatal:new boolean[]{false,true}){
            ObserverHostProbe.reset();Fixture f=new Fixture();NativeEnvironmentV2.Observer o=f.open();
            Throwable failure=fault(fatal,"remove"+slot+":"+phase);ObserverHostProbe.faults[phase][slot]=failure;
            check(thrown(o::close)==failure,"cleanup failure changed");retired(o);removed(7);
            int[] status=(int[])field(o,"cleanup");check(status[slot]==NativeEnvironmentV2.Observer.FAILED_UNCERTAIN,"unknown outcome claimed returned");
            check(((Throwable[])field(o,"cleanupFailures"))[slot]==failure,"diagnostic missing");
            List<String> before=List.copyOf(ObserverHostProbe.calls);thrown(o::close);calls(before);cases++;
        }
        ObserverHostProbe.reset();Fixture f=new Fixture();NativeEnvironmentV2.Observer o=f.open();
        for(int slot=0;slot<8;slot++)ObserverHostProbe.faults[2][slot]=new IllegalStateException("all"+slot);
        thrown(o::close);removed(7);for(Throwable value:(Throwable[])field(o,"cleanupFailures"))check(value!=null,"independent cleanup missing");cases++;
        for(int fatalSlot=0;fatalSlot<8;fatalSlot++){
            ObserverHostProbe.reset();Fixture each=new Fixture();Throwable primary=new IllegalStateException("original-add");
            ObserverHostProbe.faults[1][7]=primary;
            for(int slot=0;slot<8;slot++)ObserverHostProbe.faults[2][slot]=fault(slot==fatalSlot,"cleanup"+slot);
            Throwable escaped=thrown(each::open);check(escaped==ObserverHostProbe.faults[2][fatalSlot],"fatal cleanup demoted");
            check(field(current(),"primaryFailure")==primary,"primary not retained");
            check(List.of(escaped.getSuppressed()).contains(primary),"primary not attached to fatal");removed(7);cases++;
        }
    }
    private static void reentry() {
        for(int phase=0;phase<4;phase++)for(int slot=0;slot<8;slot++)for(boolean detaching:new boolean[]{false,true}){
            ObserverHostProbe.reset();Fixture f=new Fixture();
            final boolean adding=phase<2;
            ObserverHostProbe.hooks[phase][slot]=()->{ NativeEnvironmentV2.Observer o=current(); if(detaching)detach(o);else o.close(); };
            NativeEnvironmentV2.Observer o;
            if(adding){thrown(f::open);o=current();removed(slot);check(ObserverHostProbe.calls.stream().filter(v->v.startsWith("add")).count()==slot+1,"continued registration after terminal reentry");}
            else{o=f.open();o.close();removed(7);}
            retired(o);for(Object listener:ObserverHostProbe.live)check(listener==null,"reentry leaked known acquisition");
            int notifications=f.renderer.invalidations;for(Runnable callback:callbacks(o))callback.run();check(f.renderer.invalidations==notifications,"late notification after reentry");cases++;
        }
        for(int slot=0;slot<8;slot++){
            ObserverHostProbe.reset();Fixture f=new Fixture();
            ObserverHostProbe.hooks[1][slot]=()->{unsupported(current()::capture);current().invalidate();};
            NativeEnvironmentV2.Observer o=f.open();check(f.renderer.invalidations==1,"registration notification lost");check(o.capture().current(f.renderer),"post-construction capture unavailable");o.close();cases++;
        }
        for(int slot=0;slot<8;slot++){
            ObserverHostProbe.reset();Fixture f=new Fixture();ObserverHostProbe.hooks[1][slot]=()->current().invalidate();
            Throwable failure=new Fatal("registration-invalidation");f.renderer.notification=()->{throw (Error)failure;};
            check(thrown(f::open)==failure,"registration invalidation fatal changed");removed(slot);cases++;
        }
    }
    private static void lateAndThreads() {
        ObserverHostProbe.reset();Fixture f=new Fixture();NativeEnvironmentV2.Observer o=f.open();NativeEnvironmentV2 capture=o.capture();o.close();
        long epoch=(Long)field(o,"generation");int notifications=f.renderer.invalidations,reads=ObserverHostProbe.reads,tokens=ObserverHostProbe.tokenReads;
        for(Runnable callback:callbacks(o))callback.run();check(!capture.current(f.renderer),"retired capture admitted");
        check((Long)field(o,"generation")==epoch&&notifications==f.renderer.invalidations&&reads==ObserverHostProbe.reads&&tokens==ObserverHostProbe.tokenReads,"late callback read/changed state");
        List<Runnable> entries=new ArrayList<>(callbacks(o));entries.remove(10);entries.add(o::close);entries.add(o::capture);entries.add(o::read);entries.add(()->capture.current(f.renderer));entries.add(capture::root);
        Looper.mainThread=false;
        try {for(Runnable entry:entries)check(thrown(entry) instanceof IllegalStateException,"stale guard preceded thread assertion");check(thrown(f::open) instanceof IllegalStateException,"constructor thread assertion");}
        finally {Looper.mainThread=true;}
        removed(7);cases++;
    }
    private static void terminalsAndTargets() {
        ObserverHostProbe.reset();Fixture f=new Fixture();NativeEnvironmentV2.Observer o=f.open();generation(o,Long.MAX_VALUE);
        NativeEnvironmentV2.Observer exhausted=o;
        f.renderer.notification=()->{check((Boolean)field(exhausted,"retired"),"retirement was not visible before callback");unsupported(exhausted::capture);};
        o.invalidate();check(f.renderer.invalidations==1,"exhaustion invalidation");check((Long)field(o,"generation")==Long.MAX_VALUE,"generation wrapped");removed(7);o.invalidate();check(f.renderer.invalidations==1,"exhaustion reopened");cases++;
        ObserverHostProbe.reset();f=new Fixture();o=f.open();NativeEnvironmentV2.Observer detached=o;
        f.renderer.notification=()->{retired(detached);};detach(o);removed(7);cases++;
        ObserverHostProbe.reset();f=new Fixture();o=f.open();ViewTreeObserver original=f.root.tree;f.root.tree=new ViewTreeObserver();
        f.activity.resolver=new android.content.ContentResolver();o.close();
        check(original.removes==1&&f.root.tree.removes==0,"replacement focus target used");check(ObserverHostProbe.targets[7]==ValueAnimator.class,"effective animator target replaced");cases++;
        ObserverHostProbe.reset();f=new Fixture();o=f.open();original=f.root.tree;original.alive=false;f.root.tree=new ViewTreeObserver();o.close();
        check(original.removes==0&&f.root.tree.removes==0,"dead target removal claimed");
        check(((int[])field(o,"cleanup"))[3]==NativeEnvironmentV2.Observer.DEAD_TARGET_UNCERTAIN,"dead diagnostic missing");
        for(int slot=0;slot<8;slot++)check(java.util.Collections.frequency(ObserverHostProbe.calls,"remove"+slot)==(slot==3?0:1),"dead target truncated cleanup");cases++;
        for(boolean fatal:new boolean[]{false,true}){
            ObserverHostProbe.reset();f=new Fixture();o=f.open();Throwable primary=fault(fatal,"owner");
            f.renderer.notification=()->{if(primary instanceof Error)throw (Error)primary;throw (RuntimeException)primary;};
            check(thrown(o::invalidate)==primary,"owner failure changed");retired(o);removed(7);cases++;
        }
    }
    private static void motionResults() {
        ObserverHostProbe.reset();Fixture f=new Fixture();ObserverHostProbe.motionAdd=false;
        check(thrown(f::open) instanceof IllegalStateException,"false registration accepted");
        retired(current());removed(7);check(!current().ready(),"failed registration ready");cases++;
        ObserverHostProbe.reset();f=new Fixture();ObserverHostProbe.motionAdd=false;ObserverHostProbe.motionRemove=false;
        Throwable rejected=thrown(f::open);check(rejected instanceof IllegalStateException,"false registration/removal accepted");
        retired(current());removed(7);
        check(current().cleanupLedger().primary()==rejected,"registration primary replaced");
        check(current().cleanupLedger().state(7)==NativeEnvironmentV2.Observer.FAILED_UNCERTAIN,"failed cleanup claimed returned");cases++;
        ObserverHostProbe.reset();f=new Fixture();NativeEnvironmentV2.Observer o=f.open();
        NativeEnvironmentV2 capture=o.capture();
        ValueAnimator.DurationScaleChangeListener listener=(ValueAnimator.DurationScaleChangeListener)ObserverHostProbe.live[7];
        check(field(field(o,"motion"),"listener")==listener,"listener not strongly owned");
        ObserverHostProbe.animator=0;listener.onChanged(0);Handler.drain();
        check(!capture.current(f.renderer),"effective motion callback did not invalidate capture");
        check(f.renderer.invalidations==1,"effective change notification missing");cases++;
        ObserverHostProbe.motionRemove=false;
        Throwable failure=thrown(o::close);check(failure instanceof IllegalStateException,"false removal accepted");
        check(o.cleanupLedger().state(7)==NativeEnvironmentV2.Observer.FAILED_UNCERTAIN,"false removal claimed returned");
        removed(7);check(thrown(o::close)==failure,"uncertain removal retried/lost");removed(7);cases++;
    }
    private static Throwable background(Runnable action) {
        java.util.concurrent.atomic.AtomicReference<Throwable> failure = new java.util.concurrent.atomic.AtomicReference<>();
        Thread thread = new Thread(() -> {
            try {
                check(Looper.myLooper() != Looper.getMainLooper(), "background impersonated UI");
                action.run();
            } catch (RuntimeException | Error caught) { failure.set(caught); }
        }, "motion-binder-host");
        thread.setDaemon(true); thread.start();
        try { thread.join(2000); }
        catch (InterruptedException caught) { Thread.currentThread().interrupt(); throw new AssertionError(caught); }
        check(!thread.isAlive(), "bounded background callback did not return");
        return failure.get();
    }
    private static ValueAnimator.DurationScaleChangeListener motion() {
        return (ValueAnimator.DurationScaleChangeListener)ObserverHostProbe.last[7];
    }
    private static void producerPublication() {
        for (float effective : new float[]{0, 2, Float.NaN}) {
            ObserverHostProbe.reset(); Fixture f = new Fixture(); NativeEnvironmentV2.Observer o = f.open();
            NativeEnvironmentV2 old = o.capture(); int reads = ObserverHostProbe.readCounts.get("animator");
            ValueAnimator.DurationScaleChangeListener listener = motion();
            // Opaque flags schedule the test without a release/acquire edge that would
            // accidentally publish the producer's plain getter state before delivery.
            java.util.concurrent.atomic.AtomicInteger done = new java.util.concurrent.atomic.AtomicInteger();
            java.util.concurrent.atomic.AtomicInteger finish = new java.util.concurrent.atomic.AtomicInteger();
            Throwable[] failure = {null};
            Thread producer = new Thread(() -> {
                try {
                    ValueAnimator.changeFromProducer(1, Float.NaN, listener);
                    for (int i=0; i<64; i++) ValueAnimator.changeFromProducer(effective, -1, listener);
                } catch (RuntimeException | Error caught) { failure[0] = caught; }
                finally { done.setOpaque(1); }
                long deadline = System.nanoTime() + 2_000_000_000L;
                while (finish.getOpaque() == 0 && System.nanoTime() < deadline) Thread.onSpinWait();
            }, "motion-effective-producer");
            producer.setDaemon(true); producer.start();
            try {
                long deadline = System.nanoTime() + 2_000_000_000L;
                while (done.getOpaque() == 0 && System.nanoTime() < deadline) Thread.onSpinWait();
                check(done.getOpaque() == 1, "producer did not reach coalesced notice bound");
                check(Handler.pending() == 1 && f.renderer.invalidations == 0, "producer did UI work or failed coalescing");
                check(ObserverHostProbe.readCounts.get("animator") == reads, "producer read the effective getter");
                Handler.drain();
                check(f.renderer.invalidations == 1 && Handler.pending() == 0, "coalesced producer delivery missing");
                check(Float.compare(ValueAnimator.getDurationScale(), effective) == 0,
                    "main did not observe the exact coalesced producer value");
                if (Float.isNaN(effective)) unsupported(o::capture);
                else check(!old.current(f.renderer)
                    && o.capture().value.accessibility().reduceMotion() == (effective == 0),
                    "coalesced producer value was not validated and captured");
            } finally {
                // Join only AFTER all getter/result observations, solely for owned cleanup.
                finish.setOpaque(1);
                try { producer.join(2000); }
                catch (InterruptedException caught) { Thread.currentThread().interrupt(); throw new AssertionError(caught); }
                check(!producer.isAlive() && failure[0] == null, "producer cleanup/failure");
                o.close();
            }
            cases++;
        }
    }
    private static void motionThreads() {
        ObserverHostProbe.reset(); Fixture f = new Fixture(); NativeEnvironmentV2.Observer o = f.open();
        NativeEnvironmentV2 old = o.capture(); int reads = ObserverHostProbe.readCounts.get("animator");
        ObserverHostProbe.animator = 0;
        check(background(() -> { for (int i=0;i<64;i++) motion().onChanged(Float.NaN); }) == null, "Binder callback escaped");
        check(f.renderer.invalidations == 0 && Handler.pending() == 1, "callback did UI work or unbounded posting");
        check(ObserverHostProbe.readCounts.get("animator") == reads, "background getter read");
        check(background(o::invalidate) instanceof IllegalStateException, "production UI guard weakened");
        Handler.drain(); check(f.renderer.invalidations == 1, "UI callback missing");
        check(!old.current(f.renderer) && o.capture().value.accessibility().reduceMotion(), "validated effective reread missing");
        ObserverHostProbe.animator = Float.NaN;
        check(background(() -> motion().onChanged(1)) == null, "invalid getter callback escaped");
        Handler.drain(); unsupported(o::capture); o.close(); cases++;

        ObserverHostProbe.reset(); f = new Fixture(); o = f.open();
        check(background(() -> motion().onChanged(0)) == null, "pending callback escaped");
        o.close(); Handler.drain();
        check(background(() -> motion().onChanged(0)) == null, "late Binder callback escaped");
        Handler.drain(); check(f.renderer.invalidations == 0 && Handler.pending() == 0, "removed listener delivered");
        removed(7); cases++;

        ObserverHostProbe.reset(); f = new Fixture(); o = f.open();
        java.util.concurrent.CountDownLatch posting = new java.util.concurrent.CountDownLatch(1);
        java.util.concurrent.CountDownLatch removed = new java.util.concurrent.CountDownLatch(1);
        Handler.beforeEnqueue = () -> {
            posting.countDown();
            try { check(removed.await(2, java.util.concurrent.TimeUnit.SECONDS), "remove did not release posting"); }
            catch (InterruptedException e) { Thread.currentThread().interrupt(); throw new AssertionError(e); }
        };
        java.util.concurrent.atomic.AtomicReference<Throwable> raced = new java.util.concurrent.atomic.AtomicReference<>();
        Thread racing = new Thread(() -> { try {motion().onChanged(0);}catch(Throwable e){raced.set(e);}}, "motion-post-remove-race");
        racing.setDaemon(true); racing.start();
        try {
            check(posting.await(2, java.util.concurrent.TimeUnit.SECONDS), "post boundary not reached");
            o.close();
        } catch (InterruptedException e) {Thread.currentThread().interrupt();throw new AssertionError(e);}
        finally {removed.countDown();}
        try {racing.join(2000);}catch(InterruptedException e){Thread.currentThread().interrupt();throw new AssertionError(e);}
        check(!racing.isAlive() && raced.get()==null && Handler.pending()==1, "late enqueue race not exercised");
        Handler.beforeEnqueue=null;Handler.drain();check(f.renderer.invalidations==0,"post admitted before remove delivered after remove");cases++;

        for (int phase=0;phase<4;phase++) {
            ObserverHostProbe.reset(); Fixture each = new Fixture();
            ObserverHostProbe.hooks[phase][7] = () -> check(background(() -> motion().onChanged(0)) == null, "racing callback escaped");
            NativeEnvironmentV2.Observer observer = each.open();
            if (phase<2) { check(each.renderer.invalidations == 0, "add callback ran inline"); Handler.drain(); check(each.renderer.invalidations == 1, "add callback lost"); }
            observer.close(); Handler.drain();
            check(each.renderer.invalidations == (phase<2?1:0), "remove callback delivered"); removed(7); cases++;
        }
        for (boolean fatal:new boolean[]{false,true}) {
            ObserverHostProbe.reset(); Fixture each = new Fixture(); Throwable fault=fault(fatal,"queued registration failure");
            ObserverHostProbe.hooks[1][7]=()->check(background(()->motion().onChanged(0))==null,"add callback escaped");
            ObserverHostProbe.faults[1][7]=fault;
            check(thrown(each::open)==fault,"registration identity changed"); Handler.drain();
            check(each.renderer.invalidations==1,"queued registration notice escaped terminal report"); removed(7); cases++;

            ObserverHostProbe.reset(); each=new Fixture(); NativeEnvironmentV2.Observer observer=each.open();
            Throwable notification=fault(fatal,"queued UI sink");
            each.renderer.notification=()->{if(notification instanceof Error)throw (Error)notification;throw (RuntimeException)notification;};
            check(background(()->motion().onChanged(0))==null,"sink ran on Binder");
            check(thrown(Handler::drain)==notification,"UI sink failure identity changed"); retired(observer);removed(7); cases++;
        }
        ObserverHostProbe.reset(); f=new Fixture(); ObserverHostProbe.motionAdd=false;
        ObserverHostProbe.hooks[1][7]=()->check(background(()->motion().onChanged(0))==null,"false registration callback");
        thrown(f::open); Handler.drain(); check(f.renderer.invalidations==1,"false registration delivered queued notice");cases++;

        for(int phase=0;phase<2;phase++) {
            ObserverHostProbe.reset(); int[] notices={0};
            NativeEnvironmentPlatformV2.Listener handle=NativeEnvironmentPlatformV2.motionListener(()->notices[0]++);
            ObserverHostProbe.hooks[phase][7]=()->{
                check(background(()->motion().onChanged(0))==null,"reentrant add callback");
                handle.remove(); handle.remove();
                check(thrown(handle::add) instanceof IllegalStateException,"reentrant add reopened");
            };
            handle.add(); Handler.drain();handle.remove();
            check(notices[0]==0 && ObserverHostProbe.live[7]==null,"reentrant remove leaked/delivered");
            check(java.util.Collections.frequency(ObserverHostProbe.calls,"remove7")==1,"reentrant removal not once");cases++;
        }
        for(boolean addFatal:new boolean[]{false,true})for(boolean removeFatal:new boolean[]{false,true}) {
            ObserverHostProbe.reset(); int[] notices={0};
            NativeEnvironmentPlatformV2.Listener handle=NativeEnvironmentPlatformV2.motionListener(()->notices[0]++);
            Throwable primary=fault(addFatal,"direct reentrant add");Throwable cleanup=fault(removeFatal,"direct deferred remove");
            ObserverHostProbe.hooks[0][7]=()->{motion().onChanged(0);handle.remove();};
            ObserverHostProbe.faults[1][7]=primary;ObserverHostProbe.faults[2][7]=cleanup;
            Throwable escaped=thrown(handle::add);Throwable expected=removeFatal&&!addFatal?cleanup:primary;
            check(escaped==expected,"deferred cleanup changed fatal priority/identity");
            check(List.of(escaped.getSuppressed()).contains(escaped==primary?cleanup:primary),"deferred diagnostic missing");
            Handler.drain();check(notices[0]==0,"failed reentrant add delivered");handle.remove();
            check(java.util.Collections.frequency(ObserverHostProbe.calls,"remove7")==1,"failed direct cleanup retried");cases++;
        }
        for(int failureKind=0;failureKind<3;failureKind++) {
            ObserverHostProbe.reset(); f=new Fixture();o=f.open();
            Throwable fault=failureKind==0?null:fault(failureKind==2,"dispatch failure");
            Handler.postResult=false;Handler.postFailure=fault;
            Throwable escaped=background(()->motion().onChanged(0));
            check(fault==null?escaped instanceof IllegalStateException:escaped==fault,"dispatch failure identity lost");
            Handler.postResult=true;Handler.postFailure=null;
            check(background(()->motion().onChanged(0))==null,"dispatch did not recover");Handler.drain();
            check(f.renderer.invalidations==1,"failed dispatch kept queue reservation");o.close();cases++;
        }
    }
    public static void main(String[] args) {
        producerPublication();motionThreads();motionResults();twoPhase();clean();acquisitionFailures();cleanupFailures();reentry();lateAndThreads();terminalsAndTargets();
        System.out.println("PASS " + cases + " production Observer host cases; faulting Android leaves only; native runtime pending");
    }
}
