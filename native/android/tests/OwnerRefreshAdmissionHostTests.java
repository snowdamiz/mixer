package dev.mixer.android;

import android.app.Activity;
import android.os.Handler;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

/** Actual owner/core/coordinator/observer with the unchanged R25 closure-A renderer leaf. */
public final class OwnerRefreshAdmissionHostTests {
    private static byte[] descriptor;
    private static int assertions, passed, failed;
    private static void check(boolean condition, String message) {
        assertions++;
        if (!condition) throw new AssertionError(message);
    }
    private static Object field(Object value, String name) {
        try { Field f=value.getClass().getDeclaredField(name); f.setAccessible(true); return f.get(value); }
        catch (ReflectiveOperationException failure) { throw new AssertionError(failure); }
    }
    private static byte[] packet() {
        return ("{\"schemaVersion\":1,\"document\":{\"schemaVersion\":1,\"revision\":1,\"root\":{\"id\":\"button\",\"kind\":\"button\",\"properties\":{\"label\":\"Immutable\"},\"children\":[],\"actions\":[{\"id\":\"activate\",\"event\":\"activate\"}]}},\"identities\":[{\"id\":\"button\",\"generation\":1}]}").getBytes(StandardCharsets.UTF_8);
    }
    private static final class Fixture implements AutoCloseable {
        final Activity activity=new Activity();
        final FrameLayout root=new FrameLayout(activity);
        final int[] deliveries={0};
        final ExternalFrameSourceV2 source=new ExternalFrameSourceV2(bytes -> deliveries[0]++);
        final NativeOwnerV2 owner;
        final Handler queue;
        final OwnerLifecycleV2 core;
        int baselineCaptures;
        Fixture() { this(true); }
        Fixture(boolean install) {
            OwnerHostProbe.reset(); NativeBridge.reset();
            activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);
            root.layout(0,0,1000,1500); activity.window.getDecorView().layout(0,0,1000,1500);
            root.hostAttach(new Object());
            owner=NativeOwnerV2.external(activity,root,source);
            queue=(Handler)field(owner,"handler"); core=(OwnerLifecycleV2)field(owner,"core");
            if (install) owner.installExternal(packet(),descriptor);
            else source.offer(packet(),descriptor);
            baselineCaptures=captures();
        }
        NativeOwnerV2.Fence fence() { return (NativeOwnerV2.Fence)field(owner,"fence"); }
        NativeCoordinatorV2 coordinator() { return (NativeCoordinatorV2)field(owner,"coordinator"); }
        NativeRenderer renderer() { return (NativeRenderer)field(coordinator(),"renderer"); }
        int captures() { return OwnerHostProbe.count("Renderer.captureInstalled","entry"); }
        void deferred() {
            check(captures()==baselineCaptures,"inadmissible native capture delta="+(captures()-baselineCaptures));
            check(core.snapshot().dirty() && core.snapshot().operation()==null,"deferred owner lost dirty state or began operation");
            check(queue.queued()==0 && core.snapshot().pendingDrain()==null,"deferred owner kept a poller/drain");
            check(!fence().inputAllowed && !fence().drawAllowed && !fence().terminal,"deferred gates/terminal incorrect");
            check(owner.cleanupLedger().primary()==null,"lifecycle created a primary failure");
        }
        void recovered() {
            check(queue.queued()==1,"recovery must schedule exactly one drain");
            queue.drainAll(3);
            check(captures()==baselineCaptures+1,"recovery did not perform exactly one refresh");
            check(owner.externalCurrent() && fence().inputAllowed,"recovery did not publish current presentation/input");
            check(owner.cleanupLedger().primary()==null,"recovery recorded failure");
        }
        @Override public void close() { OwnerHostProbe.hook=null; owner.close(); queue.drainAll(3); }
    }
    private static void run(String name, Runnable action) {
        try { action.run(); passed++; System.out.println("PASS "+name); }
        catch (AssertionError failure) { failed++; System.out.println("FAIL "+name+": "+failure.getMessage()); }
    }
    public static void main(String[] args) throws Exception {
        descriptor=Files.readAllBytes(Path.of(args[0]));
        run("paused-no-queued-work",()->{try(Fixture f=new Fixture()) {
            f.owner.onPause(); f.queue.drainAll(3); f.deferred();
        }});
        run("stopped-no-queued-work",()->{try(Fixture f=new Fixture()) {
            f.owner.onStop(); f.queue.drainAll(3); f.deferred();
        }});
        run("focus-loss-no-queued-work",()->{try(Fixture f=new Fixture()) {
            f.root.hostWindowFocus(false); f.queue.drainAll(3); f.deferred();
        }});
        run("pause-with-already-queued-drain",()->{try(Fixture f=new Fixture()) {
            f.owner.externalObserver().invalidate(); check(f.queue.queued()==1,"missing queued control");
            f.owner.onPause(); f.queue.drainAll(3); f.deferred();
        }});
        run("focus-loss-with-already-queued-drain",()->{try(Fixture f=new Fixture()) {
            f.owner.externalObserver().invalidate(); check(f.queue.queued()==1,"missing queued control");
            f.root.hostWindowFocus(false); f.queue.drainAll(3); f.deferred();
        }});
        run("fresh-focus-probe-at-delivery",()->{try(Fixture f=new Fixture()) {
            f.owner.externalObserver().invalidate(); f.root.windowFocus=false;
            f.queue.drainAll(3); f.deferred();
        }});
        run("focus-gain-while-paused-then-resume",()->{try(Fixture f=new Fixture()) {
            f.owner.onPause(); f.root.hostWindowFocus(false); f.queue.drainAll(3); f.deferred();
            f.root.hostWindowFocus(true); check(f.queue.queued()==0,"focus gain refreshed paused owner");
            f.owner.onResume(); f.recovered();
        }});
        run("resume-before-focus-gain",()->{try(Fixture f=new Fixture()) {
            f.owner.onPause(); f.root.hostWindowFocus(false); f.queue.drainAll(3); f.deferred();
            f.owner.onResume(); check(f.queue.queued()==0,"resume refreshed unfocused owner");
            f.root.hostWindowFocus(true); f.recovered();
        }});
        run("late-work-cannot-consume-successor",()->{try(Fixture f=new Fixture()) {
            f.owner.externalObserver().invalidate(); Runnable old=f.queue.snapshot().get(0);
            f.root.hostWindowFocus(false); f.queue.drainAll(3); f.deferred(); old.run(); f.deferred();
            f.root.hostWindowFocus(true); old.run(); f.recovered();
        }});
        run("close-while-deferred",()->{try(Fixture f=new Fixture()) {
            f.root.hostWindowFocus(false); f.queue.drainAll(3); f.deferred(); f.owner.close();
            check(f.captures()==f.baselineCaptures,"close refreshed deferred owner");
            check(f.owner.cleanupLedger().coordinator()==NativeOwnerV2.Outcome.RETURNED &&
                  f.owner.cleanupLedger().primary()==null,"deferred close hid cleanup failure");
            check(f.fence().terminal,"deferred close failed to retire");
        }});
        run("close-cancels-queued-drain-and-late-delivery",()->{try(Fixture f=new Fixture()) {
            f.owner.externalObserver().invalidate(); Runnable old=f.queue.snapshot().get(0);
            f.root.hostWindowFocus(false); f.owner.close(); old.run(); f.queue.drainAll(3);
            check(f.captures()==f.baselineCaptures && f.fence().terminal,"close/late work refreshed");
            check(f.owner.cleanupLedger().primary()==null,"close hid prior primary");
        }});
        run("immutable-packet-and-sealed-input-through-deferral",()->{try(Fixture f=new Fixture()) {
            Object committed=field(f.coordinator(),"committedPacket"); byte[] bytes=((byte[])committed).clone();
            byte[] envelope=UiPacket.decode(bytes).event("button","1","activate",null);
            f.owner.gateExternalInput(); f.root.hostWindowFocus(false); f.queue.drainAll(3); f.deferred();
            f.renderer().emit(envelope); check(f.deliveries[0]==0,"deferred input delivered");
            f.root.hostWindowFocus(true); f.queue.drainAll(3);
            check(f.owner.externalCurrent() && f.fence().drawAllowed && !f.fence().inputAllowed,"app input seal reopened with draw");
            check(field(f.coordinator(),"committedPacket")==committed && Arrays.equals(bytes,(byte[])committed) &&
                  f.renderer().preparedReference==committed,"committed packet identity/bytes changed");
            check(NativeBridge.createCalls==0 && NativeBridge.prepareCalls==0 && NativeBridge.commitCalls==0,
                  "environment refresh replayed presentation/business engine");
        }});
        run("genuine-operation-primary-retained",()->{try(Fixture f=new Fixture()) {
            RuntimeException expected=new IllegalStateException("eligible capture failure");
            OwnerHostProbe.hook=(method,at)->{if(method.equals("Renderer.captureInstalled") && at.equals("entry"))throw expected;};
            f.owner.externalObserver().invalidate(); f.queue.drainAll(3); OwnerHostProbe.hook=null;
            check(f.fence().terminal && f.owner.cleanupLedger().primary()==expected,"primary swallowed/replaced");
        }});
        run("foreign-window-remains-terminal-while-deferred",()->{try(Fixture f=new Fixture()) {
            f.root.hostWindowFocus(false); f.activity.window=new android.view.Window(f.activity);
            f.owner.externalObserver().invalidate();
            check(f.fence().terminal && f.core.snapshot().terminalReason()==OwnerLifecycleV2.Reason.WINDOW_LOST,
                  "admission bypassed window identity guard");
        }});
        run("initial-open-waits-for-foreground-and-focus",()->{try(Fixture f=new Fixture(false)) {
            f.root.windowFocus=false; f.owner.start(); f.queue.drainAll(3);
            check(f.captures()==0 && f.queue.queued()==0,"inactive initial open captured");
            f.owner.onResume(); check(f.queue.queued()==0,"initial resume ignored focus");
            f.root.hostWindowFocus(true); check(f.queue.queued()==1,"focused initial open missing");
            f.queue.drainAll(3); check(f.owner.hasCommittedPresentation(),"initial open did not complete");
        }});
        System.out.println("RESULT passed="+passed+" failed="+failed+" assertions="+assertions);
        if(failed!=0) System.exit(1);
    }
}
