package dev.mixer.android;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/** Host-testable ownership decisions only. No Android capture, effect runner or release authority. */
final class OwnerLifecycleV2 {
    enum Phase { WAITING_WINDOW, OPENING, LIVE, REFRESHING, INPUTTING, RETIRED }
    enum Kind { QUEUE_DRAIN, OPEN_INITIAL, REFRESH_COMMITTED, DISPATCH_INPUT, SEAL, CANCEL_QUEUED, UNREGISTER, CLOSE }
    enum Reason { CLOSED, DETACHED, DESTROYED, FOREIGN_WINDOW, WINDOW_LOST, FAILED_OPERATION, FAILED_REGISTRATION, EPOCH_EXHAUSTED }
    @FunctionalInterface interface ThreadCheck { void requireOwner(); }
    static final class Token { private Token() {} }
    /** Facts are untrusted test/adapter values, never a concrete native capture. Identity uses ==. */
    record WindowFacts(Object activity, Object root, boolean destroyed, boolean attached,
                       Object window, int width, int height, boolean insetsAvailable) {
        boolean ready() { return attached && window != null && width > 0 && height > 0 && insetsAvailable && !destroyed; }
    }
    /** token correlates delivery/completion; resource is borrowed and never grants native authority. */
    record Decision(Kind kind, Token token, Object resource, boolean terminal) {}
    record Snapshot(Phase phase, long epoch, boolean dirty, boolean foreground, boolean focused,
                    Token pendingDrain, Token operation, Token presentation, Object resource,
                    Reason terminalReason, Object primaryFailure, boolean cancelPending,
                    boolean unregisterPending, boolean closePending, Object cancelFailure,
                    Object unregisterFailure, Object closeFailure) {}
    static final int MAX_DECISIONS = 5;

    private final ThreadCheck thread;
    private final Object activity;
    private final Object root;
    private final Token lifetime = new Token();
    private Phase phase = Phase.WAITING_WINDOW;
    private WindowFacts facts;
    private Object window;
    private Object resource;
    private Token drain;
    private Token operation;
    private Kind operationKind;
    private long operationEpoch;
    private Token presentation;
    private long epoch;
    private boolean dirty = true;
    private boolean foreground;
    private boolean focused;
    private Reason terminalReason;
    private Object primaryFailure;
    private Token cancel;
    private Token unregister;
    private Token close;
    private boolean cancelDone;
    private boolean unregisterDone;
    private boolean closeDone;
    private Object cancelFailure;
    private Object unregisterFailure;
    private Object closeFailure;

    OwnerLifecycleV2(ThreadCheck thread, Object activity, Object root) { this(thread, activity, root, 0); }
    /** Package-private epoch seed for deterministic exhaustion tests; normal construction uses zero. */
    OwnerLifecycleV2(ThreadCheck thread, Object activity, Object root, long initialEpoch) {
        Objects.requireNonNull(thread).requireOwner();
        this.thread = thread;
        this.activity = Objects.requireNonNull(activity);
        this.root = Objects.requireNonNull(root);
        if (initialEpoch < 0) throw new IllegalArgumentException("negative owner epoch");
        epoch = initialEpoch;
    }

    Token lifetime() { thread.requireOwner(); return lifetime; }
    Snapshot snapshot() {
        thread.requireOwner();
        return new Snapshot(phase, epoch, dirty, foreground, focused, drain, operation, presentation,
            resource, terminalReason, primaryFailure, cancel != null && !cancelDone,
            unregister != null && !unregisterDone, close != null && !closeDone,
            cancelFailure, unregisterFailure, closeFailure);
    }
    /** Terminal fence only. Environment/current-record checks remain the native owner's responsibility. */
    boolean permits(Token candidate) {
        thread.requireOwner();
        return phase != Phase.RETIRED && candidate != null && operation == candidate;
    }
    boolean admitsInput(Token owner, Token displayed) {
        thread.requireOwner();
        return accepts(owner) && phase == Phase.LIVE && !dirty && foreground && focused &&
            operation == null && drain == null && displayed != null && presentation == displayed;
    }

    List<Decision> windowChanged(Token owner, WindowFacts next) {
        thread.requireOwner();
        if (!accepts(owner)) return List.of();
        var out = new ArrayList<Decision>();
        observe(next, out);
        schedule(out);
        return batch(out);
    }
    /** Caller must synchronously probe again when a queued drain is delivered. */
    List<Decision> drain(Token owner, Token queued, WindowFacts fresh) {
        thread.requireOwner();
        if (!accepts(owner) || queued == null || queued != drain) return List.of();
        drain = null;
        var out = new ArrayList<Decision>();
        observe(fresh, out);
        if (phase == Phase.RETIRED || operation != null || facts == null || !facts.ready()) return batch(out);
        if (phase == Phase.WAITING_WINDOW) {
            window = facts.window();
            begin(Kind.OPEN_INITIAL, Phase.OPENING, out);
        } else if (phase == Phase.LIVE && dirty) {
            begin(Kind.REFRESH_COMMITTED, Phase.REFRESHING, out);
        }
        return batch(out);
    }
    List<Decision> invalidate(Token owner) {
        thread.requireOwner();
        return invalidateOwner(owner);
    }
    List<Decision> configurationChanged(Token owner) {
        thread.requireOwner();
        return invalidateOwner(owner);
    }
    List<Decision> focusChanged(Token owner, boolean value) {
        thread.requireOwner();
        if (!accepts(owner)) return List.of();
        focused = value;
        return invalidateOwner(owner);
    }
    List<Decision> pause(Token owner) {
        thread.requireOwner();
        if (!accepts(owner)) return List.of();
        foreground = false;
        return invalidateOwner(owner);
    }
    List<Decision> stop(Token owner) {
        thread.requireOwner();
        if (!accepts(owner)) return List.of();
        foreground = false;
        return invalidateOwner(owner);
    }
    List<Decision> resume(Token owner) {
        thread.requireOwner();
        if (!accepts(owner)) return List.of();
        foreground = true;
        return invalidateOwner(owner);
    }
    /** No payload is retained or queued here. Runner dispatches the current caller's input synchronously. */
    List<Decision> dispatchInput(Token owner, Token displayed) {
        thread.requireOwner();
        if (!(accepts(owner) && phase == Phase.LIVE && !dirty && foreground && focused &&
              operation == null && drain == null && displayed != null && presentation == displayed)) return List.of();
        var out = new ArrayList<Decision>();
        begin(Kind.DISPATCH_INPUT, Phase.INPUTTING, out);
        return batch(out);
    }

    /** Only the exact OPEN_INITIAL completion can first adopt an acquired resource identity. */
    List<Decision> complete(Token completed, Object acquired, boolean committed, Object failure) {
        thread.requireOwner();
        if (completed == null || completed != operation) return List.of();
        var out = new ArrayList<Decision>();
        boolean opening = operationKind == Kind.OPEN_INITIAL;
        boolean validResource = opening ? acquired != null : acquired == resource && acquired != null;
        if (opening && acquired != null) resource = acquired;
        operation = null;
        operationKind = null;
        if (phase == Phase.RETIRED) {
            if (primaryFailure == null && failure != null) primaryFailure = failure;
            closeIfIdle(out);
            return batch(out);
        }
        if (!validResource || !committed || failure != null) {
            retire(Reason.FAILED_OPERATION, failure, out);
            return batch(out);
        }
        phase = Phase.LIVE;
        presentation = new Token();
        dirty = epoch != operationEpoch;
        schedule(out);
        return batch(out);
    }
    List<Decision> detached(Token owner) {
        thread.requireOwner();
        return terminate(owner, Reason.DETACHED, null);
    }
    List<Decision> close(Token owner) {
        thread.requireOwner();
        return terminate(owner, Reason.CLOSED, null);
    }
    List<Decision> registrationFailed(Token owner, Object failure) {
        thread.requireOwner();
        return terminate(owner, Reason.FAILED_REGISTRATION, failure);
    }
    /** First completion per cleanup token wins; diagnostics are three bounded identity slots. */
    void cleanupComplete(Token completed, Object failure) {
        thread.requireOwner();
        if (completed == null) return;
        if (completed == cancel && !cancelDone) { cancelDone = true; cancelFailure = failure; }
        else if (completed == unregister && !unregisterDone) { unregisterDone = true; unregisterFailure = failure; }
        else if (completed == close && !closeDone) { closeDone = true; closeFailure = failure; resource = null; }
    }

    private boolean accepts(Token owner) { return owner == lifetime && phase != Phase.RETIRED; }
    private List<Decision> invalidateOwner(Token owner) {
        if (!accepts(owner)) return List.of();
        var out = new ArrayList<Decision>();
        markDirty(out);
        schedule(out);
        return batch(out);
    }
    private List<Decision> terminate(Token owner, Reason reason, Object failure) {
        if (!accepts(owner)) return List.of();
        var out = new ArrayList<Decision>();
        retire(reason, failure, out);
        return batch(out);
    }
    private void observe(WindowFacts next, List<Decision> out) {
        Objects.requireNonNull(next);
        if (next.activity() != activity || next.root() != root) { retire(Reason.FOREIGN_WINDOW, null, out); return; }
        if (next.destroyed()) { retire(Reason.DESTROYED, null, out); return; }
        if (window != null && (!next.attached() || next.window() != window)) { retire(Reason.WINDOW_LOST, null, out); return; }
        boolean changed = facts != null && (facts.attached() != next.attached() || facts.window() != next.window() ||
            facts.width() != next.width() || facts.height() != next.height() || facts.insetsAvailable() != next.insetsAvailable());
        facts = next;
        if (changed && phase != Phase.WAITING_WINDOW) markDirty(out);
    }
    private void markDirty(List<Decision> out) {
        if (epoch == Long.MAX_VALUE) { retire(Reason.EPOCH_EXHAUSTED, null, out); return; }
        epoch++;
        dirty = true;
        out.add(new Decision(Kind.SEAL, lifetime, null, false));
    }
    private void schedule(List<Decision> out) {
        if (phase == Phase.RETIRED || operation != null || drain != null || facts == null || !facts.ready()) return;
        if (phase == Phase.WAITING_WINDOW || phase == Phase.LIVE && dirty) {
            drain = new Token();
            out.add(new Decision(Kind.QUEUE_DRAIN, drain, null, false));
        }
    }
    private void begin(Kind kind, Phase next, List<Decision> out) {
        operation = new Token();
        operationKind = kind;
        operationEpoch = epoch;
        phase = next;
        out.add(new Decision(kind, operation, resource, false));
    }
    private void retire(Reason reason, Object failure, List<Decision> out) {
        if (phase == Phase.RETIRED) return;
        phase = Phase.RETIRED;
        terminalReason = reason;
        primaryFailure = failure;
        presentation = null;
        dirty = true;
        Token queued = drain;
        drain = null;
        out.add(new Decision(Kind.SEAL, lifetime, null, true));
        cancel = new Token();
        unregister = new Token();
        out.add(new Decision(Kind.CANCEL_QUEUED, cancel, queued, true));
        out.add(new Decision(Kind.UNREGISTER, unregister, null, true));
        closeIfIdle(out);
    }
    private void closeIfIdle(List<Decision> out) {
        if (phase == Phase.RETIRED && operation == null && resource != null && close == null) {
            close = new Token();
            out.add(new Decision(Kind.CLOSE, close, resource, true));
        }
    }
    private static List<Decision> batch(List<Decision> out) {
        if (out.size() > MAX_DECISIONS) throw new AssertionError("unbounded owner decision batch");
        return List.copyOf(out);
    }
}
