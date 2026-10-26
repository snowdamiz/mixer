package dev.mixer.android;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;

import static dev.mixer.android.OwnerLifecycleV2.Kind;
import static dev.mixer.android.OwnerLifecycleV2.Phase;
import static dev.mixer.android.OwnerLifecycleV2.Reason;

/** Actual pure Java core, deterministic manual queue; no Android stubs or native authority. */
public final class OwnerLifecycleV2HostTests {
    private static int checks;
    private static int tests;
    private static final List<String> names = new ArrayList<>();
    private OwnerLifecycleV2HostTests() {}
    private static void check(boolean value, String message) {
        checks++;
        if (!value) throw new AssertionError(message);
    }
    private static void run(String name, Runnable body) {
        body.run(); tests++; names.add(name);
    }
    private static final class Gate implements OwnerLifecycleV2.ThreadCheck {
        boolean allowed = true;
        int calls;
        @Override public void requireOwner() {
            calls++;
            if (!allowed) throw new IllegalStateException("test wrong owner thread");
        }
    }
    private static final class Harness {
        final Object activity = new Object(), root = new Object(), window = new Object(), resource = new Object();
        final Gate gate = new Gate();
        final OwnerLifecycleV2 core;
        final OwnerLifecycleV2.Token lifetime;
        final ArrayDeque<OwnerLifecycleV2.Token> queue = new ArrayDeque<>();
        final List<OwnerLifecycleV2.Decision> history = new ArrayList<>();
        Harness() { this(0); }
        Harness(long epoch) {
            core = new OwnerLifecycleV2(gate, activity, root, epoch);
            lifetime = core.lifetime();
        }
        OwnerLifecycleV2.WindowFacts ready() { return facts(false, true, window, 320, 640, true); }
        OwnerLifecycleV2.WindowFacts facts(boolean destroyed, boolean attached, Object token, int width, int height, boolean insets) {
            return new OwnerLifecycleV2.WindowFacts(activity, root, destroyed, attached, token, width, height, insets);
        }
        List<OwnerLifecycleV2.Decision> record(List<OwnerLifecycleV2.Decision> batch) {
            check(batch.size() <= OwnerLifecycleV2.MAX_DECISIONS, "bounded decision batch");
            history.addAll(batch);
            for (var action : batch) if (action.kind() == Kind.QUEUE_DRAIN) queue.add(action.token());
            try { batch.add(null); throw new AssertionError("mutable batch"); }
            catch (UnsupportedOperationException expected) { checks++; }
            return batch;
        }
        void activate() { record(core.resume(lifetime)); record(core.focusChanged(lifetime, true)); }
        OwnerLifecycleV2.Decision deliver(OwnerLifecycleV2.WindowFacts fresh, Kind wanted) {
            check(!queue.isEmpty(), "manual queue has explicit delivery");
            return one(record(core.drain(lifetime, queue.remove(), fresh)), wanted);
        }
        OwnerLifecycleV2.Decision opening() {
            activate(); record(core.windowChanged(lifetime, ready()));
            return deliver(ready(), Kind.OPEN_INITIAL);
        }
        void live() {
            var open = opening();
            record(core.complete(open.token(), resource, true, null));
            check(core.snapshot().phase() == Phase.LIVE && core.admitsInput(lifetime, core.snapshot().presentation()), "live input after exact initial completion");
        }
        long count(Kind kind) { return history.stream().filter(d -> d.kind() == kind).count(); }
    }
    private static OwnerLifecycleV2.Decision one(List<OwnerLifecycleV2.Decision> actions, Kind kind) {
        var matches = actions.stream().filter(d -> d.kind() == kind).toList();
        check(matches.size() == 1, "exactly one " + kind);
        return matches.get(0);
    }
    private static void kinds(List<OwnerLifecycleV2.Decision> actions, Kind... expected) {
        check(actions.stream().map(OwnerLifecycleV2.Decision::kind).toList().equals(List.of(expected)), "ordered expected decisions");
    }
    private static void readiness() {
        Harness h = new Harness(); h.activate();
        var unready = List.of(h.facts(false, false, h.window, 320, 640, true),
            h.facts(false, true, null, 320, 640, true), h.facts(false, true, h.window, 0, 640, true),
            h.facts(false, true, h.window, 320, 0, true), h.facts(false, true, h.window, -1, 640, true),
            h.facts(false, true, h.window, 320, 640, false));
        for (var facts : unready) {
            kinds(h.record(h.core.windowChanged(h.lifetime, facts)));
            check(h.queue.isEmpty() && h.core.snapshot().phase() == Phase.WAITING_WINDOW, "unready never polls/opens");
        }
        h.record(h.core.windowChanged(h.lifetime, h.ready()));
        var drain = h.core.snapshot().pendingDrain();
        h.record(h.core.windowChanged(h.lifetime, h.ready()));
        check(h.queue.size() == 1 && h.core.snapshot().pendingDrain() == drain, "duplicate readiness coalesces");
        var open = h.deliver(h.ready(), Kind.OPEN_INITIAL);
        check(open.token() != h.lifetime && open.token() != drain && h.core.permits(open.token()), "distinct operation identity");
        kinds(h.record(h.core.windowChanged(h.lifetime, h.ready())));
        check(h.count(Kind.OPEN_INITIAL) == 1, "opening cannot overlap");
    }
    private static void freshProbe() {
        Harness h = new Harness(); h.record(h.core.windowChanged(h.lifetime, h.ready()));
        var queued = h.queue.remove();
        kinds(h.record(h.core.drain(h.lifetime, queued, h.facts(false, true, h.window, 0, 640, true))));
        check(h.core.snapshot().phase() == Phase.WAITING_WINDOW && h.queue.isEmpty(), "drain uses fresh size, no poll");
        h.record(h.core.windowChanged(h.lifetime, h.ready()));
        h.deliver(h.ready(), Kind.OPEN_INITIAL);
    }
    private static void dirtyBurst() {
        Harness h = new Harness(); h.live();
        var prior = h.core.snapshot().presentation();
        for (int i = 0; i < 20; i++) h.record(h.core.invalidate(h.lifetime));
        check(h.queue.size() == 1 && !h.core.admitsInput(h.lifetime, prior), "dirty burst coalesces and denies input");
        var refresh = h.deliver(h.ready(), Kind.REFRESH_COMMITTED);
        check(refresh.resource() == h.resource, "refresh retained owner");
        h.record(h.core.complete(refresh.token(), h.resource, true, null));
        check(h.queue.isEmpty() && !h.core.snapshot().dirty() && h.count(Kind.OPEN_INITIAL) == 1 && h.count(Kind.DISPATCH_INPUT) == 0, "refresh emits no open/input");
        check(!h.core.admitsInput(h.lifetime, prior), "previous presentation fenced");
    }
    private static void invalidationDuringOperations() {
        Harness h = new Harness();
        var open = h.opening(); h.record(h.core.invalidate(h.lifetime));
        check(h.queue.isEmpty() && h.core.permits(open.token()), "terminal fence distinct from native environment gate");
        h.record(h.core.complete(open.token(), h.resource, true, null));
        check(h.core.snapshot().dirty() && h.queue.size() == 1, "opening dirty epoch retained");
        var refresh = h.deliver(h.ready(), Kind.REFRESH_COMMITTED);
        h.record(h.core.invalidate(h.lifetime)); h.record(h.core.invalidate(h.lifetime));
        check(h.queue.isEmpty(), "busy refresh not overlapped");
        h.record(h.core.complete(refresh.token(), h.resource, true, null));
        check(h.core.snapshot().dirty() && h.queue.size() == 1, "newer dirty epoch survives refresh completion");
        var next = h.deliver(h.ready(), Kind.REFRESH_COMMITTED);
        h.record(h.core.complete(next.token(), h.resource, true, null));
        check(!h.core.snapshot().dirty() && h.queue.isEmpty(), "one needed follow-up completes");
    }
    private static void temporarySize() {
        Harness h = new Harness(); h.live();
        var zero = h.facts(false, true, h.window, 320, 0, true);
        h.record(h.core.windowChanged(h.lifetime, zero));
        check(h.queue.isEmpty() && h.core.snapshot().dirty(), "live zero size waits without refresh");
        h.record(h.core.windowChanged(h.lifetime, h.ready()));
        var refresh = h.deliver(h.ready(), Kind.REFRESH_COMMITTED);
        h.record(h.core.complete(refresh.token(), h.resource, true, null));
        check(h.count(Kind.REFRESH_COMMITTED) == 1 && h.count(Kind.OPEN_INITIAL) == 1, "readiness recovery preserves owner");
    }
    private static void closeBeforeReadyAndStaleQueue() {
        Harness h = new Harness();
        kinds(h.record(h.core.close(h.lifetime)), Kind.SEAL, Kind.CANCEL_QUEUED, Kind.UNREGISTER);
        kinds(h.record(h.core.windowChanged(h.lifetime, h.ready())));
        kinds(h.record(h.core.resume(h.lifetime)));
        kinds(h.record(h.core.close(h.lifetime)));
        check(h.count(Kind.OPEN_INITIAL) == 0, "retired waiting owner cannot open");
        Harness queued = new Harness(); queued.record(queued.core.windowChanged(queued.lifetime, queued.ready()));
        var alreadyDequeued = queued.queue.remove();
        var terminal = queued.record(queued.core.detached(queued.lifetime));
        check(terminal.get(0).terminal(), "terminal seal before cleanup");
        kinds(queued.record(queued.core.drain(queued.lifetime, alreadyDequeued, queued.ready())));
        check(queued.core.snapshot().phase() == Phase.RETIRED && queued.count(Kind.OPEN_INITIAL) == 0, "dequeued delivery ignored without queue removal");
    }
    private static void closeDuringOpen() {
        Harness h = new Harness(); var open = h.opening();
        kinds(h.record(h.core.close(h.lifetime)), Kind.SEAL, Kind.CANCEL_QUEUED, Kind.UNREGISTER);
        check(!h.core.permits(open.token()) && h.core.snapshot().operation() == open.token() && h.core.snapshot().resource() == null, "busy retired open retained pending until return");
        var closed = one(h.record(h.core.complete(open.token(), h.resource, true, null)), Kind.CLOSE);
        check(closed.resource() == h.resource && h.core.snapshot().presentation() == null, "late acquired resource closed, never published");
        kinds(h.record(h.core.complete(open.token(), new Object(), true, null)));
        check(h.count(Kind.CLOSE) == 1, "duplicate open completion cannot close foreign resource");
    }
    private static void failedOpenWithResource() {
        for (boolean retireFirst : new boolean[] { false, true }) {
            Harness h = new Harness(); var open = h.opening(); Object failure = new Object();
            if (retireFirst) h.record(h.core.close(h.lifetime));
            var actions = h.record(h.core.complete(open.token(), h.resource, false, failure));
            check(one(actions, Kind.CLOSE).resource() == h.resource, "failed open acquisition still closed");
            check(h.core.snapshot().primaryFailure() == failure && h.core.snapshot().phase() == Phase.RETIRED, "failed open diagnostic preserved");
        }
        Harness none = new Harness(); var open = none.opening();
        none.record(none.core.complete(open.token(), null, false, new Object()));
        check(none.count(Kind.CLOSE) == 0 && none.core.snapshot().phase() == Phase.RETIRED, "no invented close for absent resource");
    }
    private static void inputSerializationAndReentrantTerminal() {
        Harness h = new Harness(); h.live(); var displayed = h.core.snapshot().presentation();
        var input = one(h.record(h.core.dispatchInput(h.lifetime, displayed)), Kind.DISPATCH_INPUT);
        check(h.core.snapshot().phase() == Phase.INPUTTING && h.core.permits(input.token()), "input operation in flight");
        kinds(h.record(h.core.dispatchInput(h.lifetime, displayed)));
        h.record(h.core.invalidate(h.lifetime));
        kinds(h.record(h.core.close(h.lifetime)), Kind.SEAL, Kind.CANCEL_QUEUED, Kind.UNREGISTER);
        check(!h.core.permits(input.token()) && !h.core.admitsInput(h.lifetime, displayed), "synchronous terminal request revokes busy fence");
        var close = one(h.record(h.core.complete(input.token(), h.resource, true, null)), Kind.CLOSE);
        check(close.resource() == h.resource && h.queue.isEmpty() && h.core.snapshot().presentation() == null, "retired input never publishes or refreshes");
    }
    private static void refreshDetachAndNeverReturn() {
        Harness h = new Harness(); h.live(); h.record(h.core.invalidate(h.lifetime));
        var refresh = h.deliver(h.ready(), Kind.REFRESH_COMMITTED);
        h.record(h.core.detached(h.lifetime));
        check(!h.core.permits(refresh.token()) && h.count(Kind.CLOSE) == 0, "never-returning operation cleanup remains pending");
        kinds(h.record(h.core.windowChanged(h.lifetime, h.ready())));
        var close = one(h.record(h.core.complete(refresh.token(), h.resource, false, new Object())), Kind.CLOSE);
        check(close.resource() == h.resource && h.count(Kind.OPEN_INITIAL) == 1, "refresh terminal cleanup once");
    }
    private static void foreignAndDuplicateCompletions() {
        Harness a = new Harness(), b = new Harness(); var open = a.opening(); var otherOpen = b.opening();
        var before = a.core.snapshot();
        kinds(a.record(a.core.complete(otherOpen.token(), b.resource, true, null)));
        check(a.core.snapshot().equals(before), "foreign completion observes no owner change");
        a.record(a.core.complete(open.token(), a.resource, true, null));
        before = a.core.snapshot();
        kinds(a.record(a.core.complete(open.token(), b.resource, true, null)));
        check(a.core.snapshot().equals(before), "duplicate completion cannot adopt foreign owner");
        kinds(a.record(a.core.complete(null, b.resource, true, null)));
        kinds(a.record(a.core.dispatchInput(b.lifetime, a.core.snapshot().presentation())));
        a.record(a.core.close(a.lifetime));
        check(one(a.history.stream().filter(d -> d.kind() == Kind.CLOSE).toList(), Kind.CLOSE).resource() == a.resource, "only own resource closed");
    }
    private static void operationCannotReplaceResource() {
        for (boolean input : new boolean[] { false, true }) {
            Harness h = new Harness(); h.live();
            OwnerLifecycleV2.Decision operation;
            if (input) operation = one(h.record(h.core.dispatchInput(h.lifetime, h.core.snapshot().presentation())), Kind.DISPATCH_INPUT);
            else { h.record(h.core.invalidate(h.lifetime)); operation = h.deliver(h.ready(), Kind.REFRESH_COMMITTED); }
            Object foreign = new Object();
            var close = one(h.record(h.core.complete(operation.token(), foreign, true, null)), Kind.CLOSE);
            check(close.resource() == h.resource && h.core.snapshot().phase() == Phase.RETIRED, "refresh/input cannot replace or close foreign resource");
        }
    }
    private static void stalePresentationAndInputDirty() {
        Harness h = new Harness(); h.live(); var old = h.core.snapshot().presentation();
        var input = one(h.record(h.core.dispatchInput(h.lifetime, old)), Kind.DISPATCH_INPUT);
        h.record(h.core.complete(input.token(), h.resource, true, null));
        check(!h.core.admitsInput(h.lifetime, old) && h.core.admitsInput(h.lifetime, h.core.snapshot().presentation()), "successful input replaces presentation fence");
        h.record(h.core.invalidate(h.lifetime));
        kinds(h.record(h.core.dispatchInput(h.lifetime, h.core.snapshot().presentation())));
        check(h.count(Kind.DISPATCH_INPUT) == 1, "dirty input rejected, never queued/replayed");
    }
    private static void windowRetirementMatrix() {
        for (int i = 0; i < 5; i++) {
            Harness h = new Harness(); h.live();
            OwnerLifecycleV2.WindowFacts next = switch (i) {
                case 0 -> h.facts(false, true, new Object(), 320, 640, true);
                case 1 -> h.facts(false, true, null, 320, 640, true);
                case 2 -> h.facts(false, false, h.window, 320, 640, true);
                case 3 -> h.facts(true, true, h.window, 320, 640, true);
                default -> new OwnerLifecycleV2.WindowFacts(new Object(), h.root, false, true, h.window, 320, 640, true);
            };
            var close = one(h.record(h.core.windowChanged(h.lifetime, next)), Kind.CLOSE);
            check(h.core.snapshot().phase() == Phase.RETIRED && close.resource() == h.resource, "changed authority retires actual owner");
            kinds(h.record(h.core.windowChanged(h.lifetime, h.ready())));
        }
        Harness opening = new Harness(); var op = opening.opening();
        opening.record(opening.core.windowChanged(opening.lifetime, opening.facts(false, true, new Object(), 320, 640, true)));
        check(!opening.core.permits(op.token()), "replacement during open revokes fence");
        check(one(opening.record(opening.core.complete(op.token(), opening.resource, true, null)), Kind.CLOSE).resource() == opening.resource, "replacement late acquisition closed");
    }
    private static void pauseFocusConfig() {
        Harness h = new Harness(); h.live();
        h.record(h.core.pause(h.lifetime)); h.record(h.core.stop(h.lifetime));
        var refresh = h.deliver(h.ready(), Kind.REFRESH_COMMITTED);
        h.record(h.core.complete(refresh.token(), h.resource, true, null));
        check(!h.core.admitsInput(h.lifetime, h.core.snapshot().presentation()), "background denies input even after refresh");
        h.record(h.core.resume(h.lifetime));
        check(!h.core.admitsInput(h.lifetime, h.core.snapshot().presentation()), "resume dirties before input");
        refresh = h.deliver(h.ready(), Kind.REFRESH_COMMITTED); h.record(h.core.complete(refresh.token(), h.resource, true, null));
        h.record(h.core.focusChanged(h.lifetime, false));
        refresh = h.deliver(h.ready(), Kind.REFRESH_COMMITTED); h.record(h.core.complete(refresh.token(), h.resource, true, null));
        check(!h.core.admitsInput(h.lifetime, h.core.snapshot().presentation()), "focus loss remains denied after refresh");
        h.record(h.core.focusChanged(h.lifetime, true)); h.record(h.core.configurationChanged(h.lifetime));
        refresh = h.deliver(h.ready(), Kind.REFRESH_COMMITTED); h.record(h.core.complete(refresh.token(), h.resource, true, null));
        check(h.core.admitsInput(h.lifetime, h.core.snapshot().presentation()) && h.count(Kind.OPEN_INITIAL) == 1, "foreground/focus/config use same owner");
    }
    private static void failuresAndIndependentCleanup() {
        Harness h = new Harness(); h.live(); Object primary = new Object();
        var terminal = h.record(h.core.registrationFailed(h.lifetime, primary));
        kinds(terminal, Kind.SEAL, Kind.CANCEL_QUEUED, Kind.UNREGISTER, Kind.CLOSE);
        Object cancelError = new Object(), unregisterError = new Object(), closeError = new Object();
        var cancel = one(terminal, Kind.CANCEL_QUEUED); var unregister = one(terminal, Kind.UNREGISTER); var close = one(terminal, Kind.CLOSE);
        h.core.cleanupComplete(cancel.token(), cancelError);
        check(h.core.snapshot().unregisterPending() && h.core.snapshot().closePending(), "failed cancel cannot suppress other cleanup decisions");
        h.core.cleanupComplete(unregister.token(), unregisterError); h.core.cleanupComplete(close.token(), closeError);
        h.core.cleanupComplete(close.token(), new Object());
        var snapshot = h.core.snapshot();
        check(snapshot.primaryFailure() == primary && snapshot.cancelFailure() == cancelError && snapshot.unregisterFailure() == unregisterError && snapshot.closeFailure() == closeError, "bounded diagnostic identity slots, first completion wins");
        check(!snapshot.cancelPending() && !snapshot.unregisterPending() && !snapshot.closePending() && snapshot.resource() == null, "reported attempts discharged and owner reference released");
        kinds(h.record(h.core.close(h.lifetime)));
    }
    private static void failedRefreshAndInput() {
        for (boolean input : new boolean[] { false, true }) {
            Harness h = new Harness(); h.live();
            OwnerLifecycleV2.Decision op;
            if (input) op = one(h.record(h.core.dispatchInput(h.lifetime, h.core.snapshot().presentation())), Kind.DISPATCH_INPUT);
            else { h.record(h.core.invalidate(h.lifetime)); op = h.deliver(h.ready(), Kind.REFRESH_COMMITTED); }
            Object failure = new Object();
            var terminal = h.record(h.core.complete(op.token(), h.resource, false, failure));
            check(one(terminal, Kind.CLOSE).resource() == h.resource && h.core.snapshot().primaryFailure() == failure, "failed operation closes owned resource");
            kinds(h.record(h.core.complete(op.token(), h.resource, true, null)));
            check(h.core.snapshot().phase() == Phase.RETIRED && h.count(Kind.CLOSE) == 1, "failure never retried or reopened");
        }
    }
    private static void overflow() {
        Harness h = new Harness(Long.MAX_VALUE);
        kinds(h.record(h.core.invalidate(h.lifetime)), Kind.SEAL, Kind.CANCEL_QUEUED, Kind.UNREGISTER);
        check(h.core.snapshot().epoch() == Long.MAX_VALUE && h.core.snapshot().terminalReason() == Reason.EPOCH_EXHAUSTED, "epoch exhaustion terminal without wrap");
        Harness active = new Harness(Long.MAX_VALUE - 2);
        active.activate(); active.record(active.core.windowChanged(active.lifetime, active.ready()));
        var open = active.deliver(active.ready(), Kind.OPEN_INITIAL);
        active.record(active.core.complete(open.token(), active.resource, true, null));
        check(one(active.record(active.core.invalidate(active.lifetime)), Kind.CLOSE).resource() == active.resource, "exhaustion closes live owner");
    }
    private static void recreationAndIdentityEquality() {
        Harness old = new Harness(); old.live(); old.record(old.core.close(old.lifetime));
        Harness next = new Harness(); next.live(); var before = next.core.snapshot();
        kinds(next.record(next.core.close(old.lifetime)));
        kinds(next.record(next.core.windowChanged(old.lifetime, old.ready())));
        check(next.core.snapshot().equals(before) && next.lifetime != old.lifetime && next.resource != old.resource, "recreation old callbacks cannot affect new lifetime");
        Object hostile = new Object() { @Override public boolean equals(Object other) { throw new AssertionError("identity required"); } @Override public int hashCode() { throw new AssertionError("identity required"); } };
        Gate gate = new Gate(); var core = new OwnerLifecycleV2(gate, hostile, hostile); var token = core.lifetime();
        var facts = new OwnerLifecycleV2.WindowFacts(hostile, hostile, false, true, hostile, 1, 1, true);
        var queue = one(core.windowChanged(token, facts), Kind.QUEUE_DRAIN);
        var open = one(core.drain(token, queue.token(), facts), Kind.OPEN_INITIAL);
        core.complete(open.token(), hostile, true, null);
        check(one(core.close(token), Kind.CLOSE).resource() == hostile, "no application equals/hashCode called");
    }
    private static void wrongThreadEveryEntry() {
        Harness h = new Harness(); var open = h.opening();
        List<Runnable> calls = List.of(
            () -> h.core.lifetime(), () -> h.core.snapshot(), () -> h.core.permits(open.token()),
            () -> h.core.admitsInput(h.lifetime, null), () -> h.core.windowChanged(h.lifetime, null),
            () -> h.core.drain(h.lifetime, null, null), () -> h.core.invalidate(h.lifetime),
            () -> h.core.configurationChanged(h.lifetime), () -> h.core.focusChanged(h.lifetime, false),
            () -> h.core.pause(h.lifetime), () -> h.core.stop(h.lifetime), () -> h.core.resume(h.lifetime),
            () -> h.core.dispatchInput(h.lifetime, null), () -> h.core.complete(open.token(), h.resource, true, null),
            () -> h.core.detached(h.lifetime), () -> h.core.close(h.lifetime),
            () -> h.core.registrationFailed(h.lifetime, new Object()), () -> h.core.cleanupComplete(null, new Object()));
        for (Runnable call : calls) {
            var before = h.core.snapshot(); int count = h.gate.calls;
            h.gate.allowed = false;
            try { call.run(); throw new AssertionError("wrong thread accepted"); }
            catch (IllegalStateException expected) { checks++; }
            finally { h.gate.allowed = true; }
            check(h.gate.calls == count + 1 && h.core.snapshot().equals(before), "thread checked once before state/payload effects");
        }
        h.record(h.core.close(h.lifetime));
        h.gate.allowed = false;
        try { h.core.complete(open.token(), new Object(), true, null); throw new AssertionError("retired completion bypassed thread check"); }
        catch (IllegalStateException expected) { checks++; } finally { h.gate.allowed = true; }
        Gate rejected = new Gate(); rejected.allowed = false;
        for (boolean seeded : new boolean[] { false, true }) {
            try {
                if (seeded) new OwnerLifecycleV2(rejected, null, null, -1);
                else new OwnerLifecycleV2(rejected, null, null);
                throw new AssertionError("wrong-thread construction accepted");
            } catch (IllegalStateException expected) { checks++; }
        }
    }
    private static void boundedLongRun() {
        Harness h = new Harness(); h.live();
        for (int i = 0; i < 5000; i++) {
            h.record(h.core.invalidate(h.lifetime));
            var refresh = h.deliver(h.ready(), Kind.REFRESH_COMMITTED);
            h.record(h.core.complete(refresh.token(), h.resource, true, null));
            check(h.queue.isEmpty() && h.core.snapshot().operation() == null && h.core.snapshot().pendingDrain() == null, "long-run pending state remains bounded");
        }
        check(h.count(Kind.OPEN_INITIAL) == 1 && h.count(Kind.REFRESH_COMMITTED) == 5000 && h.core.snapshot().resource() == h.resource, "long-run retains one owner");
    }
    public static void main(String[] args) {
        run("readiness", OwnerLifecycleV2HostTests::readiness);
        run("freshProbe", OwnerLifecycleV2HostTests::freshProbe);
        run("dirtyBurst", OwnerLifecycleV2HostTests::dirtyBurst);
        run("invalidationDuringOperations", OwnerLifecycleV2HostTests::invalidationDuringOperations);
        run("temporarySize", OwnerLifecycleV2HostTests::temporarySize);
        run("closeBeforeReadyAndStaleQueue", OwnerLifecycleV2HostTests::closeBeforeReadyAndStaleQueue);
        run("closeDuringOpen", OwnerLifecycleV2HostTests::closeDuringOpen);
        run("failedOpenWithResource", OwnerLifecycleV2HostTests::failedOpenWithResource);
        run("inputSerializationAndReentrantTerminal", OwnerLifecycleV2HostTests::inputSerializationAndReentrantTerminal);
        run("refreshDetachAndNeverReturn", OwnerLifecycleV2HostTests::refreshDetachAndNeverReturn);
        run("foreignAndDuplicateCompletions", OwnerLifecycleV2HostTests::foreignAndDuplicateCompletions);
        run("operationCannotReplaceResource", OwnerLifecycleV2HostTests::operationCannotReplaceResource);
        run("stalePresentationAndInputDirty", OwnerLifecycleV2HostTests::stalePresentationAndInputDirty);
        run("windowRetirementMatrix", OwnerLifecycleV2HostTests::windowRetirementMatrix);
        run("pauseFocusConfig", OwnerLifecycleV2HostTests::pauseFocusConfig);
        run("failuresAndIndependentCleanup", OwnerLifecycleV2HostTests::failuresAndIndependentCleanup);
        run("failedRefreshAndInput", OwnerLifecycleV2HostTests::failedRefreshAndInput);
        run("overflow", OwnerLifecycleV2HostTests::overflow);
        run("recreationAndIdentityEquality", OwnerLifecycleV2HostTests::recreationAndIdentityEquality);
        run("wrongThreadEveryEntry", OwnerLifecycleV2HostTests::wrongThreadEveryEntry);
        run("boundedLongRun", OwnerLifecycleV2HostTests::boundedLongRun);
        System.out.println("{\"scope\":\"host ownership decisions only\",\"tests\":" + tests + ",\"assertions\":" + checks + ",\"cases\":[\"" + String.join("\",\"", names) + "\"],\"status\":\"pass\"}");
    }
}
