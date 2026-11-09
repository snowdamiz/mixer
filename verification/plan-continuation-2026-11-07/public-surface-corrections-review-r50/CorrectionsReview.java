package dev.mixer.android;

import android.app.Activity;
import android.os.Handler;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

/** Independent bounded review; actual facade/owner/core/observer, existing host leaves. */
public final class CorrectionsReview {
    private static int checks;
    private static byte[] descriptor;
    private static final byte[] ID = "independent-r50".getBytes(StandardCharsets.UTF_8);
    private static final byte[] PACKET = ("{\"schemaVersion\":1,\"document\":{\"schemaVersion\":1,\"revision\":1,\"root\":{\"id\":\"button\",\"kind\":\"button\",\"properties\":{\"label\":\"Save\"},\"children\":[],\"actions\":[{\"id\":\"activate\",\"event\":\"activate\"}]}},\"identities\":[{\"id\":\"button\",\"generation\":1}]}").getBytes(StandardCharsets.UTF_8);
    private CorrectionsReview() {}
    private static void check(boolean yes, String why) {
        checks++;
        if (!yes) throw new AssertionError(why);
    }
    private static Object field(Object target, String name) throws ReflectiveOperationException {
        Field f = target.getClass().getDeclaredField(name);
        f.setAccessible(true);
        return f.get(target);
    }
    private static void set(Object target, String name, Object value) throws ReflectiveOperationException {
        Field f = target.getClass().getDeclaredField(name);
        f.setAccessible(true);
        f.set(target, value);
    }
    private static Throwable rejection(Runnable action) {
        try { action.run(); }
        catch (RuntimeException | Error expected) { checks++; return expected; }
        throw new AssertionError("expected rejection");
    }
    private static final class Fixture {
        final Activity activity = new Activity();
        final FrameLayout root = new FrameLayout(activity);
        final AndroidUINativeSurface surface;
        Fixture(boolean install) {
            OwnerHostProbe.reset(); NativeBridge.reset();
            activity.assets.put("MixerAppearanceV2/descriptor.json", descriptor);
            root.layout(0, 0, 1000, 1500);
            activity.window.getDecorView().layout(0, 0, 1000, 1500);
            root.hostAttach(new Object());
            surface = new AndroidUINativeSurface(activity, root,
                AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3, (owner, envelope) -> {});
            surface.activate(ID);
            if (install) surface.install(new AndroidUINativeSurface.Frame(ID, PACKET, descriptor));
        }
        NativeOwnerV2 owner() throws ReflectiveOperationException { return (NativeOwnerV2) field(surface, "nativeOwner"); }
        NativeEnvironmentV2.Observer observer() throws ReflectiveOperationException { return owner().externalObserver(); }
        Handler queue() throws ReflectiveOperationException { return (Handler) field(owner(), "handler"); }
        OwnerLifecycleV2 core() throws ReflectiveOperationException { return (OwnerLifecycleV2) field(owner(), "core"); }
        NativeOwnerV2.Fence fence() throws ReflectiveOperationException { return (NativeOwnerV2.Fence) field(owner(), "fence"); }
        Object coordinator() throws ReflectiveOperationException { return field(owner(), "coordinator"); }
        int captures() { return OwnerHostProbe.count("Renderer.captureInstalled", "entry"); }
        int[] states() throws ReflectiveOperationException {
            int[] states = new int[8];
            for (int i = 0; i < 8; i++) states[i] = observer().cleanupLedger().state(i);
            return states;
        }
    }
    private static void sticky(Fixture f, Throwable first) throws Exception {
        NativeOwnerV2 owner = f.owner();
        NativeEnvironmentV2.Observer observer = f.observer();
        int[] states = f.states();
        int effects = OwnerHostProbe.events().size();
        int removals = f.root.treeObserver.removeCalls;
        f.root.treeObserver.alive = true;
        check(rejection(f.surface::close) == first, "repeat close changed failure identity");
        check(rejection(() -> f.surface.revoke(ID)) == first, "revoke changed failure identity");
        f.surface.onResume(); f.surface.onPause(); f.surface.onStop();
        check(f.owner() == owner && f.observer() == observer, "terminal close discarded owner");
        check(!f.surface.isCurrent() && f.fence().terminal, "failed close not terminal");
        check(f.root.treeObserver.removeCalls == removals && OwnerHostProbe.events().size() == effects,
            "repeat close/lifecycle performed native cleanup again");
        check(Arrays.equals(states, f.states()), "repeat changed retained observer ledger");
        rejection(() -> f.surface.activate(ID));
        rejection(() -> f.surface.install(new AndroidUINativeSurface.Frame(ID, PACKET, descriptor)));
    }
    private static void deadTarget() throws Exception {
        Fixture f = new Fixture(true);
        f.root.treeObserver.alive = false;
        Throwable first = rejection(f.surface::close);
        check(f.owner().cleanupLedger().primary() == null &&
            f.owner().cleanupLedger().unregister() == NativeOwnerV2.Outcome.RETURNED,
            "dead-target baseline path no longer distinguishes nested settlement");
        for (int i = 0; i < 8; i++) check(f.states()[i] == (i == 3 ?
            NativeEnvironmentV2.Observer.DEAD_TARGET_UNCERTAIN : NativeEnvironmentV2.Observer.RETURNED),
            "dead target unexpected slot " + i);
        sticky(f, first);
        System.out.println("PASS reachable dead-target uncertainty; same retained failure; no retry");
    }
    private static void removalFailures() throws Exception {
        for (int slot = 0; slot < 8; slot++) {
            Fixture f = new Fixture(true);
            NativeEnvironmentV2.Observer observer = f.observer();
            final int target = slot;
            RuntimeException original = new IllegalStateException("r50 removal " + slot);
            boolean[] fired = {false};
            OwnerHostProbe.hook = (method, phase) -> {
                if (!fired[0] && observer.cleanupLedger().state(target) == NativeEnvironmentV2.Observer.REMOVING) {
                    fired[0] = true; throw original;
                }
            };
            Throwable first;
            try { first = rejection(f.surface::close); }
            finally { OwnerHostProbe.hook = null; }
            check(fired[0] && observer.cleanupLedger().state(slot) == NativeEnvironmentV2.Observer.FAILED_UNCERTAIN,
                "did not exercise uncertain removal slot " + slot);
            check(f.owner().cleanupLedger().primary() == original && first.getCause() == original,
                "cleanup primary lost for slot " + slot);
            sticky(f, first);
        }
        Fixture fatal = new Fixture(true);
        NativeEnvironmentV2.Observer observer = fatal.observer();
        Error original = new AssertionError("r50 fatal removal");
        boolean[] fired = {false};
        OwnerHostProbe.hook = (method, phase) -> {
            if (!fired[0] && observer.cleanupLedger().state(7) == NativeEnvironmentV2.Observer.REMOVING) {
                fired[0] = true; throw original;
            }
        };
        Throwable first;
        try { first = rejection(fatal.surface::close); }
        finally { OwnerHostProbe.hook = null; }
        check(fired[0] && first == original && observer.cleanupLedger().firstFatal() == original,
            "fatal cleanup error replaced");
        sticky(fatal, first);
        System.out.println("PASS all eight reachable failed removals and fatal Error identity");
    }
    private static void settlementMatrix() throws Exception {
        Fixture f = new Fixture(true);
        f.surface.close();
        for (int state : f.states()) check(state == NativeEnvironmentV2.Observer.RETURNED, "success did not return all slots");
        int effects = OwnerHostProbe.events().size();
        f.surface.close(); f.surface.revoke(ID);
        check(effects == OwnerHostProbe.events().size(), "success repeated cleanup");
        NativeEnvironmentV2.Observer observer = f.observer();
        Method settled = AndroidUINativeSurface.class.getDeclaredMethod("observerSettled", NativeEnvironmentV2.Observer.class);
        settled.setAccessible(true);
        int[] ledger = (int[]) field(observer, "cleanup");
        // Direct predicate policy controls, separate from naturally reached teardown above.
        for (int slot = 0; slot < 8; slot++) {
            for (int state : new int[]{0, 1, 2, 3, 4, 5, -1, 99}) {
                ledger[slot] = state;
                check((boolean) settled.invoke(null, observer) == (state == 0 || state == 3),
                    "settlement policy accepted uncertain/unknown state slot=" + slot + " state=" + state);
            }
            ledger[slot] = NativeEnvironmentV2.Observer.RETURNED;
        }
        RuntimeException primary = new IllegalStateException("predicate primary");
        set(observer, "primaryFailure", primary);
        check(!(boolean) settled.invoke(null, observer), "settled ledger primary accepted");
        set(observer, "primaryFailure", null);
        set(observer, "fatalFailure", new AssertionError("predicate fatal"));
        check(!(boolean) settled.invoke(null, observer), "settled ledger fatal accepted");
        set(observer, "fatalFailure", null);
        Fixture unacquired = new Fixture(false);
        check(unacquired.observer() == null, "activate acquired an observer");
        unacquired.surface.close(); unacquired.surface.close(); unacquired.surface.revoke(ID);
        check(unacquired.observer() == null && unacquired.root.treeObserver.addCalls == 0,
            "unacquired success performed registration");
        System.out.println("PASS 8-slot x 8-state settlement policy, primary/fatal rejection, unacquired/allRETURNED success");
    }
    private static void deferred(Fixture f, int captures, Object packet, byte[] bytes) throws Exception {
        check(f.captures() == captures, "inadmissible native capture delta=" + (f.captures() - captures));
        OwnerLifecycleV2.Snapshot state = f.core().snapshot();
        check(state.dirty() && state.operation() == null && state.pendingDrain() == null && f.queue().queued() == 0,
            "deferral lost dirty state, started operation or retained poller");
        check(!f.fence().terminal && !f.fence().inputAllowed && !f.fence().drawAllowed,
            "deferred owner relaxed gates or retired");
        check(field(f.coordinator(), "committedPacket") == packet && Arrays.equals(bytes, (byte[]) packet),
            "deferral changed committed frame identity/bytes");
        check(f.owner().cleanupLedger().primary() == null, "deferral invented a primary");
    }
    private static void lifecycle(String mode, boolean focusFirst, boolean closeDeferred) throws Exception {
        Fixture f = new Fixture(true);
        int captures = f.captures();
        Object packet = field(f.coordinator(), "committedPacket");
        byte[] bytes = ((byte[]) packet).clone();
        f.observer().invalidate();
        check(f.queue().queued() == 1, "control missing queued drain");
        Runnable old = f.queue().snapshot().get(0);
        switch (mode) {
            case "focus" -> f.root.hostWindowFocus(false);
            case "silent-focus" -> f.root.windowFocus = false;
            case "pause" -> f.surface.onPause();
            case "stop" -> f.surface.onStop();
            default -> throw new AssertionError(mode);
        }
        f.queue().drainAll(3);
        deferred(f, captures, packet, bytes);
        old.run(); deferred(f, captures, packet, bytes);
        if (closeDeferred) {
            f.surface.close();
            int effects = OwnerHostProbe.events().size();
            f.surface.close(); f.surface.revoke(ID); old.run(); f.queue().drainAll(3);
            check(f.captures() == captures && f.fence().terminal && !f.surface.isCurrent(), "deferred close refreshed/revived");
            check(OwnerHostProbe.events().size() == effects, "deferred terminal repeated side effects");
            for (int state : f.states()) check(state == NativeEnvironmentV2.Observer.RETURNED, "deferred close incomplete");
        } else {
            f.surface.onPause(); f.root.hostWindowFocus(false);
            if (focusFirst) {
                f.root.hostWindowFocus(true);
                check(f.queue().queued() == 0, "focus gain refreshed paused owner");
                f.surface.onResume();
            } else {
                f.surface.onResume();
                check(f.queue().queued() == 0, "resume refreshed unfocused owner");
                f.root.hostWindowFocus(true);
            }
            check(f.queue().queued() == 1, "recovery did not coalesce one drain");
            old.run(); check(f.queue().queued() == 1, "old work consumed successor drain");
            f.queue().drainAll(3);
            check(f.captures() == captures + 1 && f.surface.isCurrent(), "recovery did not commit exactly one refresh");
            check(field(f.coordinator(), "committedPacket") == packet && Arrays.equals(bytes, (byte[]) packet),
                "recovery replayed frame");
            check(NativeBridge.createCalls == 0 && NativeBridge.prepareCalls == 0 && NativeBridge.commitCalls == 0,
                "refresh replayed engine presentation");
            f.surface.close();
        }
        System.out.println("PASS queued " + mode + (closeDeferred ? " terminal close" : " recovery focusFirst=" + focusFirst));
    }
    private static void primaryFailure() throws Exception {
        Fixture f = new Fixture(true);
        RuntimeException original = new IllegalStateException("r50 genuine admissible capture failure");
        OwnerHostProbe.hook = (method, phase) -> {
            if (method.equals("Renderer.captureInstalled") && phase.equals("entry")) throw original;
        };
        try { f.observer().invalidate(); f.queue().drainAll(3); }
        finally { OwnerHostProbe.hook = null; }
        check(f.fence().terminal && f.owner().cleanupLedger().primary() == original, "genuine capture failure swallowed");
        Throwable first = rejection(f.surface::close);
        check(first.getCause() == original, "facade replaced genuine primary");
        sticky(f, first);
        System.out.println("PASS genuine admissible capture primary retained through facade close");
    }
    private static void legacyPolicy() {
        Object activity = new Object(), root = new Object(), window = new Object();
        OwnerLifecycleV2.WindowFacts facts = new OwnerLifecycleV2.WindowFacts(activity, root, false, true, window, 100, 100, true);
        OwnerLifecycleV2 legacy = new OwnerLifecycleV2(() -> {}, activity, root);
        check(legacy.windowChanged(legacy.lifetime(), facts).stream().anyMatch(d -> d.kind() == OwnerLifecycleV2.Kind.QUEUE_DRAIN),
            "legacy constructor admission changed");
        OwnerLifecycleV2 strict = new OwnerLifecycleV2(() -> {}, activity, root, true);
        check(strict.windowChanged(strict.lifetime(), facts).isEmpty(), "V3 initial schedule ignored foreground/focus");
        strict.resume(strict.lifetime());
        check(strict.snapshot().pendingDrain() == null, "V3 resume without focus queued initial open");
        strict.focusChanged(strict.lifetime(), true);
        OwnerLifecycleV2.Token queued = strict.snapshot().pendingDrain();
        check(queued != null, "V3 initial recovery missing drain");
        strict.pause(strict.lifetime());
        check(strict.drain(strict.lifetime(), queued, facts).isEmpty() && strict.snapshot().operation() == null,
            "V3 initial queued drain ignored pause");
        System.out.println("PASS legacy constructor policy and V3 initial schedule/drain admission");
    }
    public static void main(String[] args) throws Exception {
        descriptor = Files.readAllBytes(Path.of(args[0]));
        String mode = args.length > 1 ? args[1] : "candidate";
        if (mode.equals("baseline-observer")) { deadTarget(); return; }
        if (mode.equals("baseline-focus")) { lifecycle("focus", true, false); return; }
        System.out.println("loaded facade=" + AndroidUINativeSurface.class.getProtectionDomain().getCodeSource().getLocation());
        System.out.println("loaded owner=" + NativeOwnerV2.class.getProtectionDomain().getCodeSource().getLocation());
        System.out.println("loaded core=" + OwnerLifecycleV2.class.getProtectionDomain().getCodeSource().getLocation());
        settlementMatrix(); deadTarget(); removalFailures();
        for (String event : new String[]{"focus", "silent-focus", "pause", "stop"}) {
            lifecycle(event, true, false); lifecycle(event, false, false); lifecycle(event, true, true);
        }
        primaryFailure(); legacyPolicy();
        System.out.println("PASS independent combined correction assertions=" + checks);
    }
}
