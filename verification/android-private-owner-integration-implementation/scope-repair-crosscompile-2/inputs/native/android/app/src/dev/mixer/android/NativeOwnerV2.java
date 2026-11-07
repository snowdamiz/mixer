package dev.mixer.android;

import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import android.view.Window;
import android.widget.FrameLayout;
import java.util.List;
import java.util.Objects;

/** Private main-thread lifetime. This adapter owns effects; the core owns decisions. */
final class NativeOwnerV2 implements AutoCloseable, NativeEnvironmentV2.Sink {
    static final class Fence {
        boolean terminal, drawAllowed, inputAllowed, commitFinish, rendererReportActive;
        long sealSerial = 1;
        OwnerLifecycleV2.Token operation, presentation;
    }
    enum Outcome { NOT_REQUESTED, DEFERRED, IN_PROGRESS, ATTEMPTED, RETURNED, FAILED_UNCERTAIN }
    enum Cause { CLOSED, DETACHED, REGISTRATION_FAILED, OBSERVER_EXHAUSTED,
        RENDERER_TERMINAL, SEAL_SERIAL_EXHAUSTED, SCHEDULING_FAILED, OPERATION_FAILED, CORE_FAILURE }
    static final class CleanupLedger {
        private Throwable primary;
        private Error firstFatal;
        private Cause cause;
        private NativeEnvironmentV2.RendererCause rendererCause;
        private Outcome handler = Outcome.NOT_REQUESTED, input = Outcome.NOT_REQUESTED,
            unregister = Outcome.NOT_REQUESTED, coordinator = Outcome.NOT_REQUESTED;
        private Throwable handlerFailure, inputFailure, unregisterFailure, coordinatorFailure;
        private boolean coreCompletionUnreported;
        Throwable primary() { requireMain(); return primary; }
        Error firstFatal() { requireMain(); return firstFatal; }
        Cause cause() { requireMain(); return cause; }
        NativeEnvironmentV2.RendererCause rendererCause() { requireMain(); return rendererCause; }
        Outcome handler() { requireMain(); return handler; }
        Outcome input() { requireMain(); return input; }
        Outcome unregister() { requireMain(); return unregister; }
        Outcome coordinator() { requireMain(); return coordinator; }
        Throwable handlerFailure() { requireMain(); return handlerFailure; }
        Throwable inputFailure() { requireMain(); return inputFailure; }
        Throwable unregisterFailure() { requireMain(); return unregisterFailure; }
        Throwable coordinatorFailure() { requireMain(); return coordinatorFailure; }
        boolean coreCompletionUnreported() { requireMain(); return coreCompletionUnreported; }
    }
    private record WindowIdentity(Window window, Object token) {}
    private enum WorkKind { DRAIN, TERMINAL_CLOSE }
    private final class Work implements Runnable {
        final WorkKind kind;
        final OwnerLifecycleV2.Token token;
        final NativeCoordinatorV2 resource;
        boolean posting, cancellationPending;
        OwnerLifecycleV2.Token cancellationToken;
        Work(WorkKind kind, OwnerLifecycleV2.Token token, NativeCoordinatorV2 resource) {
            this.kind = kind; this.token = token; this.resource = resource;
        }
        @Override public void run() {
            requireMain();
            if (queued != this) return;
            queued = null; // consume before any callback or concrete probe
            try {
                if (kind == WorkKind.TERMINAL_CLOSE) {
                    if (pendingCloseResource != resource || pendingCloseToken != token) return;
                    closePending();
                } else {
                    if (fence.terminal || token == null || core.snapshot().pendingDrain() != token) return;
                    seal(false);
                    if (!fence.terminal) seedFocus();
                    if (!fence.terminal) process(core.drain(lifetime, token, probeWindow()), null);
                }
            } catch (RuntimeException | Error failure) { fail(failure, Cause.CORE_FAILURE); }
            finally { settle(); }
            throwFatal();
        }
    }
    private final Activity activity;
    private final FrameLayout root;
    private final Handler handler;
    private final Runnable completionFault;
    private final OwnerLifecycleV2 core;
    private final OwnerLifecycleV2.Token lifetime;
    private final Fence fence = new Fence();
    private final CleanupLedger ledger = new CleanupLedger();
    private NativeEnvironmentV2.Observer observer;
    private NativeCoordinatorV2 opening, coordinator;
    private Work queued;
    private WindowIdentity window;
    private OwnerLifecycleV2.Token activeOperation, pendingUnregister, pendingCloseToken;
    private NativeCoordinatorV2 pendingCloseResource;
    private boolean started, registering, terminalProcessed, focusKnown, lastFocus, emergency;
    private int effectDepth;

    NativeOwnerV2(Activity activity, FrameLayout root) { this(activity,root,null); }
    /** Host-only fault at the completion-bookkeeping boundary; production always supplies null. */
    NativeOwnerV2(Activity activity, FrameLayout root, Runnable completionFault) {
        requireMain();
        this.completionFault=completionFault;
        this.activity = Objects.requireNonNull(activity);
        this.root = Objects.requireNonNull(root);
        if (root.getContext() != activity) throw new IllegalArgumentException("foreign V2 root context");
        handler = new Handler(Looper.getMainLooper());
        core = new OwnerLifecycleV2(NativeOwnerV2::requireMain, activity, root);
        lifetime = core.lifetime();
    }
    void start() {
        requireMain();
        if (started || fence.terminal) throw new IllegalStateException("V2 owner start is one shot");
        started = true;
        try {
            observer = new NativeEnvironmentV2.Observer(activity, root, this);
            registering = true;
            try { observer.register(); } finally { registering = false; unregisterPending(); }
            if (!fence.terminal) {
                seal(false);
                if (!fence.terminal) seedFocus();
                if (!fence.terminal) process(core.windowChanged(lifetime, probeWindow()), null);
            }
        } catch (RuntimeException | Error failure) { fail(failure, Cause.REGISTRATION_FAILED); }
        finally { settle(); }
        throwFatal();
    }
    void onResume() {
        requireMain(); if (fence.terminal) return;
        try {
            seal(false);
            if (!fence.terminal) process(core.resume(lifetime), null);
            if (!fence.terminal) seedFocus();
            if (!fence.terminal) process(core.windowChanged(lifetime, probeWindow()), null);
        }
        catch (RuntimeException | Error failure) { fail(failure, Cause.CORE_FAILURE); }
        finally { settle(); }
        throwFatal();
    }
    void onPause() {
        requireMain(); if (fence.terminal) return;
        try { seal(false); process(core.pause(lifetime), null); }
        catch (RuntimeException | Error failure) { fail(failure, Cause.CORE_FAILURE); }
        finally { settle(); }
        throwFatal();
    }
    void onStop() {
        requireMain(); if (fence.terminal) return;
        try { seal(false); process(core.stop(lifetime), null); }
        catch (RuntimeException | Error failure) { fail(failure, Cause.CORE_FAILURE); }
        finally { settle(); }
        throwFatal();
    }
    @Override public void close() {
        requireMain();
        if (!terminalProcessed) terminate(Cause.CLOSED, null, null, null, NativeEnvironmentV2.Change.EPOCH_EXHAUSTED);
        settle(); throwFatal();
    }
    @Override public void changed(NativeEnvironmentV2.Observer source, NativeEnvironmentV2.Change change,
                                   NativeEnvironmentV2.RendererCause rendererCause, Throwable primary, Error firstFatal) {
        requireMain();
        if (source != observer || change == null) throw new IllegalArgumentException("foreign V2 observer notice");
        if (terminalProcessed) return;
        if (change != NativeEnvironmentV2.Change.INVALIDATED) {
            Cause cause = switch (change) {
                case DETACHED -> Cause.DETACHED;
                case REGISTRATION_FAILED -> Cause.REGISTRATION_FAILED;
                case RENDERER_TERMINAL -> Cause.RENDERER_TERMINAL;
                default -> Cause.OBSERVER_EXHAUSTED;
            };
            terminate(cause, rendererCause, primary, firstFatal, change);
        } else {
            try {
                seal(false);
                if (!fence.terminal) { seedFocus(); process(core.invalidate(lifetime), null); process(core.windowChanged(lifetime, probeWindow()), null); }
            } catch (RuntimeException | Error failure) { fail(failure, Cause.CORE_FAILURE); }
        }
        settle(); throwFatal();
    }
    boolean hasCommittedPresentation() {
        requireMain(); return !fence.terminal && fence.presentation != null && coordinator != null && coordinator.hasCommittedPresentation();
    }
    CleanupLedger cleanupLedger() { requireMain(); return ledger; }

    private void nativeInput(byte[] envelope) {
        requireMain();
        if (fence.terminal || activeOperation != null || !fence.inputAllowed) return;
        try {
            OwnerLifecycleV2.Token admitted = fence.presentation;
            seal(false);
            if (!fence.terminal && activeOperation == null && admitted != null && admitted == fence.presentation) {
                seedFocus();
                // The barrier intentionally closed inputAllowed. Only the same real core presentation can admit input.
                if (!fence.terminal && activeOperation == null && admitted == fence.presentation && core.admitsInput(lifetime, admitted))
                    process(core.dispatchInput(lifetime, admitted), envelope); // bytes never leave this synchronous stack
            }
        } catch (RuntimeException failure) {
            fail(failure, Cause.OPERATION_FAILED);
            if (!(fence.terminal && coordinator != null && coordinator.isRetired())) throw failure;
        } catch (Error fatal) { fail(fatal, Cause.OPERATION_FAILED); throw fatal; }
        finally { settle(); }
        throwFatal();
    }
    private void seedFocus() {
        if (fence.terminal) return;
        boolean actual = root.hasWindowFocus();
        if (fence.terminal) return;
        if (!focusKnown || actual != lastFocus) {
            focusKnown = true; lastFocus = actual;
            process(core.focusChanged(lifetime, actual), null);
        }
    }
    private OwnerLifecycleV2.WindowFacts probeWindow() {
        boolean destroyed = activity.isDestroyed(), attached = root.isAttachedToWindow();
        Window actual = activity.getWindow(); Object token = root.getWindowToken();
        if (actual == null || token == null) window = null;
        else if (window == null || window.window() != actual || window.token() != token) window = new WindowIdentity(actual, token);
        return new OwnerLifecycleV2.WindowFacts(activity, root, destroyed, attached,
            observer != null && observer.ready() ? window : null, root.getWidth(), root.getHeight(), root.getRootWindowInsets() != null);
    }
    /** No callbacks or core work precede this barrier. */
    private void seal(boolean terminal) {
        if (terminal) fence.terminal = true;
        fence.drawAllowed = false; fence.inputAllowed = false;
        if (opening != null) opening.sealGatesScalar();
        if (coordinator != null && coordinator != opening) coordinator.sealGatesScalar();
        if (fence.sealSerial == Long.MAX_VALUE) {
            fence.terminal = true;
            if (ledger.cause == null) ledger.cause = Cause.SEAL_SERIAL_EXHAUSTED;
        } else fence.sealSerial++;
        cancelInput();
        if (fence.terminal && !terminalProcessed) terminate(Cause.SEAL_SERIAL_EXHAUSTED, null, null, null, NativeEnvironmentV2.Change.EPOCH_EXHAUSTED);
    }
    private void cancelInput() {
        effectDepth++;
        try {
            if (opening != null) cancelInput(opening);
            if (coordinator != null && coordinator != opening) cancelInput(coordinator);
        } finally { effectDepth--; }
    }
    private void cancelInput(NativeCoordinatorV2 owned) {
        ledger.input = Outcome.IN_PROGRESS;
        try {
            owned.cancelInputFromOwner(fence.sealSerial);
            ledger.input = owned.inputCancellationInProgress() ? Outcome.IN_PROGRESS : Outcome.RETURNED;
        } catch (RuntimeException | Error failure) {
            ledger.input = Outcome.FAILED_UNCERTAIN; ledger.inputFailure = failure; remember(failure);
        }
    }
    private void terminate(Cause cause, NativeEnvironmentV2.RendererCause rendererCause, Throwable primary,
                           Error firstFatal, NativeEnvironmentV2.Change change) {
        if (terminalProcessed) return;
        fence.terminal = true; fence.drawAllowed = false; fence.inputAllowed = false;
        if (opening != null) opening.sealGatesScalar();
        if (coordinator != null && coordinator != opening) coordinator.sealGatesScalar();
        terminalProcessed = true;
        if (ledger.cause == null) ledger.cause = cause;
        ledger.rendererCause = rendererCause;
        remember(primary); remember(firstFatal);
        if (fence.sealSerial != Long.MAX_VALUE) fence.sealSerial++;
        cancelInput();
        try {
            process(switch (change) {
                case DETACHED -> core.detached(lifetime);
                case REGISTRATION_FAILED -> core.registrationFailed(lifetime, primary);
                default -> core.close(lifetime);
            }, null);
        } catch (RuntimeException | Error failure) { fallback(failure); }
    }
    private void process(List<OwnerLifecycleV2.Decision> decisions, byte[] input) {
        for (OwnerLifecycleV2.Decision decision : decisions) {
            switch (decision.kind()) {
                case SEAL -> {
                    if (decision.terminal()) fence.terminal = true;
                    fence.drawAllowed = false; fence.inputAllowed = false;
                    if (opening != null) opening.sealGatesScalar();
                    if (coordinator != null && coordinator != opening) coordinator.sealGatesScalar();
                    if (decision.terminal()) {
                        terminalProcessed = true;
                        if (ledger.cause == null) ledger.cause = Cause.OPERATION_FAILED;
                    }
                }
                case QUEUE_DRAIN -> {
                    if (!fence.terminal && core.snapshot().pendingDrain() == decision.token() && queued == null)
                        post(new Work(WorkKind.DRAIN, decision.token(), null));
                }
                case CANCEL_QUEUED -> cancelQueued(decision.token());
                case UNREGISTER -> { pendingUnregister = decision.token(); if (observer != null) observer.retireScalarFromOwner(); unregisterPending(); }
                case CLOSE -> {
                    if (decision.resource() instanceof NativeCoordinatorV2 owned) {
                        pendingCloseToken = decision.token(); pendingCloseResource = owned;
                        ledger.coordinator = Outcome.DEFERRED;
                    }
                }
                case OPEN_INITIAL, REFRESH_COMMITTED, DISPATCH_INPUT -> {
                    if (!fence.terminal && activeOperation == null && core.permits(decision.token())) operate(decision, input);
                }
            }
        }
    }
    private void operate(OwnerLifecycleV2.Decision decision, byte[] input) {
        activeOperation = decision.token(); fence.operation = decision.token();
        NativeCoordinatorV2 owned = coordinator;
        Throwable failure = null; boolean committed = false;
        effectDepth++;
        try {
            if (decision.kind() == OwnerLifecycleV2.Kind.OPEN_INITIAL) {
                owned = new NativeCoordinatorV2(activity, root, observer, fence, this::nativeInput);
                opening = owned;
                owned.sealGatesScalar();
                if (!fence.terminal) owned.renderInitial();
            } else if (decision.resource() != owned || owned == null) throw new IllegalStateException("foreign coordinator effect");
            else if (decision.kind() == OwnerLifecycleV2.Kind.REFRESH_COMMITTED) owned.refreshEnvironment();
            else owned.dispatchInput(input);
            committed = !fence.terminal && owned != null && owned.hasCommittedPresentation();
        } catch (RuntimeException | Error caught) {
            failure = caught;
            if (owned != null) remember(owned.cleanupLedger().primary());
            remember(caught);
        }
        finally {
            effectDepth--;
            try {
                if(completionFault!=null)completionFault.run();
                List<OwnerLifecycleV2.Decision> completion = core.complete(activeOperation, owned, committed, failure);
                if (owned != null) coordinator = owned;
                process(completion, null);
                publish();
            } catch (RuntimeException | Error caught) { fallback(caught); }
            finally { opening = null; activeOperation = null; fence.operation = null; }
        }
        if (failure != null && !fence.terminal) fail(failure, Cause.OPERATION_FAILED);
    }
    private void publish() {
        OwnerLifecycleV2.Snapshot state = core.snapshot();
        if (!fence.terminal && state.phase() == OwnerLifecycleV2.Phase.LIVE && !state.dirty()) {
            fence.presentation = state.presentation(); fence.drawAllowed = true;
            fence.inputAllowed = state.foreground() && state.focused();
        } else { fence.drawAllowed = false; fence.inputAllowed = false; }
    }
    private void post(Work work) {
        queued = work; work.posting = true;
        try {
            if (!handler.post(work)) throw new IllegalStateException("main Handler rejected V2 work");
        } catch (RuntimeException | Error failure) {
            remember(failure);
            if (work.kind == WorkKind.TERMINAL_CLOSE) {
                if (queued == work) queued = null;
                work.cancellationPending = true;
                ledger.handler = Outcome.DEFERRED;
                ledger.coordinator = Outcome.DEFERRED; return;
            }
            terminate(Cause.SCHEDULING_FAILED, null, failure, failure instanceof Error fatal ? fatal : null, NativeEnvironmentV2.Change.EPOCH_EXHAUSTED);
        } finally {
            work.posting = false;
            // A callback may consume/cancel the slot before Handler.post acquires its native queue entry.
            if (work.cancellationPending || queued != work) {
                OwnerLifecycleV2.Token token = work.cancellationToken;
                work.cancellationToken = null; work.cancellationPending = false;
                removeWork(work, token);
            }
        }
    }
    private void cancelQueued(OwnerLifecycleV2.Token token) {
        Work owned = queued; queued = null;
        if (owned != null && owned.posting) {
            owned.cancellationPending = true; owned.cancellationToken = token;
            ledger.handler = Outcome.DEFERRED; return;
        }
        removeWork(owned, token);
    }
    private void removeWork(Work owned, OwnerLifecycleV2.Token token) {
        ledger.handler = Outcome.ATTEMPTED;
        Throwable failure = null;
        try { if (owned != null) handler.removeCallbacks(owned); ledger.handler = Outcome.RETURNED; }
        catch (RuntimeException | Error caught) { failure = caught; ledger.handlerFailure = caught; ledger.handler = Outcome.FAILED_UNCERTAIN; remember(caught); }
        completeCleanup(token, failure);
    }
    private void unregisterPending() {
        if (pendingUnregister == null && !emergency) return;
        if (registering) { ledger.unregister = Outcome.DEFERRED; return; }
        if (ledger.unregister == Outcome.RETURNED || ledger.unregister == Outcome.FAILED_UNCERTAIN) return;
        OwnerLifecycleV2.Token token = pendingUnregister; pendingUnregister = null;
        ledger.unregister = Outcome.ATTEMPTED;
        Throwable failure = null; effectDepth++;
        try { if (observer != null) observer.close(); ledger.unregister = Outcome.RETURNED; }
        catch (RuntimeException | Error caught) { failure = caught; ledger.unregisterFailure = caught; ledger.unregister = Outcome.FAILED_UNCERTAIN; remember(caught); }
        finally { effectDepth--; }
        completeCleanup(token, failure);
    }
    private void closePending() {
        NativeCoordinatorV2 owned = pendingCloseResource;
        if (owned == null) return;
        if (effectDepth != 0 || activeOperation != null || owned.busyForOwnerDisposal()) { ledger.coordinator = Outcome.DEFERRED; return; }
        OwnerLifecycleV2.Token token = pendingCloseToken;
        pendingCloseResource = null; pendingCloseToken = null;
        ledger.coordinator = Outcome.ATTEMPTED;
        Throwable failure = null;
        try { owned.closeFromOwner(); ledger.coordinator = Outcome.RETURNED; }
        catch (RuntimeException | Error caught) { failure = caught; ledger.coordinatorFailure = caught; ledger.coordinator = Outcome.FAILED_UNCERTAIN; remember(caught); }
        completeCleanup(token, failure);
    }
    private void settle() {
        unregisterPending();
        if (pendingCloseResource == null || effectDepth != 0 || activeOperation != null) return;
        if (pendingCloseResource.busyForOwnerDisposal()) {
            if (queued == null) post(new Work(WorkKind.TERMINAL_CLOSE, pendingCloseToken, pendingCloseResource));
        } else closePending();
    }
    private void completeCleanup(OwnerLifecycleV2.Token token, Throwable failure) {
        if (token == null || emergency) return;
        try { core.cleanupComplete(token, failure); }
        catch (RuntimeException | Error caught) { fallback(caught); }
    }
    private void fail(Throwable failure, Cause cause) {
        remember(failure);
        if (!terminalProcessed) terminate(cause, null, failure, failure instanceof Error fatal ? fatal : null, NativeEnvironmentV2.Change.EPOCH_EXHAUSTED);
    }
    private void fallback(Throwable failure) {
        fence.terminal = true; fence.drawAllowed = false; fence.inputAllowed = false;
        if (opening != null) opening.sealGatesScalar();
        if (coordinator != null && coordinator != opening) coordinator.sealGatesScalar();
        terminalProcessed = true; emergency = true; ledger.coreCompletionUnreported = true;
        if (observer != null) observer.retireScalarFromOwner();
        if (ledger.cause == null) ledger.cause = Cause.CORE_FAILURE;
        remember(failure); cancelInput();
        cancelQueued(null); unregisterPending();
        if (pendingCloseResource == null) pendingCloseResource = opening != null ? opening : coordinator;
    }
    private void remember(Throwable failure) {
        if (failure == null) return;
        if (ledger.primary == null) ledger.primary = failure;
        if (failure instanceof Error fatal && ledger.firstFatal == null) ledger.firstFatal = fatal;
    }
    private void throwFatal() { if (ledger.firstFatal != null) throw ledger.firstFatal; }
    static void requireMain() {
        if (Looper.myLooper() != Looper.getMainLooper()) throw new IllegalStateException("V2 owner requires main Looper");
    }
}
