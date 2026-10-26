package dev.mixer.android;

import android.app.Activity;
import android.content.ContentResolver;
import android.content.res.Configuration;
import android.os.Build;
import android.os.Looper;
import android.view.View;
import android.view.ViewTreeObserver;
import android.view.WindowInsets;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.IdentityHashMap;
import java.util.List;

/** Assertions authored before candidate access; compiles the actual admitted observer. */
public final class ObserverIndependentHostTests {
    private ObserverIndependentHostTests() { }
    private static int cases;
    private static int assertions;
    private static List<String> cleanupOrder;
    private record Callback(String name, Runnable action) { }
    private static final class InjectedError extends Error {
        private static final long serialVersionUID = 1L;
        InjectedError(String message) { super(message); }
    }
    private static final class QuietFailure extends RuntimeException {
        private static final long serialVersionUID = 1L;
        QuietFailure() { super("independent suppression-disabled primary", null, false, false); }
    }
    private static final class Fixture {
        final Activity activity = new Activity();
        final FrameLayout root = new FrameLayout(activity);
        final NativeRenderer owner = new NativeRenderer();
        final ViewTreeObserver acquiredTree = root.tree;
        final ContentResolver acquiredResolver = activity.resolver;
        NativeEnvironmentV2.Observer observer;
        NativeEnvironmentV2 capture;
        void construct() { observer = new NativeEnvironmentV2.Observer(owner, activity, root); }
        NativeEnvironmentV2.Observer seen() {
            check(activity.savedComponent instanceof NativeEnvironmentV2.Observer, "actual Observer supplied to component leaf");
            return (NativeEnvironmentV2.Observer) activity.savedComponent;
        }
    }
    private static Fixture fresh(boolean construct) {
        IndependentFaults.reset(); Looper.setMain(true); Build.VERSION.SDK_INT = 36;
        Fixture fixture = new Fixture();
        if (construct) fixture.construct();
        return fixture;
    }
    private static void check(boolean condition, String message) {
        assertions++;
        if (!condition) throw new AssertionError(message + "; trace=" + IndependentFaults.events);
    }
    private static Throwable failure(Runnable action) {
        try { action.run(); return null; }
        catch (RuntimeException | Error thrown) {
            if (thrown instanceof AssertionError assertion) throw assertion;
            return thrown;
        }
    }
    private static void run(String id, Runnable action) {
        action.run(); cases++; System.out.println("PASS " + id);
    }
    private static Object field(NativeEnvironmentV2.Observer observer, String name) {
        try {
            Field selected = NativeEnvironmentV2.Observer.class.getDeclaredField(name);
            selected.setAccessible(true); return selected.get(observer);
        } catch (ReflectiveOperationException problem) { throw new AssertionError("old-source test setup field " + name, problem); }
    }
    private static long generation(NativeEnvironmentV2.Observer observer) { return (Long) field(observer, "generation"); }
    private static void generation(NativeEnvironmentV2.Observer observer, long value) {
        try {
            Field selected = NativeEnvironmentV2.Observer.class.getDeclaredField("generation");
            selected.setAccessible(true); selected.setLong(observer, value);
        } catch (ReflectiveOperationException problem) { throw new AssertionError(problem); }
    }
    private static void detach(Fixture fixture) {
        ((View.OnAttachStateChangeListener) field(fixture.seen(), "attachment")).onViewDetachedFromWindow(fixture.root);
    }
    private static void rejectedCapture(Fixture fixture) {
        Throwable thrown = failure(() -> fixture.seen().capture());
        check(thrown instanceof RuntimeException, "terminal or partially registered observer cannot publish a capture");
        if (fixture.capture != null) check(!fixture.capture.current(fixture.owner), "retired old capture is not current");
    }
    private static void attempts(int lastSlot, boolean deadTree) {
        for (int i = 0; i < IndependentFaults.SLOTS.size(); i++) {
            String slot = IndependentFaults.SLOTS.get(i);
            long expected = i <= lastSlot && !(deadTree && slot.equals("window-focus")) ? 1 : 0;
            check(IndependentFaults.count("remove.enter", slot) == expected, "one cleanup disposition for eligible slot " + slot);
            check(IndependentFaults.count("add.enter", slot) == (i <= lastSlot ? 1 : 0), "no add beyond acquired/uncertain prefix " + slot);
        }
    }
    private static void noRetry(Fixture fixture) {
        int before = IndependentFaults.events.size();
        failure(() -> fixture.seen().close());
        check(IndependentFaults.events.size() == before, "repeated close never retries consumed cleanup slots");
    }
    private static List<String> removalOrder() {
        List<String> result = new ArrayList<>();
        for (IndependentFaults.Event event : IndependentFaults.events)
            if (event.kind().equals("remove.enter")) result.add(event.slot());
        return result;
    }
    private static void projectedOrder(int last) {
        List<String> expected = cleanupOrder.stream().filter(s -> IndependentFaults.SLOTS.indexOf(s) <= last).toList();
        check(removalOrder().equals(expected), "eligible cleanup projection is deterministic");
    }
    private static List<Callback> callbacks(Fixture fixture) {
        NativeEnvironmentV2.Observer observer = fixture.seen();
        List<Callback> result = new ArrayList<>();
        result.add(new Callback("configuration", () -> observer.onConfigurationChanged(new Configuration())));
        result.add(new Callback("low-memory", observer::onLowMemory));
        if (fixture.root.savedLayout != null) {
            result.add(new Callback("layout-changed", () -> fixture.root.savedLayout.onLayoutChange(fixture.root, 0, 0, 8, 8, 0, 0, 4, 4)));
            result.add(new Callback("layout-unchanged", () -> fixture.root.savedLayout.onLayoutChange(fixture.root, 0, 0, 8, 8, 0, 0, 8, 8)));
        }
        if (fixture.root.savedAttach != null) {
            result.add(new Callback("attached", () -> fixture.root.savedAttach.onViewAttachedToWindow(fixture.root)));
            result.add(new Callback("detached", () -> fixture.root.savedAttach.onViewDetachedFromWindow(fixture.root)));
        }
        if (fixture.acquiredTree.savedFocus != null)
            result.add(new Callback("focus", () -> fixture.acquiredTree.savedFocus.onWindowFocusChanged(true)));
        if (fixture.root.savedInsets != null) result.add(new Callback("insets", () -> {
            WindowInsets exact = fixture.root.insets;
            check(fixture.root.savedInsets.onApplyWindowInsets(fixture.root, exact) == exact, "insets callback returns exact received object");
        }));
        if (fixture.activity.modes.savedContrast != null)
            result.add(new Callback("contrast", () -> fixture.activity.modes.savedContrast.onContrastChanged(0)));
        if (fixture.activity.accessibility.savedHighContrast != null)
            result.add(new Callback("high-contrast", () -> fixture.activity.accessibility.savedHighContrast.onHighContrastTextStateChanged(false)));
        if (fixture.acquiredResolver.savedObserver != null)
            result.add(new Callback("animator-settings", () -> fixture.acquiredResolver.savedObserver.onChange(false)));
        return result;
    }
    private static void lateCallbacks(Fixture fixture) {
        int notifications = fixture.owner.notifications;
        int reads = IndependentFaults.reads;
        int events = IndependentFaults.events.size();
        long epoch = generation(fixture.seen());
        for (Callback callback : callbacks(fixture)) {
            check(failure(callback.action()) == null, "retired callback returns normally " + callback.name());
            check(fixture.owner.notifications == notifications, "retired callback cannot call renderer " + callback.name());
            check(IndependentFaults.reads == reads, "retired callback cannot read tuple " + callback.name());
            check(generation(fixture.seen()) == epoch, "retired callback cannot advance epoch " + callback.name());
            check(IndependentFaults.events.size() == events, "retired callback cannot add/remove listeners " + callback.name());
        }
    }
    private static boolean failureGraphContains(Throwable root, Throwable expected) {
        return graph(root, expected, new IdentityHashMap<>());
    }
    private static boolean graph(Throwable root, Throwable expected, IdentityHashMap<Throwable, Boolean> seen) {
        if (root == null || seen.put(root, Boolean.TRUE) != null) return false;
        if (root == expected) return true;
        check(seen.size() <= 32, "bounded failure graph");
        if (graph(root.getCause(), expected, seen)) return true;
        for (Throwable suppressed : root.getSuppressed()) if (graph(suppressed, expected, seen)) return true;
        return false;
    }

    private static void clean() {
        Fixture fixture = fresh(true);
        for (String slot : IndependentFaults.SLOTS) check(IndependentFaults.active(slot) == 1, "one successful acquisition " + slot);
        check(fixture.owner.notifications == 0, "registration alone does not invent notification");
        fixture.capture = fixture.observer.capture();
        check(fixture.capture.current(fixture.owner), "clean actual capture is current");
        check(!fixture.capture.current(new Object()), "capture rejects foreign owner");
        fixture.activity.resources.configuration.uiMode = Configuration.UI_MODE_NIGHT_YES;
        check(!fixture.capture.current(fixture.owner), "second synchronous tuple read catches change without callback");
        fixture.activity.resources.configuration.uiMode = 0;
        fixture.observer.invalidate();
        check(!fixture.capture.current(fixture.owner), "generation invalidates old capture");
        fixture.capture = fixture.observer.capture();
        check(fixture.capture.current(fixture.owner), "new complete capture succeeds");
        fixture.root.token = new Object();
        check(!fixture.capture.current(fixture.owner), "changed window token rejects capture");
        fixture.observer.close(); attempts(7, false);
        check(IndependentFaults.active.isEmpty(), "effective clean removals empty modeled platform registry");
        check(fixture.root.currentInsets == null, "dedicated owned inset setter cleared");
        cleanupOrder = removalOrder();
        check(cleanupOrder.size() == 8 && cleanupOrder.stream().distinct().count() == 8, "clean full deterministic removal permutation");
        rejectedCapture(fixture); lateCallbacks(fixture); noRetry(fixture);
    }
    private static void addFault(int index, String phase, boolean fatal) {
        Fixture fixture = fresh(false);
        String slot = IndependentFaults.SLOTS.get(index);
        Throwable injected = fatal ? new InjectedError("add " + slot + phase) : new IllegalArgumentException("add " + slot + phase);
        IndependentFaults.addFaultSlot = slot; IndependentFaults.addFaultPhase = phase; IndependentFaults.addFault = injected;
        Throwable thrown = failure(fixture::construct);
        check(thrown == injected, "original acquisition failure identity preserved");
        check(fixture.observer == null, "failed constructor not published");
        attempts(index, false); projectedOrder(index);
        check(IndependentFaults.active.isEmpty(), "prefix and uncertain slot rolled back");
        rejectedCapture(fixture); lateCallbacks(fixture); noRetry(fixture);
    }
    private static void addReentry(int index, String phase, boolean detach, boolean throwAfter) {
        Fixture fixture = fresh(false);
        String slot = IndependentFaults.SLOTS.get(index);
        IndependentFaults.addHookSlot = slot; IndependentFaults.addHookPhase = phase;
        IndependentFaults.addHook = () -> {
            if (detach) detach(fixture); else fixture.seen().close();
            rejectedCapture(fixture);
        };
        if (throwAfter) {
            IndependentFaults.addFaultSlot = slot; IndependentFaults.addFaultPhase = "after";
            IndependentFaults.addFault = new IllegalArgumentException("add settles with failure");
        }
        Throwable thrown = failure(fixture::construct);
        check(thrown instanceof RuntimeException, "terminal add reentry must unwind construction");
        check(fixture.observer == null, "terminal reentry cannot publish constructor result");
        check(IndependentFaults.addHookFired, "intended acquisition hook reached");
        attempts(index, false);
        check(IndependentFaults.active.isEmpty(), "resumed acquisition is covered by final disposal");
        check(IndependentFaults.position("remove.effect", slot) > IndependentFaults.position("add.acquire", slot),
            "active add settles before its effective final removal");
        rejectedCapture(fixture); lateCallbacks(fixture); noRetry(fixture);
    }
    private static void constructionNotification(String callbackName) {
        Fixture fixture = fresh(false);
        IndependentFaults.addHookSlot = "animator-settings"; IndependentFaults.addHookPhase = "after";
        fixture.owner.invalidationHook = () -> rejectedCapture(fixture);
        IndependentFaults.addHook = () -> {
            Callback selected = callbacks(fixture).stream().filter(c -> c.name().equals(callbackName)).findFirst().orElseThrow();
            selected.action().run();
            check(fixture.owner.notifications == 1, "partial notification synchronously reaches existing gate invalidation");
        };
        fixture.construct();
        check(fixture.owner.notifications == 1, "no deferred notification replay after construction");
        fixture.owner.invalidationHook = null;
        check(fixture.observer.capture().current(fixture.owner), "completed observer capture works after construction notification");
        fixture.observer.close(); attempts(7, false);
    }
    private static void retirementFirst(boolean detach, boolean invalidationFatal) {
        Fixture fixture = fresh(true); fixture.capture = fixture.observer.capture();
        InjectedError injected = new InjectedError("renderer invalidation");
        fixture.owner.invalidationHook = () -> { rejectedCapture(fixture); if (invalidationFatal) throw injected; };
        IndependentFaults.removeHookSlot = cleanupOrder.get(0); IndependentFaults.removeHookPhase = "before";
        IndependentFaults.removeHook = () -> { rejectedCapture(fixture); fixture.seen().close(); };
        Throwable thrown = failure(() -> { if (detach) detach(fixture); else fixture.observer.close(); });
        if (invalidationFatal) check(thrown == injected, "renderer Error escapes after independent cleanup");
        else check(thrown == null, "clean first retirement succeeds");
        if (detach) check(fixture.owner.notifications == 1, "first detach synchronously invalidates old gates exactly once");
        attempts(7, false); check(IndependentFaults.active.isEmpty(), "first retirement completes eligible cleanup");
        rejectedCapture(fixture); lateCallbacks(fixture); noRetry(fixture);
    }
    private static void wrongThread(boolean retired) {
        Fixture fixture = fresh(true); fixture.capture = fixture.observer.capture();
        if (retired) fixture.observer.close();
        List<Callback> entries = new ArrayList<>(callbacks(fixture));
        entries.add(new Callback("close", fixture.observer::close));
        entries.add(new Callback("read", () -> fixture.observer.read()));
        entries.add(new Callback("capture", () -> fixture.observer.capture()));
        entries.add(new Callback("current", () -> fixture.capture.current(fixture.owner)));
        entries.add(new Callback("invalidate", fixture.observer::invalidate));
        int notifications = fixture.owner.notifications, reads = IndependentFaults.reads, events = IndependentFaults.events.size();
        long epoch = generation(fixture.observer);
        Looper.setMain(false);
        try {
            for (Callback entry : entries) {
                check(failure(entry.action()) instanceof IllegalStateException, "actual main-Looper assertion first: " + entry.name());
                check(fixture.owner.notifications == notifications && IndependentFaults.reads == reads &&
                    IndependentFaults.events.size() == events && generation(fixture.observer) == epoch,
                    "wrong-thread entry has no effects: " + entry.name());
            }
        } finally { Looper.setMain(true); }
        if (!retired) fixture.observer.close();
    }
    private static void wrongThreadAfterOtherTerminal(boolean constructorFailure) {
        Fixture fixture = fresh(!constructorFailure);
        if (constructorFailure) {
            IndependentFaults.addFaultSlot = "animator-settings"; IndependentFaults.addFaultPhase = "after";
            IndependentFaults.addFault = new IllegalStateException("terminal constructor fixture");
            check(failure(fixture::construct) == IndependentFaults.addFault, "intended constructor failure reached");
        } else detach(fixture);
        NativeEnvironmentV2.Observer observed = fixture.seen();
        List<Callback> entries = new ArrayList<>(callbacks(fixture));
        entries.add(new Callback("close", observed::close));
        entries.add(new Callback("read", () -> observed.read()));
        entries.add(new Callback("capture", () -> observed.capture()));
        entries.add(new Callback("invalidate", observed::invalidate));
        int notifications = fixture.owner.notifications, reads = IndependentFaults.reads, events = IndependentFaults.events.size();
        long epoch = generation(observed);
        Looper.setMain(false);
        try {
            for (Callback entry : entries) {
                check(failure(entry.action()) instanceof IllegalStateException, "terminal-origin thread guard first: " + entry.name());
                check(fixture.owner.notifications == notifications && IndependentFaults.reads == reads &&
                    IndependentFaults.events.size() == events && generation(observed) == epoch,
                    "terminal-origin wrong-thread entry has no effects: " + entry.name());
            }
        } finally { Looper.setMain(true); }
        noRetry(fixture);
    }
    private static void exhaustion() {
        Fixture fixture = fresh(true); fixture.capture = fixture.observer.capture();
        generation(fixture.observer, Long.MAX_VALUE - 1); fixture.observer.invalidate();
        check(generation(fixture.observer) == Long.MAX_VALUE, "last unique generation does not wrap");
        fixture.owner.invalidationHook = () -> rejectedCapture(fixture);
        fixture.observer.invalidate();
        check(generation(fixture.observer) == Long.MAX_VALUE, "exhausted generation never wraps");
        attempts(7, false); rejectedCapture(fixture); lateCallbacks(fixture); noRetry(fixture);
    }
    private static void removalFault(int index, boolean fatal, boolean afterEffect, boolean primaryOrdinary) {
        Fixture fixture = fresh(!primaryOrdinary);
        String slot = IndependentFaults.SLOTS.get(index);
        Throwable injected = fatal ? new InjectedError("cleanup " + slot) : new IllegalArgumentException("cleanup " + slot);
        IndependentFaults.removeFaults.put(slot, injected); IndependentFaults.failRemovalAfterEffect = afterEffect;
        RuntimeException primary = new IllegalStateException("original acquisition");
        Throwable thrown;
        if (primaryOrdinary) {
            IndependentFaults.addFaultSlot = "animator-settings"; IndependentFaults.addFaultPhase = "after"; IndependentFaults.addFault = primary;
            thrown = failure(fixture::construct);
        } else thrown = failure(fixture.observer::close);
        if (fatal) check(thrown == injected, "cleanup Error escapes including ordinary acquisition primary");
        else check(thrown == (primaryOrdinary ? primary : injected), "ordinary primary identity preserved");
        if (primaryOrdinary) check(failureGraphContains(thrown, primary), "original ordinary primary retained in failure graph");
        check(failureGraphContains(thrown, injected), "cleanup diagnostic retained in failure graph");
        attempts(7, false); projectedOrder(7);
        check(IndependentFaults.active.size() == (afterEffect ? 0 : 1), "modeled removal outcome retains uncertainty precisely");
        rejectedCapture(fixture); lateCallbacks(fixture); noRetry(fixture);
    }
    private static void combinedRemoval(boolean withFatal, boolean primaryFatal, boolean quiet, boolean sameThrowable) {
        Fixture fixture = fresh(false);
        Throwable primary = primaryFatal ? new InjectedError("primary Error") : quiet ? new QuietFailure() : new IllegalStateException("primary ordinary");
        IndependentFaults.addFaultSlot = "animator-settings"; IndependentFaults.addFaultPhase = "after"; IndependentFaults.addFault = primary;
        List<Throwable> cleanup = new ArrayList<>();
        for (int i = 0; i < 8; i++) {
            Throwable next = sameThrowable ? primary : withFatal && i == 3 ? new InjectedError("combined cleanup Error") : new IllegalArgumentException("cleanup " + i);
            cleanup.add(next); IndependentFaults.removeFaults.put(IndependentFaults.SLOTS.get(i), next);
        }
        Throwable thrown = failure(fixture::construct);
        if (primaryFatal || !withFatal) check(thrown == primary, "combined cleanup preserves original primary identity");
        else check(thrown == cleanup.get(3), "combined cleanup fatal dominates ordinary primary");
        attempts(7, false); projectedOrder(7);
        check(IndependentFaults.active.size() == 8, "all failed modeled removals remain uncertain");
        if (!quiet && !sameThrowable) {
            check(failureGraphContains(thrown, primary), "combined ordinary primary retained");
            for (Throwable next : cleanup) check(failureGraphContains(thrown, next), "each independent cleanup diagnostic retained");
        }
        rejectedCapture(fixture); lateCallbacks(fixture); noRetry(fixture);
    }
    private static void invalidationFailure(int cleanupIndex, boolean primaryFatal, boolean cleanupFatal) {
        Fixture fixture = fresh(true); fixture.capture = fixture.observer.capture();
        Throwable primary = primaryFatal ? new InjectedError("invalidation primary Error") : new IllegalStateException("invalidation primary ordinary");
        List<Throwable> cleanup = new ArrayList<>();
        for (int i = 0; i < 8; i++) {
            if (cleanupIndex >= 0 && i != cleanupIndex) continue;
            Throwable next = cleanupFatal && (cleanupIndex >= 0 || i == 3) ? new InjectedError("invalidation cleanup Error " + i) : new IllegalArgumentException("invalidation cleanup " + i);
            cleanup.add(next); IndependentFaults.removeFaults.put(IndependentFaults.SLOTS.get(i), next);
        }
        fixture.owner.invalidationHook = () -> { rejectedCapture(fixture); IndependentFaults.raise(primary); };
        Throwable thrown = failure(() -> detach(fixture));
        if (primaryFatal || !cleanupFatal) check(thrown == primary, "invalidation primary identity preserved");
        else {
            Throwable fatal = cleanup.stream().filter(t -> t instanceof Error).findFirst().orElseThrow();
            check(thrown == fatal, "cleanup fatal escapes ordinary invalidation failure");
        }
        check(failureGraphContains(thrown, primary), "invalidation primary retained");
        for (Throwable next : cleanup) check(failureGraphContains(thrown, next), "invalidation cleanup diagnostics remain independent");
        attempts(7, false); projectedOrder(7);
        rejectedCapture(fixture); lateCallbacks(fixture); noRetry(fixture);
    }
    private static void allCleanupErrors(boolean acquisitionPrimary) {
        Fixture fixture = fresh(!acquisitionPrimary);
        RuntimeException primary = new IllegalStateException("ordinary primary before eight Errors");
        for (String slot : IndependentFaults.SLOTS)
            IndependentFaults.removeFaults.put(slot, new InjectedError("independent fatal cleanup " + slot));
        Throwable thrown;
        if (acquisitionPrimary) {
            IndependentFaults.addFaultSlot = "animator-settings"; IndependentFaults.addFaultPhase = "after"; IndependentFaults.addFault = primary;
            thrown = failure(fixture::construct);
        } else thrown = failure(fixture.observer::close);
        check(thrown == IndependentFaults.removeFaults.get(cleanupOrder.get(0)), "first deterministic cleanup Error escapes");
        if (acquisitionPrimary) check(failureGraphContains(thrown, primary), "ordinary primary retained with eight fatal cleanup diagnostics");
        for (Throwable next : IndependentFaults.removeFaults.values())
            check(failureGraphContains(thrown, next), "every fatal cleanup diagnostic retained");
        attempts(7, false); projectedOrder(7); lateCallbacks(fixture); noRetry(fixture);
    }
    private static void removeReentry(int index, String phase, boolean detach, boolean fail) {
        Fixture fixture = fresh(true);
        String slot = IndependentFaults.SLOTS.get(index);
        IndependentFaults.removeHookSlot = slot; IndependentFaults.removeHookPhase = phase;
        IndependentFaults.removeHook = () -> { rejectedCapture(fixture); if (detach) detach(fixture); else fixture.seen().close(); };
        RuntimeException injected = new IllegalStateException("reentrant removal failure");
        if (fail) { IndependentFaults.removeFaults.put(slot, injected); IndependentFaults.failRemovalAfterEffect = true; }
        Throwable thrown = failure(fixture.observer::close);
        check(thrown == (fail ? injected : null), "removal reentry preserves expected failure");
        check(IndependentFaults.removeHookFired, "removal hook reached");
        attempts(7, false); projectedOrder(7);
        check(IndependentFaults.active.isEmpty(), "all modeled removals effective despite reentry");
        lateCallbacks(fixture); noRetry(fixture);
    }
    private static void storedTargets(boolean dead) {
        Fixture fixture = fresh(true);
        fixture.root.tree = new ViewTreeObserver(); fixture.acquiredTree.alive = !dead;
        fixture.activity.resolver = new ContentResolver();
        Throwable thrown = failure(fixture.observer::close);
        if (!dead) check(thrown == null, "live stored-target cleanup returns normally");
        else check(!(thrown instanceof Error), "dead target alone cannot invent a fatal Error");
        attempts(7, dead);
        for (IndependentFaults.Event event : IndependentFaults.events) {
            if (!event.kind().equals("remove.enter")) continue;
            if (event.slot().equals("window-focus")) check(event.target() == fixture.acquiredTree, "remove retained VTO A only");
            if (event.slot().equals("animator-settings")) check(event.target() == fixture.acquiredResolver, "remove retained resolver only");
            if (List.of("layout", "attach", "insets").contains(event.slot())) check(event.target() == fixture.root, "exact retained root");
            if (event.slot().equals("component")) check(event.target() == fixture.activity, "exact retained Activity");
            if (event.slot().equals("contrast")) check(event.target() == fixture.activity.modes, "exact retained UiModeManager");
            if (event.slot().equals("high-contrast")) check(event.target() == fixture.activity.accessibility, "exact retained AccessibilityManager");
            IndependentFaults.Event acquisition = IndependentFaults.events.stream().filter(e -> e.kind().equals("add.enter") && e.slot().equals(event.slot())).findFirst().orElseThrow();
            check(event.listener() == acquisition.listener(), "exact listener identity for removal " + event.slot());
        }
        check(IndependentFaults.active.size() == (dead ? 1 : 0), "dead VTO remains explicitly uncertain in modeled registry");
        lateCallbacks(fixture); noRetry(fixture);
    }
    private static void delayedRemoval() {
        Fixture fixture = fresh(true);
        IndependentFaults.delayedRemoval.addAll(IndependentFaults.SLOTS);
        fixture.observer.close(); attempts(7, false);
        check(IndependentFaults.active.size() == 8, "returned removals are deliberately not reclamation evidence");
        lateCallbacks(fixture); noRetry(fixture);
    }
    private static void preflight(boolean wrongThread) {
        Fixture fixture = fresh(false);
        if (wrongThread) Looper.setMain(false); else Build.VERSION.SDK_INT = 35;
        try {
            Throwable thrown = failure(fixture::construct);
            check(wrongThread ? thrown instanceof IllegalStateException : thrown instanceof AppearanceDescriptorV2.Failure,
                "preflight fails closed before acquisition");
            check(IndependentFaults.events.isEmpty(), "preflight never registers anything");
            if (wrongThread) check(IndependentFaults.reads == 0, "constructor thread check precedes tuple/platform reads");
        } finally { Looper.setMain(true); Build.VERSION.SDK_INT = 36; }
    }

    public static void main(String[] args) {
        run("H00-clean-capture-close", ObserverIndependentHostTests::clean);
        run("H00-constructor-wrong-thread", () -> preflight(true));
        run("H00-api35-remains-unsupported", () -> preflight(false));
        for (int index = 0; index < 8; index++) {
            final int slot = index;
            for (String phase : List.of("before", "after")) {
                for (boolean fatal : List.of(false, true))
                    run("H01-add-" + slot + '-' + phase + "-fatal=" + fatal, () -> addFault(slot, phase, fatal));
                for (boolean detach : List.of(false, true)) for (boolean settlesWithThrow : List.of(false, true))
                    run("H02-add-reentry-" + slot + '-' + phase + "-detach=" + detach + "-throws=" + settlesWithThrow,
                        () -> addReentry(slot, phase, detach, settlesWithThrow));
            }
        }
        for (String callback : List.of("configuration", "layout-changed", "attached", "focus", "insets", "contrast", "high-contrast", "animator-settings"))
            run("H03-construction-notification-" + callback, () -> constructionNotification(callback));
        run("H04-close-retired-first", () -> retirementFirst(false, false));
        run("H04-detach-retired-first", () -> retirementFirst(true, false));
        run("H04-detach-invalidation-Error", () -> retirementFirst(true, true));
        run("H05-live-wrong-thread-all-entries", () -> wrongThread(false));
        run("H05-retired-wrong-thread-all-entries", () -> wrongThread(true));
        run("H05-detached-wrong-thread-all-entries", () -> wrongThreadAfterOtherTerminal(false));
        run("H05-failed-constructor-wrong-thread-all-entries", () -> wrongThreadAfterOtherTerminal(true));
        run("H06-generation-exhaustion", ObserverIndependentHostTests::exhaustion);
        for (int index = 0; index < 8; index++) {
            final int slot = index;
            for (boolean fatal : List.of(false, true)) for (boolean after : List.of(false, true)) for (boolean primary : List.of(false, true))
                run("H07-cleanup-" + slot + "-fatal=" + fatal + "-after=" + after + "-primary=" + primary,
                    () -> removalFault(slot, fatal, after, primary));
            for (boolean primaryFatal : List.of(false, true)) for (boolean cleanupFatal : List.of(false, true))
                run("H08-invalidation-failure-cleanup-" + slot + "-primary-fatal=" + primaryFatal + "-cleanup-fatal=" + cleanupFatal,
                    () -> invalidationFailure(slot, primaryFatal, cleanupFatal));
            for (String phase : List.of("before", "after")) for (boolean detach : List.of(false, true)) for (boolean fail : List.of(false, true))
                run("H07-remove-reentry-" + slot + '-' + phase + "-detach=" + detach + "-fail=" + fail,
                    () -> removeReentry(slot, phase, detach, fail));
        }
        run("H08-combined-ordinary", () -> combinedRemoval(false, false, false, false));
        run("H08-combined-cleanup-Error", () -> combinedRemoval(true, false, false, false));
        run("H08-combined-primary-Error", () -> combinedRemoval(true, true, false, false));
        run("H08-combined-disabled-suppression", () -> combinedRemoval(false, false, true, false));
        run("H08-combined-self-suppression", () -> combinedRemoval(false, false, false, true));
        run("H08-invalidation-combined-ordinary-cleanup", () -> invalidationFailure(-1, false, false));
        run("H08-invalidation-combined-fatal-cleanup", () -> invalidationFailure(-1, false, true));
        run("H08-eight-cleanup-Errors", () -> allCleanupErrors(false));
        run("H08-ordinary-primary-eight-cleanup-Errors", () -> allCleanupErrors(true));
        run("H09-stored-replacement-targets", () -> storedTargets(false));
        run("H09-dead-stored-VTO", () -> storedTargets(true));
        run("H10-returned-removal-with-delayed-effect-and-late-callbacks", ObserverIndependentHostTests::delayedRemoval);
        System.out.println("INDEPENDENT_OBSERVER_SUCCESS cases=" + cases + " assertions=" + assertions);
    }
}
