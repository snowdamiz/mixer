package dev.mixer.android;

import android.app.Activity;
import android.content.ComponentCallbacks;
import android.content.res.Configuration;
import android.database.ContentObserver;
import android.os.Looper;
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
        NativeEnvironmentV2.Observer open() { return new NativeEnvironmentV2.Observer(renderer, activity, root); }
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
        android.app.UiModeManager.ContrastChangeListener contrast = (android.app.UiModeManager.ContrastChangeListener)field(observer,"contrast");
        android.view.accessibility.AccessibilityManager.HighContrastTextStateChangeListener high = (android.view.accessibility.AccessibilityManager.HighContrastTextStateChangeListener)field(observer,"highContrast");
        ContentObserver motion = (ContentObserver)field(observer,"motion");
        return List.of(() -> observer.onConfigurationChanged(new Configuration()), observer::onLowMemory,
            () -> layout.onLayoutChange(observer.root,1,0,0,0,0,0,0,0),
            () -> layout.onLayoutChange(observer.root,0,0,0,0,0,0,0,0),
            () -> attach.onViewAttachedToWindow(observer.root), () -> attach.onViewDetachedFromWindow(observer.root),
            () -> focus.onWindowFocusChanged(false), () -> insets.onApplyWindowInsets(observer.root,new WindowInsets()),
            () -> contrast.onContrastChanged(1), () -> high.onHighContrastTextStateChanged(true), () -> motion.onChange(false), observer::invalidate);
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
        List<Runnable> entries=new ArrayList<>(callbacks(o));entries.add(o::close);entries.add(o::capture);entries.add(o::read);entries.add(()->capture.current(f.renderer));entries.add(capture::root);
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
        android.content.ContentResolver resolver=f.activity.resolver;f.activity.resolver=new android.content.ContentResolver();o.close();
        check(original.removes==1&&f.root.tree.removes==0,"replacement focus target used");check(ObserverHostProbe.targets[7]==resolver,"resolver target replaced");cases++;
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
    public static void main(String[] args) {
        clean();acquisitionFailures();cleanupFailures();reentry();lateAndThreads();terminalsAndTargets();
        System.out.println("PASS " + cases + " production Observer host cases; faulting Android leaves only; native runtime pending");
    }
}
