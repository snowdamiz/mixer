package dev.mixer.android;

import android.app.Activity;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

/** Extends R45's reachable control using the unchanged R42 Android/JNI/renderer leaves. */
public final class DeadObserverControl {
    private static int checks;
    private static byte[] descriptor;
    private static final byte[] IDENTITY =
        "A34B0762-4A40-4FAA-A459-C4A16D2F0831".getBytes(StandardCharsets.UTF_8);
    private static final byte[] PACKET = ("{\"schemaVersion\":1,\"document\":{\"schemaVersion\":1,\"revision\":1,\"root\":{\"id\":\"button\",\"kind\":\"button\",\"properties\":{\"label\":\"Save\"},\"children\":[],\"actions\":[{\"id\":\"activate\",\"event\":\"activate\"}]}},\"identities\":[{\"id\":\"button\",\"generation\":1}]}").getBytes(StandardCharsets.UTF_8);

    private DeadObserverControl() {}

    private static void check(boolean condition, String why) {
        checks++;
        if (!condition) throw new AssertionError(why);
    }

    private static RuntimeException rejects(Runnable action) {
        checks++;
        try { action.run(); }
        catch (IllegalStateException expected) { return expected; }
        throw new AssertionError("expected cleanup rejection");
    }

    private static final class Fixture {
        final Activity activity = new Activity();
        final FrameLayout root = new FrameLayout(activity);
        final AndroidUINativeSurface surface;

        Fixture() {
            OwnerHostProbe.reset();
            NativeBridge.reset();
            activity.assets.put("MixerAppearanceV2/descriptor.json", descriptor);
            root.layout(0, 0, 1000, 1500);
            activity.window.getDecorView().layout(0, 0, 1000, 1500);
            root.hostAttach(new Object());
            surface = new AndroidUINativeSurface(activity, root,
                AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3, (owner, event) -> {});
        }

        NativeOwnerV2 owner() throws ReflectiveOperationException {
            Field field = AndroidUINativeSurface.class.getDeclaredField("nativeOwner");
            field.setAccessible(true);
            return (NativeOwnerV2) field.get(surface);
        }

        void install() {
            surface.activate(IDENTITY);
            surface.install(new AndroidUINativeSurface.Frame(IDENTITY, PACKET, descriptor));
            check(surface.isCurrent(), "setup did not install");
        }
    }

    private static int[] states(NativeEnvironmentV2.Observer observer) {
        int[] states = new int[8];
        for (int slot = 0; slot < states.length; slot++)
            states[slot] = observer.cleanupLedger().state(slot);
        return states;
    }

    private static void stableFailure(Fixture f, NativeOwnerV2 owner,
                                      NativeEnvironmentV2.Observer observer,
                                      RuntimeException failure) throws Exception {
        int[] retained = states(observer);
        int focusRemovals = f.root.treeObserver.removeCalls;
        int allEffects = OwnerHostProbe.events().size();
        // If a later close retries the dead focus target, it can now perform a removal.
        f.root.treeObserver.alive = true;
        check(rejects(f.surface::close) == failure, "repeat close replaced first failure");
        check(rejects(() -> f.surface.revoke(IDENTITY)) == failure,
            "repeat revoke replaced first failure");
        check(f.owner() == owner && owner.externalObserver() == observer,
            "terminal facade discarded owner or observer");
        check(!f.surface.isCurrent(), "failed close left surface current");
        check(f.root.treeObserver.removeCalls == focusRemovals &&
            OwnerHostProbe.events().size() == allEffects && Arrays.equals(states(observer), retained),
            "repeated close/revoke retried cleanup or changed retained outcomes");
        rejects(() -> f.surface.activate(IDENTITY));
        rejects(() -> f.surface.install(new AndroidUINativeSurface.Frame(IDENTITY, PACKET, descriptor)));
    }

    private static void deadObserver() throws Exception {
        Fixture f = new Fixture();
        f.install();
        NativeOwnerV2 owner = f.owner();
        NativeEnvironmentV2.Observer observer = owner.externalObserver();
        for (int state : states(observer))
            check(state == NativeEnvironmentV2.Observer.POSSIBLY_OWNED, "slot was not acquired");
        f.root.treeObserver.alive = false;
        RuntimeException failure = rejects(f.surface::close);
        NativeOwnerV2.CleanupLedger wrapper = owner.cleanupLedger();
        check(wrapper.unregister() == NativeOwnerV2.Outcome.RETURNED && wrapper.primary() == null,
            "R45 wrapper-returned/no-primary path changed");
        for (int slot = 0; slot < 8; slot++)
            check(observer.cleanupLedger().state(slot) == (slot == 3 ?
                NativeEnvironmentV2.Observer.DEAD_TARGET_UNCERTAIN : NativeEnvironmentV2.Observer.RETURNED),
                "unexpected dead-observer outcome for slot " + slot);
        check(failure.getMessage().equals("native surface cleanup failed or remains incomplete") &&
            failure.getCause() == null, "facade did not latch incomplete cleanup");
        stableFailure(f, owner, observer, failure);
        System.out.println("PASS R45 exact dead target: slot3=DEAD_TARGET_UNCERTAIN(5); wrapper unregister=RETURNED; primary=null; first close rejects; repeat close/revoke identical; owner retained; no removal retry");
    }

    private static void returnedObserver() throws Exception {
        Fixture f = new Fixture();
        f.install();
        NativeOwnerV2 owner = f.owner();
        NativeEnvironmentV2.Observer observer = owner.externalObserver();
        f.surface.close();
        for (int state : states(observer))
            check(state == NativeEnvironmentV2.Observer.RETURNED, "successful slot did not return");
        check(owner.cleanupLedger().primary() == null &&
            owner.cleanupLedger().unregister() == NativeOwnerV2.Outcome.RETURNED,
            "successful wrapper retained failure");
        int allEffects = OwnerHostProbe.events().size();
        int removals = f.root.treeObserver.removeCalls;
        f.surface.close();
        f.surface.revoke(IDENTITY);
        check(f.owner() == owner && !f.surface.isCurrent() && removals == 1 &&
            f.root.treeObserver.removeCalls == removals &&
            OwnerHostProbe.events().size() == allEffects, "successful cleanup repeated effects");
        System.out.println("PASS all eight removals RETURNED; close/revoke repeat without retry");
    }

    private static void unacquiredObserver() throws Exception {
        Fixture empty = new Fixture();
        int effects = OwnerHostProbe.events().size();
        empty.surface.close();
        empty.surface.close();
        check(empty.owner() == null && OwnerHostProbe.events().size() == effects,
            "unactivated close acquired resources");
        Fixture f = new Fixture();
        f.surface.activate(IDENTITY);
        NativeOwnerV2 owner = f.owner();
        check(owner.externalObserver() == null, "activation acquired observer before installation");
        f.surface.close();
        effects = OwnerHostProbe.events().size();
        f.surface.close();
        f.surface.revoke(IDENTITY);
        check(f.owner() == owner && owner.externalObserver() == null && !f.surface.isCurrent() &&
            f.root.treeObserver.addCalls == 0 && f.root.treeObserver.removeCalls == 0 &&
            OwnerHostProbe.events().size() == effects, "unacquired cleanup performed observer effects");
        System.out.println("PASS unactivated and activated/uninstalled lifetime: unacquired observer accepted");
    }

    private static void failedRemoval(int slot) throws Exception {
        Fixture f = new Fixture();
        f.install();
        NativeOwnerV2 owner = f.owner();
        NativeEnvironmentV2.Observer observer = owner.externalObserver();
        RuntimeException injected = new IllegalStateException("controlled removal slot " + slot);
        boolean[] fired = {false};
        OwnerHostProbe.hook = (method, phase) -> {
            if (!fired[0] && observer.cleanupLedger().state(slot) == NativeEnvironmentV2.Observer.REMOVING) {
                fired[0] = true;
                OwnerHostProbe.fail(injected);
            }
        };
        RuntimeException failure;
        try { failure = rejects(f.surface::close); }
        finally { OwnerHostProbe.hook = null; }
        check(fired[0] && observer.cleanupLedger().state(slot) == NativeEnvironmentV2.Observer.FAILED_UNCERTAIN,
            "failed removal path was not reached for slot " + slot);
        check(owner.cleanupLedger().primary() == injected && failure.getCause() == injected,
            "cleanup primary history changed for slot " + slot);
        stableFailure(f, owner, observer, failure);
        System.out.println("PASS failed removal slot=" + slot + "; primary retained; identical repeat close/revoke; no retry");
    }

    public static void main(String[] args) throws Exception {
        descriptor = Files.readAllBytes(Path.of(args[0]));
        returnedObserver();
        unacquiredObserver();
        deadObserver();
        for (int slot = 0; slot < 8; slot++) failedRemoval(slot);
        System.out.println("PASS observer settlement checks=" + checks + "; real R42 facade/owner/core/coordinator/observer; inert host leaves only");
    }
}
