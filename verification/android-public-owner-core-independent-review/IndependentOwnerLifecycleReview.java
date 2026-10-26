package dev.mixer.android;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import dev.mixer.android.OwnerLifecycleV2.Decision;
import dev.mixer.android.OwnerLifecycleV2.Kind;
import dev.mixer.android.OwnerLifecycleV2.Phase;
import dev.mixer.android.OwnerLifecycleV2.Reason;
import dev.mixer.android.OwnerLifecycleV2.Snapshot;
import dev.mixer.android.OwnerLifecycleV2.Token;
import dev.mixer.android.OwnerLifecycleV2.WindowFacts;

/** Independently authored manual-delivery oracles. No Android, producer tests, or effect execution. */
public final class IndependentOwnerLifecycleReview {
    private static int assertions;
    private static int methods;
    private static int failures;
    private static int scenarios;
    private static int batches;
    private static int decisions;
    private static int maxBatch;
    private static int wrongThreadCalls;
    private static int stressCycles;
    private static final Map<String, Integer> controls = new LinkedHashMap<>();
    private static final Map<String, Integer> threadEntries = new LinkedHashMap<>();

    private IndependentOwnerLifecycleReview() {}

    private static final class Guard implements OwnerLifecycleV2.ThreadCheck {
        boolean reject;
        int calls;
        final IllegalStateException rejected = new IllegalStateException("independent wrong-thread check");
        @Override public void requireOwner() {
            calls++;
            if (reject) throw rejected;
        }
    }

    private static final class F {
        final Guard guard = new Guard();
        final Object activity;
        final Object root;
        final Object window;
        final Object resource;
        final OwnerLifecycleV2 core;
        final Token lifetime;
        F() { this(0); }
        F(long epoch) { this(new Object(), new Object(), new Object(), new Object(), epoch); }
        F(Object activity, Object root, Object window, Object resource, long epoch) {
            this.activity = activity;
            this.root = root;
            this.window = window;
            this.resource = resource;
            core = new OwnerLifecycleV2(guard, activity, root, epoch);
            lifetime = core.lifetime();
        }
        WindowFacts facts(boolean attached, Object token, int width, int height, boolean insets) {
            return new WindowFacts(activity, root, false, attached, token, width, height, insets);
        }
        WindowFacts ready() { return facts(true, window, 360, 720, true); }
        Snapshot state() { return core.snapshot(); }
    }

    /** Deliberately value-equal distinct objects detect accidentally weakened identity checks. */
    private static final class EqualValue {
        @Override public boolean equals(Object other) { return other instanceof EqualValue; }
        @Override public int hashCode() { return 1; }
    }

    private record Entry(String name, Runnable call) {}

    private static void check(boolean condition, String why) {
        assertions++;
        if (!condition) throw new AssertionError(why);
    }
    private static void same(Object expected, Object actual, String why) { check(expected == actual, why); }
    private static void unchanged(F f, Snapshot previous, String why) { check(previous.equals(f.state()), why); }
    private static void scenario() { scenarios++; }
    private static List<Decision> b(List<Decision> out) {
        batches++;
        decisions += out.size();
        maxBatch = Math.max(maxBatch, out.size());
        check(out.size() <= 5, "decision batch exceeds selected bound of five");
        return out;
    }
    private static void kinds(List<Decision> out, Kind... expected) {
        Kind[] actual = out.stream().map(Decision::kind).toArray(Kind[]::new);
        check(Arrays.equals(expected, actual), "expected " + Arrays.toString(expected) + " got " + Arrays.toString(actual));
    }
    private static Decision one(List<Decision> out, Kind expected) {
        kinds(out, expected);
        return out.get(0);
    }
    private static void empty(List<Decision> out) { kinds(out); }
    private static Decision find(List<Decision> out, Kind expected) {
        Decision found = null;
        for (Decision d : out) if (d.kind() == expected) {
            check(found == null, "duplicate decision " + expected);
            found = d;
        }
        check(found != null, "missing decision " + expected);
        return found;
    }
    private static Token open(F f) {
        Decision queued = one(b(f.core.windowChanged(f.lifetime, f.ready())), Kind.QUEUE_DRAIN);
        Decision opened = one(b(f.core.drain(f.lifetime, queued.token(), f.ready())), Kind.OPEN_INITIAL);
        check(opened.resource() == null, "initial open cannot borrow an unacquired resource");
        same(Phase.OPENING, f.state().phase(), "opening phase");
        check(f.core.permits(opened.token()), "current opening operation is permitted");
        check(queued.token() != opened.token() && queued.token() != f.lifetime && opened.token() != f.lifetime,
            "lifetime, drain and operation are distinct");
        return opened.token();
    }
    private static void finishOpen(F f, Token op) {
        empty(b(f.core.complete(op, f.resource, true, null)));
        same(Phase.LIVE, f.state().phase(), "successful opening becomes live");
        same(f.resource, f.state().resource(), "opening adopts exactly its acquired resource");
        check(!f.state().dirty() && f.state().presentation() != null, "successful clean opening has a presentation");
    }
    private static F live() {
        F f = new F();
        kinds(b(f.core.resume(f.lifetime)), Kind.SEAL);
        kinds(b(f.core.focusChanged(f.lifetime, true)), Kind.SEAL);
        finishOpen(f, open(f));
        check(f.core.admitsInput(f.lifetime, f.state().presentation()), "current foreground/focused clean presentation admitted");
        return f;
    }
    private static Token refresh(F f) {
        Token queued = f.state().pendingDrain();
        check(queued != null, "refresh needs an actual queued token");
        List<Decision> out = b(f.core.drain(f.lifetime, queued, f.ready()));
        Decision refreshed = one(out, Kind.REFRESH_COMMITTED);
        same(f.resource, refreshed.resource(), "refresh borrows original committed owner");
        same(Phase.REFRESHING, f.state().phase(), "refreshing phase");
        return refreshed.token();
    }
    private static void refreshClean(F f) {
        Token op = refresh(f);
        empty(b(f.core.complete(op, f.resource, true, null)));
        check(!f.state().dirty() && f.state().pendingDrain() == null, "completed current refresh is clean and unqueued");
    }
    private static void terminal(F f, List<Decision> out, Reason reason, Object resource, boolean deferred) {
        if (resource != null && !deferred) kinds(out, Kind.SEAL, Kind.CANCEL_QUEUED, Kind.UNREGISTER, Kind.CLOSE);
        else kinds(out, Kind.SEAL, Kind.CANCEL_QUEUED, Kind.UNREGISTER);
        same(Phase.RETIRED, f.state().phase(), "terminal phase before decisions are consumed");
        same(reason, f.state().terminalReason(), "terminal reason");
        check(f.state().presentation() == null && f.state().dirty(), "terminal state has no published presentation");
        check(f.state().pendingDrain() == null, "terminal state revokes queued drain");
        for (Decision d : out) check(d.terminal(), "all retirement decisions are terminal");
        check(!f.core.admitsInput(f.lifetime, f.state().presentation()), "terminal input fence");
        if (resource != null && !deferred) same(resource, find(out, Kind.CLOSE).resource(), "close uses only owned resource");
    }

    private static void prerequisites() {
        for (int missing = 0; missing < 7; missing++) {
            scenario();
            F f = new F();
            WindowFacts bad = f.facts(missing != 0, missing == 1 ? null : f.window,
                missing == 2 ? 0 : missing == 3 ? -1 : 360,
                missing == 4 ? 0 : missing == 5 ? -1 : 720, missing != 6);
            empty(b(f.core.windowChanged(f.lifetime, bad)));
            empty(b(f.core.windowChanged(f.lifetime, bad)));
            same(Phase.WAITING_WINDOW, f.state().phase(), "unready owner waits");
            check(f.state().pendingDrain() == null && f.state().operation() == null, "unready owner cannot queue or open");
            empty(b(f.core.drain(f.lifetime, null, f.ready())));
            Decision q = one(b(f.core.windowChanged(f.lifetime, f.ready())), Kind.QUEUE_DRAIN);
            empty(b(f.core.windowChanged(f.lifetime, f.ready())));
            Token op = one(b(f.core.drain(f.lifetime, q.token(), f.ready())), Kind.OPEN_INITIAL).token();
            empty(b(f.core.drain(f.lifetime, q.token(), f.ready())));
            finishOpen(f, op);
            empty(b(f.core.windowChanged(f.lifetime, f.ready())));
        }
    }
    private static void freshReadinessProbe() {
        scenario();
        F f = new F();
        Token stale = one(b(f.core.windowChanged(f.lifetime, f.ready())), Kind.QUEUE_DRAIN).token();
        empty(b(f.core.drain(f.lifetime, stale, f.facts(true, f.window, 0, 720, true))));
        check(f.state().pendingDrain() == null && f.state().operation() == null, "unready fresh probe consumes drain without polling");
        Token current = one(b(f.core.windowChanged(f.lifetime, f.ready())), Kind.QUEUE_DRAIN).token();
        check(stale != current, "new real readiness gets a fresh drain identity");
        Snapshot before = f.state();
        empty(b(f.core.drain(f.lifetime, stale, f.ready())));
        unchanged(f, before, "obsolete drain cannot steal current queue slot");
        Token op = one(b(f.core.drain(f.lifetime, current, f.ready())), Kind.OPEN_INITIAL).token();
        finishOpen(f, op);
    }
    private static void invalidIdentityAndDestroyed() {
        for (int cause = 0; cause < 3; cause++) {
            scenario();
            F f = new F();
            WindowFacts facts = new WindowFacts(cause == 0 ? new Object() : f.activity,
                cause == 1 ? new Object() : f.root, cause == 2, true, f.window, 360, 720, true);
            terminal(f, b(f.core.windowChanged(f.lifetime, facts)), cause == 2 ? Reason.DESTROYED : Reason.FOREIGN_WINDOW, null, false);
            empty(b(f.core.windowChanged(f.lifetime, f.ready())));
        }
    }
    private static void invalidationDuringOpen() {
        scenario();
        F f = new F();
        Token op = open(f);
        long epoch = f.state().epoch();
        for (int i = 0; i < 100; i++) {
            kinds(b(f.core.invalidate(f.lifetime)), Kind.SEAL);
            check(f.state().pendingDrain() == null && f.state().operation() == op, "opening invalidation cannot start or queue concurrent work");
        }
        check(f.state().epoch() == epoch + 100, "each opening invalidation advances checked epoch");
        one(b(f.core.complete(op, f.resource, true, null)), Kind.QUEUE_DRAIN);
        check(f.state().dirty() && !f.core.admitsInput(f.lifetime, f.state().presentation()), "opening completion cannot erase later dirtiness");
        refreshClean(f);
    }
    private static void invalidationDuringRefresh() {
        scenario();
        F f = live();
        kinds(b(f.core.invalidate(f.lifetime)), Kind.SEAL, Kind.QUEUE_DRAIN);
        Token first = refresh(f);
        long epoch = f.state().epoch();
        for (int i = 0; i < 50; i++) kinds(b(f.core.invalidate(f.lifetime)), Kind.SEAL);
        one(b(f.core.complete(first, f.resource, true, null)), Kind.QUEUE_DRAIN);
        check(f.state().epoch() == epoch + 50 && f.state().dirty(), "refresh completion preserves newer epoch");
        Snapshot before = f.state();
        empty(b(f.core.complete(first, new Object(), true, null)));
        unchanged(f, before, "duplicate refresh cannot clear newer epoch");
        refreshClean(f);
    }
    private static void dirtyBurst() {
        scenario();
        F f = live();
        Token presentation = f.state().presentation();
        Token queued = null;
        for (int i = 0; i < 100; i++) {
            List<Decision> out = b(f.core.invalidate(f.lifetime));
            if (i == 0) queued = find(out, Kind.QUEUE_DRAIN).token();
            kinds(out, i == 0 ? new Kind[] {Kind.SEAL, Kind.QUEUE_DRAIN} : new Kind[] {Kind.SEAL});
            same(queued, f.state().pendingDrain(), "burst has exactly one queued drain");
            empty(b(f.core.dispatchInput(f.lifetime, presentation)));
        }
        refreshClean(f);
    }
    private static void retirementDuringOpening() {
        for (int cause = 0; cause < 8; cause++) {
            scenario();
            F f = new F();
            Token op = open(f);
            List<Decision> out;
            Reason reason;
            switch (cause) {
                case 0 -> { out = b(f.core.close(f.lifetime)); reason = Reason.CLOSED; }
                case 1 -> { out = b(f.core.detached(f.lifetime)); reason = Reason.DETACHED; }
                case 2 -> { out = b(f.core.windowChanged(f.lifetime, new WindowFacts(f.activity, f.root, true, true, f.window, 360, 720, true))); reason = Reason.DESTROYED; }
                case 3 -> { out = b(f.core.windowChanged(f.lifetime, f.facts(true, new Object(), 360, 720, true))); reason = Reason.WINDOW_LOST; }
                case 4 -> { out = b(f.core.windowChanged(f.lifetime, f.facts(true, null, 360, 720, true))); reason = Reason.WINDOW_LOST; }
                case 5 -> { out = b(f.core.windowChanged(f.lifetime, f.facts(false, f.window, 360, 720, true))); reason = Reason.WINDOW_LOST; }
                case 6 -> { out = b(f.core.windowChanged(f.lifetime, new WindowFacts(f.activity, new Object(), false, true, f.window, 360, 720, true))); reason = Reason.FOREIGN_WINDOW; }
                default -> { out = b(f.core.windowChanged(f.lifetime, new WindowFacts(new Object(), f.root, false, true, f.window, 360, 720, true))); reason = Reason.FOREIGN_WINDOW; }
            }
            terminal(f, out, reason, null, true);
            check(!f.core.permits(op) && f.state().operation() == op, "terminal fence closes while one operation is outstanding");
            Decision closed = one(b(f.core.complete(op, f.resource, true, null)), Kind.CLOSE);
            same(f.resource, closed.resource(), "late acquired resource receives exactly one close");
            check(f.state().presentation() == null && f.state().closePending(), "late completion cannot publish");
            Snapshot before = f.state();
            empty(b(f.core.complete(op, new Object(), true, null)));
            empty(b(f.core.close(f.lifetime)));
            empty(b(f.core.windowChanged(f.lifetime, f.ready())));
            unchanged(f, before, "duplicate close/completion/reattach is inert");
            f.core.cleanupComplete(closed.token(), null);
            check(f.state().resource() == null && !f.state().closePending(), "matching close result discharges retained resource");
        }
    }
    private static void retirementBeforeReadiness() {
        for (boolean detach : new boolean[] {false, true}) {
            scenario();
            F f = new F();
            terminal(f, b(detach ? f.core.detached(f.lifetime) : f.core.close(f.lifetime)), detach ? Reason.DETACHED : Reason.CLOSED, null, false);
            Snapshot before = f.state();
            empty(b(f.core.windowChanged(f.lifetime, f.ready())));
            empty(b(f.core.invalidate(f.lifetime)));
            empty(b(f.core.drain(f.lifetime, null, f.ready())));
            unchanged(f, before, "pre-readiness retirement never reopens");
        }
    }
    private static void foreignAndDuplicateCompletions() {
        scenario();
        F a = new F();
        F z = new F();
        Token ao = open(a);
        Token zo = open(z);
        check(a.lifetime != z.lifetime && ao != zo, "owners never share capabilities");
        Snapshot ap = a.state();
        Snapshot zp = z.state();
        empty(b(a.core.complete(zo, z.resource, true, new Object())));
        empty(b(z.core.complete(ao, a.resource, false, new Object())));
        unchanged(a, ap, "foreign operation cannot adopt a resource");
        unchanged(z, zp, "reverse cross-delivery cannot mutate");
        finishOpen(a, ao);
        ap = a.state();
        empty(b(a.core.complete(ao, z.resource, true, null)));
        unchanged(a, ap, "duplicate successful open cannot replace owned resource");
        finishOpen(z, zo);
        check(a.state().presentation() != z.state().presentation(), "presentation identities are owner-local");
    }
    private static void staleCompletionCannotStealOperation() {
        scenario();
        F f = live();
        kinds(b(f.core.invalidate(f.lifetime)), Kind.SEAL, Kind.QUEUE_DRAIN);
        Token old = refresh(f);
        empty(b(f.core.complete(old, f.resource, true, null)));
        kinds(b(f.core.invalidate(f.lifetime)), Kind.SEAL, Kind.QUEUE_DRAIN);
        Token current = refresh(f);
        Snapshot before = f.state();
        empty(b(f.core.complete(old, f.resource, false, new Object())));
        unchanged(f, before, "stale completion cannot clear or fail a current refresh");
        check(f.core.permits(current) && !f.core.permits(old), "only current operation is permitted");
        empty(b(f.core.complete(current, f.resource, true, null)));
    }
    private static void openingFailureCleanup() {
        for (boolean committed : new boolean[] {false, true}) {
            scenario();
            F f = new F();
            Token op = open(f);
            Object primary = new Object();
            List<Decision> out = b(f.core.complete(op, f.resource, committed, primary));
            terminal(f, out, Reason.FAILED_OPERATION, f.resource, false);
            same(primary, f.state().primaryFailure(), "opening failure preserves exact primary identity");
            Object c = new Object();
            Object u = new Object();
            Object x = new Object();
            Token cancel = find(out, Kind.CANCEL_QUEUED).token();
            Token unregister = find(out, Kind.UNREGISTER).token();
            Token close = find(out, Kind.CLOSE).token();
            check(cancel != unregister && cancel != close && close != unregister, "cleanup slots have independent identities");
            f.core.cleanupComplete(close, x);
            f.core.cleanupComplete(unregister, u);
            f.core.cleanupComplete(cancel, c);
            Snapshot s = f.state();
            same(primary, s.primaryFailure(), "cleanup cannot replace primary failure");
            same(c, s.cancelFailure(), "cancel failure identity");
            same(u, s.unregisterFailure(), "unregister failure identity");
            same(x, s.closeFailure(), "close failure identity");
            check(!s.cancelPending() && !s.unregisterPending() && !s.closePending() && s.resource() == null, "all reports discharge once even when cleanup failed");
            f.core.cleanupComplete(close, new Object());
            f.core.cleanupComplete(cancel, new Object());
            f.core.cleanupComplete(unregister, new Object());
            unchanged(f, s, "duplicate cleanup results cannot replace diagnostics");
            empty(b(f.core.close(f.lifetime)));
        }
    }
    private static void registrationFailures() {
        for (int state = 0; state < 3; state++) {
            scenario();
            F f = state == 1 ? live() : new F();
            Token op = state == 2 ? open(f) : null;
            Object primary = new Object();
            List<Decision> out = b(f.core.registrationFailed(f.lifetime, primary));
            terminal(f, out, Reason.FAILED_REGISTRATION, state == 1 ? f.resource : null, state == 2);
            same(primary, f.state().primaryFailure(), "registration failure is retained primary");
            if (op != null) {
                Decision closed = one(b(f.core.complete(op, f.resource, false, new Object())), Kind.CLOSE);
                same(f.resource, closed.resource(), "resource acquired by failed opening still closes after registration failure");
                same(primary, f.state().primaryFailure(), "later operation failure does not replace registration primary");
            }
        }
    }
    private static void foreignCleanupReports() {
        scenario();
        F a = live();
        F z = live();
        List<Decision> ac = b(a.core.close(a.lifetime));
        List<Decision> zc = b(z.core.close(z.lifetime));
        Snapshot before = a.state();
        for (Decision d : zc) a.core.cleanupComplete(d.token(), new Object());
        a.core.cleanupComplete(null, new Object());
        unchanged(a, before, "foreign/null cleanup token cannot discharge or replace ownership");
        Token close = find(ac, Kind.CLOSE).token();
        a.core.cleanupComplete(close, null);
        check(a.state().resource() == null && z.state().resource() == z.resource, "close completion affects only its owner");
    }
    private static void closeDuringRefreshOrInput() {
        for (boolean input : new boolean[] {false, true}) {
            scenario();
            F f = live();
            Token queued = null;
            Token op;
            if (input) op = one(b(f.core.dispatchInput(f.lifetime, f.state().presentation())), Kind.DISPATCH_INPUT).token();
            else {
                kinds(b(f.core.invalidate(f.lifetime)), Kind.SEAL, Kind.QUEUE_DRAIN);
                queued = f.state().pendingDrain();
                op = refresh(f);
            }
            terminal(f, b(f.core.close(f.lifetime)), Reason.CLOSED, f.resource, true);
            check(!f.core.permits(op) && !f.state().closePending(), "active native transaction is fenced and close deferred");
            empty(b(f.core.drain(f.lifetime, queued, f.ready())));
            Decision closed = one(b(f.core.complete(op, f.resource, true, null)), Kind.CLOSE);
            same(f.resource, closed.resource(), "returned operation requests one owned close");
            check(f.state().presentation() == null, "returned operation cannot publish after close");
            empty(b(f.core.complete(op, new Object(), true, null)));
            f.core.cleanupComplete(closed.token(), null);
            check(f.state().resource() == null, "deferred cleanup resource discharged");
        }
    }
    private static void ineffectiveQueueCancellation() {
        scenario();
        F f = live();
        kinds(b(f.core.invalidate(f.lifetime)), Kind.SEAL, Kind.QUEUE_DRAIN);
        Token queued = f.state().pendingDrain();
        List<Decision> closed = b(f.core.close(f.lifetime));
        terminal(f, closed, Reason.CLOSED, f.resource, false);
        same(queued, find(closed, Kind.CANCEL_QUEUED).resource(), "cancel decision identifies the queued callback");
        Object failedCancel = new Object();
        f.core.cleanupComplete(find(closed, Kind.CANCEL_QUEUED).token(), failedCancel);
        Snapshot before = f.state();
        empty(b(f.core.drain(f.lifetime, queued, f.ready())));
        unchanged(f, before, "already-dequeued callback is harmless even when cancellation failed");
    }
    private static void inputAdmissionAndStalePresentation() {
        scenario();
        F f = live();
        F foreign = live();
        Token old = f.state().presentation();
        kinds(b(f.core.invalidate(f.lifetime)), Kind.SEAL, Kind.QUEUE_DRAIN);
        check(!f.core.admitsInput(f.lifetime, old), "invalidation closes input before queued work");
        empty(b(f.core.dispatchInput(f.lifetime, old)));
        refreshClean(f);
        Token current = f.state().presentation();
        check(current != old && !f.core.admitsInput(f.lifetime, old), "old presentation remains stale after refresh");
        check(!f.core.admitsInput(foreign.lifetime, current), "foreign lifetime denied");
        empty(b(f.core.dispatchInput(foreign.lifetime, current)));
        Token op = one(b(f.core.dispatchInput(f.lifetime, current)), Kind.DISPATCH_INPUT).token();
        same(Phase.INPUTTING, f.state().phase(), "input is immediate and single-flight");
        empty(b(f.core.dispatchInput(f.lifetime, current)));
        check(!f.core.admitsInput(f.lifetime, current), "reentrant input admission denied");
        empty(b(f.core.complete(op, f.resource, true, null)));
        check(f.state().presentation() != current && f.core.admitsInput(f.lifetime, f.state().presentation()), "matching input completion publishes only its new presentation");
        check(f.state().pendingDrain() == null, "rejected input was never queued or replayed");
    }
    private static void invalidationDuringInput() {
        scenario();
        F f = live();
        Token oldPresentation = f.state().presentation();
        Token op = one(b(f.core.dispatchInput(f.lifetime, oldPresentation)), Kind.DISPATCH_INPUT).token();
        long beforeEpoch = f.state().epoch();
        kinds(b(f.core.invalidate(f.lifetime)), Kind.SEAL);
        check(f.state().dirty() && f.state().epoch() == beforeEpoch + 1 && f.state().pendingDrain() == null,
            "input invalidation records dirty epoch without concurrent queued work");
        empty(b(f.core.dispatchInput(f.lifetime, oldPresentation)));
        one(b(f.core.complete(op, f.resource, true, null)), Kind.QUEUE_DRAIN);
        check(f.state().dirty() && !f.core.admitsInput(f.lifetime, f.state().presentation()),
            "input completion cannot erase an invalidation received during input");
        check(f.state().presentation() != oldPresentation, "input completion cannot revive the previous presentation identity");
        refreshClean(f);
        check(f.core.admitsInput(f.lifetime, f.state().presentation()), "post-input environment refresh restores current admission");
        same(f.resource, f.state().resource(), "input and follow-up refresh retain original owner");
    }
    private static void foregroundFocusAndConfiguration() {
        scenario();
        F f = live();
        Token life = f.lifetime;
        kinds(b(f.core.pause(life)), Kind.SEAL, Kind.QUEUE_DRAIN);
        Token queued = f.state().pendingDrain();
        kinds(b(f.core.stop(life)), Kind.SEAL);
        same(queued, f.state().pendingDrain(), "pause/stop coalesce environment work");
        check(!f.state().foreground() && f.state().resource() == f.resource, "pause retains resource but closes admission");
        refreshClean(f);
        check(!f.core.admitsInput(life, f.state().presentation()), "clean stopped owner remains inadmissible");
        kinds(b(f.core.resume(life)), Kind.SEAL, Kind.QUEUE_DRAIN);
        check(!f.core.admitsInput(life, f.state().presentation()), "resume requires fresh environment work");
        refreshClean(f);
        check(f.core.admitsInput(life, f.state().presentation()), "foreground focused input returns after refresh");
        kinds(b(f.core.focusChanged(life, false)), Kind.SEAL, Kind.QUEUE_DRAIN);
        refreshClean(f);
        check(!f.core.admitsInput(life, f.state().presentation()), "focus loss remains a gate after refresh");
        kinds(b(f.core.focusChanged(life, true)), Kind.SEAL, Kind.QUEUE_DRAIN);
        refreshClean(f);
        kinds(b(f.core.configurationChanged(life)), Kind.SEAL, Kind.QUEUE_DRAIN);
        refreshClean(f);
        same(life, f.core.lifetime(), "configuration does not create a new lifetime");
        same(f.resource, f.state().resource(), "all transitions retain exact committed owner");
    }
    private static void focusNotAnOpeningPrerequisite() {
        scenario();
        F f = new F();
        finishOpen(f, open(f));
        check(!f.state().foreground() && !f.state().focused(), "opening needs neither foreground nor focus fact");
        check(!f.core.admitsInput(f.lifetime, f.state().presentation()), "opening does not invent foreground input authority");
    }
    private static void temporarilyUnavailableEnvironment() {
        for (int missing = 0; missing < 4; missing++) {
            scenario();
            F f = live();
            kinds(b(f.core.invalidate(f.lifetime)), Kind.SEAL, Kind.QUEUE_DRAIN);
            Token queued = f.state().pendingDrain();
            WindowFacts bad = f.facts(true, f.window, missing == 0 ? 0 : missing == 1 ? -1 : 360,
                missing == 2 ? 0 : 720, missing != 3);
            kinds(b(f.core.windowChanged(f.lifetime, bad)), Kind.SEAL);
            empty(b(f.core.drain(f.lifetime, queued, bad)));
            check(f.state().dirty() && f.state().operation() == null && f.state().pendingDrain() == null,
                "unavailable live tuple stays dirty without polling or operation");
            for (int i = 0; i < 5; i++) empty(b(f.core.windowChanged(f.lifetime, bad)));
            check(!f.core.admitsInput(f.lifetime, f.state().presentation()), "unavailable tuple never admits old presentation");
            kinds(b(f.core.windowChanged(f.lifetime, f.ready())), Kind.SEAL, Kind.QUEUE_DRAIN);
            refreshClean(f);
            same(f.resource, f.state().resource(), "readiness recovery uses same owner");
        }
    }
    private static void epochExhaustionWaiting() {
        scenario();
        F f = new F(Long.MAX_VALUE);
        terminal(f, b(f.core.invalidate(f.lifetime)), Reason.EPOCH_EXHAUSTED, null, false);
        check(f.state().epoch() == Long.MAX_VALUE, "maximum epoch does not wrap");
        empty(b(f.core.windowChanged(f.lifetime, f.ready())));
        empty(b(f.core.invalidate(f.lifetime)));
    }
    private static void epochExhaustionLiveAndQueued() {
        scenario();
        F f = new F(Long.MAX_VALUE - 1);
        Token initial = open(f);
        finishOpen(f, initial);
        kinds(b(f.core.invalidate(f.lifetime)), Kind.SEAL, Kind.QUEUE_DRAIN);
        Token queued = f.state().pendingDrain();
        check(f.state().epoch() == Long.MAX_VALUE, "penultimate invalidation reaches maximum exactly");
        List<Decision> out = b(f.core.invalidate(f.lifetime));
        terminal(f, out, Reason.EPOCH_EXHAUSTED, f.resource, false);
        same(queued, find(out, Kind.CANCEL_QUEUED).resource(), "exhaustion cancels current queue");
        Snapshot before = f.state();
        empty(b(f.core.drain(f.lifetime, queued, f.ready())));
        empty(b(f.core.complete(initial, new Object(), true, null)));
        unchanged(f, before, "old capabilities cannot revive exhausted owner");
    }
    private static void epochExhaustionOpening() {
        scenario();
        F f = new F(Long.MAX_VALUE);
        Token op = open(f);
        terminal(f, b(f.core.invalidate(f.lifetime)), Reason.EPOCH_EXHAUSTED, null, true);
        check(!f.core.permits(op), "exhaustion revokes executing operation synchronously");
        same(f.resource, one(b(f.core.complete(op, f.resource, true, null)), Kind.CLOSE).resource(), "late resource closes after exhaustion");
    }
    private static void wrong(F f, Entry entry) {
        Snapshot before = f.state();
        int calls = f.guard.calls;
        boolean rejected = false;
        f.guard.reject = true;
        try { entry.call().run(); }
        catch (IllegalStateException failure) { same(f.guard.rejected, failure, "trusted checker rejection identity for " + entry.name()); rejected = true; }
        finally { f.guard.reject = false; }
        check(rejected, "entry bypassed checker: " + entry.name());
        check(f.guard.calls == calls + 1, "entry must check before branching: " + entry.name());
        unchanged(f, before, "wrong-thread entry changed state: " + entry.name());
        wrongThreadCalls++;
        threadEntries.merge(entry.name(), 1, Integer::sum);
    }
    private static void everyEntryChecksThreadFirst() {
        F foreign = new F();
        Token foreignOperation = open(foreign);
        for (int phase = 0; phase < 6; phase++) {
            scenario();
            F f = phase == 0 || phase == 1 ? new F() : live();
            if (phase == 1) open(f);
            if (phase == 3) { b(f.core.invalidate(f.lifetime)); refresh(f); }
            if (phase == 4) one(b(f.core.dispatchInput(f.lifetime, f.state().presentation())), Kind.DISPATCH_INPUT);
            if (phase == 5) b(f.core.close(f.lifetime));
            Snapshot s = f.state();
            List<Entry> entries = List.of(
                new Entry("lifetime", () -> f.core.lifetime()),
                new Entry("snapshot", () -> f.core.snapshot()),
                new Entry("permits", () -> f.core.permits(s.operation())),
                new Entry("admitsInput", () -> f.core.admitsInput(f.lifetime, s.presentation())),
                new Entry("windowChanged", () -> f.core.windowChanged(f.lifetime, null)),
                new Entry("drain", () -> f.core.drain(f.lifetime, s.pendingDrain(), null)),
                new Entry("invalidate", () -> f.core.invalidate(f.lifetime)),
                new Entry("configurationChanged", () -> f.core.configurationChanged(f.lifetime)),
                new Entry("focusChanged", () -> f.core.focusChanged(f.lifetime, true)),
                new Entry("pause", () -> f.core.pause(f.lifetime)),
                new Entry("stop", () -> f.core.stop(f.lifetime)),
                new Entry("resume", () -> f.core.resume(f.lifetime)),
                new Entry("dispatchInput", () -> f.core.dispatchInput(f.lifetime, s.presentation())),
                new Entry("complete", () -> f.core.complete(s.operation(), new Object(), false, new Object())),
                new Entry("detached", () -> f.core.detached(f.lifetime)),
                new Entry("close", () -> f.core.close(f.lifetime)),
                new Entry("registrationFailed", () -> f.core.registrationFailed(f.lifetime, new Object())),
                new Entry("cleanupComplete", () -> f.core.cleanupComplete(s.operation(), new Object())));
            for (Entry entry : entries) wrong(f, entry);
            wrong(f, new Entry("complete-stale", () -> f.core.complete(foreignOperation, foreign.resource, true, null)));
            wrong(f, new Entry("drain-stale", () -> f.core.drain(foreign.lifetime, null, null)));
            wrong(f, new Entry("close-stale", () -> f.core.close(foreign.lifetime)));
            wrong(f, new Entry("cleanupComplete-stale", () -> f.core.cleanupComplete(foreignOperation, null)));
        }
        scenario();
        F anchor = new F();
        wrong(anchor, new Entry("constructor-default", () -> new OwnerLifecycleV2(anchor.guard, null, null)));
        wrong(anchor, new Entry("constructor-seeded", () -> new OwnerLifecycleV2(anchor.guard, null, null, -1)));
    }
    private static void operationThatNeverReturns() {
        for (int mode = 0; mode < 3; mode++) {
            scenario();
            F f = mode == 0 ? new F() : live();
            Token op;
            if (mode == 0) op = open(f);
            else if (mode == 1) { b(f.core.invalidate(f.lifetime)); op = refresh(f); }
            else op = one(b(f.core.dispatchInput(f.lifetime, f.state().presentation())), Kind.DISPATCH_INPUT).token();
            List<Decision> closed = b(f.core.close(f.lifetime));
            terminal(f, closed, Reason.CLOSED, mode == 0 ? null : f.resource, true);
            f.core.cleanupComplete(find(closed, Kind.CANCEL_QUEUED).token(), null);
            f.core.cleanupComplete(find(closed, Kind.UNREGISTER).token(), null);
            for (int i = 0; i < 20; i++) {
                empty(b(f.core.close(f.lifetime)));
                empty(b(f.core.drain(f.lifetime, null, f.ready())));
                empty(b(f.core.complete(null, new Object(), true, null)));
            }
            same(op, f.state().operation(), "never-returning operation remains recorded after retirement");
            check(!f.state().closePending() && !f.core.permits(op), "no false close request while operation never returns");
            same(mode == 0 ? null : f.resource, f.state().resource(), "actual resource reclamation remains pending");
        }
    }
    private static void boundedRepeatedCycles() {
        scenario();
        F f = live();
        Set<Token> seen = Collections.newSetFromMap(new IdentityHashMap<>());
        seen.add(f.lifetime);
        Token previousOperation = null;
        Token previousDrain = null;
        for (int cycle = 0; cycle < 20000; cycle++) {
            Token oldPresentation = f.state().presentation();
            kinds(b(f.core.invalidate(f.lifetime)), Kind.SEAL, Kind.QUEUE_DRAIN);
            Token queued = f.state().pendingDrain();
            check(seen.add(queued), "drain identity reused during long run");
            Token op = refresh(f);
            check(seen.add(op), "operation identity reused during long run");
            if (cycle % 256 == 0) {
                Snapshot before = f.state();
                empty(b(f.core.drain(f.lifetime, previousDrain, f.ready())));
                empty(b(f.core.complete(previousOperation, new Object(), true, null)));
                unchanged(f, before, "old manual delivery cannot perturb long-running operation");
            }
            empty(b(f.core.complete(op, f.resource, true, null)));
            Token current = f.state().presentation();
            check(current != oldPresentation && seen.add(current), "presentation identity reused during long run");
            check(f.state().resource() == f.resource && !f.state().dirty() && f.state().operation() == null && f.state().pendingDrain() == null,
                "long-run core retains one resource and clears consumed work");
            previousOperation = op;
            previousDrain = queued;
            stressCycles++;
        }
        List<Decision> closed = b(f.core.close(f.lifetime));
        terminal(f, closed, Reason.CLOSED, f.resource, false);
        for (Decision d : closed) f.core.cleanupComplete(d.token(), new Object());
        check(!f.state().cancelPending() && !f.state().unregisterPending() && !f.state().closePending(), "long-run terminal cleanup reports remain bounded and complete");
    }
    private static void newOwnerAfterOldRetirement() {
        scenario();
        F old = new F();
        Token oldOperation = open(old);
        List<Decision> retired = b(old.core.close(old.lifetime));
        F current = live();
        Snapshot before = current.state();
        empty(b(current.core.windowChanged(old.lifetime, old.ready())));
        empty(b(current.core.invalidate(old.lifetime)));
        empty(b(current.core.close(old.lifetime)));
        empty(b(current.core.complete(oldOperation, old.resource, true, null)));
        for (Decision d : retired) current.core.cleanupComplete(d.token(), new Object());
        unchanged(current, before, "old Activity capabilities cannot affect fresh owner");
        Decision lateClose = one(b(old.core.complete(oldOperation, old.resource, true, null)), Kind.CLOSE);
        same(old.resource, lateClose.resource(), "old owner closes only old late resource");
        unchanged(current, before, "old late completion leaves current owner independent");
        empty(b(old.core.dispatchInput(current.lifetime, current.state().presentation())));
        check(old.lifetime != current.lifetime && old.state().presentation() == null, "fresh lifetime has no saved-state transfer");
    }
    private static void unknownOrMissingOpeningOutcome() {
        for (int mode = 0; mode < 3; mode++) {
            scenario();
            F f = new F();
            Token op = open(f);
            Object acquired = mode == 0 ? null : f.resource;
            Object failure = mode == 2 ? new Object() : null;
            List<Decision> out = b(f.core.complete(op, acquired, mode == 0, failure));
            terminal(f, out, Reason.FAILED_OPERATION, acquired, false);
            same(failure, f.state().primaryFailure(), "unknown/missing outcome does not invent success or a diagnostic identity");
            empty(b(f.core.windowChanged(f.lifetime, f.ready())));
        }
    }
    private static void refreshAndInputCannotReplaceResource() {
        for (int mode = 0; mode < 4; mode++) {
            scenario();
            F f = live();
            Token op;
            if (mode < 2) { b(f.core.invalidate(f.lifetime)); op = refresh(f); }
            else op = one(b(f.core.dispatchInput(f.lifetime, f.state().presentation())), Kind.DISPATCH_INPUT).token();
            Object offered = mode % 2 == 0 ? new Object() : null;
            List<Decision> out = b(f.core.complete(op, offered, true, null));
            terminal(f, out, Reason.FAILED_OPERATION, f.resource, false);
            same(f.resource, f.state().resource(), "refresh/input completion cannot replace resource");
            same(f.resource, find(out, Kind.CLOSE).resource(), "foreign/null completion closes only original resource");
            if (offered != null) check(find(out, Kind.CLOSE).resource() != offered, "foreign offered resource is never closed");
        }
    }
    private static void onlyMatchingOpenAdoptsAfterRetirement() {
        scenario();
        F f = new F();
        F foreign = new F();
        Token own = open(f);
        Token other = open(foreign);
        b(f.core.detached(f.lifetime));
        Snapshot before = f.state();
        empty(b(f.core.complete(other, foreign.resource, false, new Object())));
        unchanged(f, before, "retired owner does not adopt foreign acquired identity");
        Object primary = new Object();
        Decision close = one(b(f.core.complete(own, f.resource, false, primary)), Kind.CLOSE);
        same(f.resource, close.resource(), "matching retired open is the only permitted resource adoption");
        same(primary, f.state().primaryFailure(), "late matching failure is retained when no earlier primary exists");
        before = f.state();
        empty(b(f.core.complete(own, foreign.resource, false, new Object())));
        unchanged(f, before, "duplicate retired completion cannot replace late resource or primary");
    }
    private static void immutableDecisionBatch() {
        scenario();
        F f = new F();
        List<Decision> out = b(f.core.windowChanged(f.lifetime, f.ready()));
        Snapshot before = f.state();
        boolean rejected = false;
        try { out.add(out.get(0)); }
        catch (UnsupportedOperationException expected) { rejected = true; }
        check(rejected, "decision batch is immutable to caller");
        unchanged(f, before, "caller cannot mutate production work through decision list");
    }
    private static void nullFactsFailClosed() {
        for (int mode = 0; mode < 3; mode++) {
            scenario();
            F f = mode == 2 ? live() : new F();
            List<Decision> out;
            if (mode == 1) {
                Token queued = one(b(f.core.windowChanged(f.lifetime, f.ready())), Kind.QUEUE_DRAIN).token();
                out = b(f.core.drain(f.lifetime, queued, null));
            } else out = b(f.core.windowChanged(f.lifetime, null));
            terminal(f, out, Reason.FAILED_OPERATION, mode == 2 ? f.resource : null, false);
        }
    }
    private static void valueEqualityDoesNotGrantOwnership() {
        scenario();
        EqualValue activity = new EqualValue();
        EqualValue root = new EqualValue();
        EqualValue window = new EqualValue();
        EqualValue resource = new EqualValue();
        F f = new F(activity, root, window, resource, 0);
        finishOpen(f, open(f));
        List<Decision> out = b(f.core.windowChanged(f.lifetime, f.facts(true, new EqualValue(), 360, 720, true)));
        terminal(f, out, Reason.WINDOW_LOST, resource, false);
        F z = new F(activity, root, window, resource, 0);
        finishOpen(z, open(z));
        b(z.core.invalidate(z.lifetime));
        Token op = refresh(z);
        terminal(z, b(z.core.complete(op, new EqualValue(), true, null)), Reason.FAILED_OPERATION, resource, false);
        F a = new F(activity, root, window, resource, 0);
        terminal(a, b(a.core.windowChanged(a.lifetime, new WindowFacts(new EqualValue(), root, false, true, window, 360, 720, true))), Reason.FOREIGN_WINDOW, null, false);
    }

    private static void run(String name, String ids, Runnable test) {
        methods++;
        int before = assertions;
        try {
            test.run();
            for (String id : ids.split(",")) controls.merge(id, 1, Integer::sum);
            System.out.println("PASS " + name + " assertions=" + (assertions - before) + " controls=" + ids);
        } catch (Throwable failure) {
            failures++;
            System.out.println("FAIL " + name + " assertions=" + (assertions - before) + " controls=" + ids);
            failure.printStackTrace(System.err);
        }
    }
    private static String mapJson(Map<String, Integer> map) {
        List<String> rows = new ArrayList<>();
        for (Map.Entry<String, Integer> e : map.entrySet()) rows.add("\"" + e.getKey() + "\":" + e.getValue());
        return "{" + String.join(",", rows) + "}";
    }
    public static void main(String[] args) {
        run("each_readiness_prerequisite", "R01", IndependentOwnerLifecycleReview::prerequisites);
        run("fresh_probe_and_stale_drain", "R01", IndependentOwnerLifecycleReview::freshReadinessProbe);
        run("foreign_root_activity_and_destroyed", "R03", IndependentOwnerLifecycleReview::invalidIdentityAndDestroyed);
        run("invalidation_during_open", "R02", IndependentOwnerLifecycleReview::invalidationDuringOpen);
        run("invalidation_during_refresh", "R02,R04", IndependentOwnerLifecycleReview::invalidationDuringRefresh);
        run("dirty_burst_before_drain", "R02", IndependentOwnerLifecycleReview::dirtyBurst);
        run("eight_retirement_causes_during_open", "R03,R04", IndependentOwnerLifecycleReview::retirementDuringOpening);
        run("retirement_before_readiness", "R03", IndependentOwnerLifecycleReview::retirementBeforeReadiness);
        run("foreign_and_duplicate_completions", "R04,R14", IndependentOwnerLifecycleReview::foreignAndDuplicateCompletions);
        run("stale_completion_cannot_steal_operation", "R04", IndependentOwnerLifecycleReview::staleCompletionCannotStealOperation);
        run("opening_failure_owned_cleanup_diagnostics", "R05", IndependentOwnerLifecycleReview::openingFailureCleanup);
        run("registration_failure_three_phases", "R05", IndependentOwnerLifecycleReview::registrationFailures);
        run("foreign_cleanup_reports", "R04,R05", IndependentOwnerLifecycleReview::foreignCleanupReports);
        run("close_during_refresh_or_input", "R06", IndependentOwnerLifecycleReview::closeDuringRefreshOrInput);
        run("ineffective_queue_cancellation", "R06", IndependentOwnerLifecycleReview::ineffectiveQueueCancellation);
        run("input_admission_stale_and_reentrant", "R07", IndependentOwnerLifecycleReview::inputAdmissionAndStalePresentation);
        run("invalidation_during_input", "R02,R07", IndependentOwnerLifecycleReview::invalidationDuringInput);
        run("pause_stop_resume_focus_configuration", "R08", IndependentOwnerLifecycleReview::foregroundFocusAndConfiguration);
        run("initial_open_without_focus", "R08", IndependentOwnerLifecycleReview::focusNotAnOpeningPrerequisite);
        run("temporary_unavailable_live_environment", "R09", IndependentOwnerLifecycleReview::temporarilyUnavailableEnvironment);
        run("epoch_exhaustion_waiting", "R10", IndependentOwnerLifecycleReview::epochExhaustionWaiting);
        run("epoch_exhaustion_live_with_queue", "R10", IndependentOwnerLifecycleReview::epochExhaustionLiveAndQueued);
        run("epoch_exhaustion_opening", "R10", IndependentOwnerLifecycleReview::epochExhaustionOpening);
        run("all_entries_thread_check_first", "R11", IndependentOwnerLifecycleReview::everyEntryChecksThreadFirst);
        run("operation_never_returns_cleanup_pending", "R12", IndependentOwnerLifecycleReview::operationThatNeverReturns);
        run("twenty_thousand_cycles", "R13", IndependentOwnerLifecycleReview::boundedRepeatedCycles);
        run("new_owner_old_activity_capabilities", "R14", IndependentOwnerLifecycleReview::newOwnerAfterOldRetirement);
        run("unknown_missing_open_outcome", "R15", IndependentOwnerLifecycleReview::unknownOrMissingOpeningOutcome);
        run("refresh_input_resource_replacement_rejected", "R15", IndependentOwnerLifecycleReview::refreshAndInputCannotReplaceResource);
        run("matching_retired_open_only_adopts", "R04,R15", IndependentOwnerLifecycleReview::onlyMatchingOpenAdoptsAfterRetirement);
        run("immutable_decision_batch", "R13", IndependentOwnerLifecycleReview::immutableDecisionBatch);
        run("null_facts_fail_closed", "R15", IndependentOwnerLifecycleReview::nullFactsFailClosed);
        run("reference_identity_despite_value_equality", "R04,R15", IndependentOwnerLifecycleReview::valueEqualityDoesNotGrantOwnership);
        System.out.println("SUMMARY {\"methods\":" + methods + ",\"failures\":" + failures + ",\"scenarios\":" + scenarios +
            ",\"assertions\":" + assertions + ",\"decision_batches_observed\":" + batches + ",\"decisions_observed\":" + decisions +
            ",\"max_batch\":" + maxBatch + ",\"wrong_thread_calls\":" + wrongThreadCalls + ",\"stress_cycles\":" + stressCycles +
            ",\"control_passed_methods\":" + mapJson(controls) + ",\"wrong_thread_entry_calls\":" + mapJson(threadEntries) + "}");
        if (failures != 0) System.exit(1);
    }
}
