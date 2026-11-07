package dev.mixer.android;

import android.app.Activity;
import android.os.Looper;
import android.widget.FrameLayout;

/** Private transaction owner. Construction acquires no engine session or native presentation. */
final class NativeCoordinatorV2 {
    enum Outcome { NOT_REQUESTED, ATTEMPTED, RETURNED, FAILED_UNCERTAIN }
    static final class CleanupLedger {
        private Outcome renderer = Outcome.NOT_REQUESTED, engine = Outcome.NOT_REQUESTED;
        private Throwable rendererFailure, engineFailure, primary;
        private Error firstFatal;
        Outcome renderer() { requireMain(); return renderer; }
        Outcome engine() { requireMain(); return engine; }
        Throwable rendererFailure() { requireMain(); return rendererFailure; }
        Throwable engineFailure() { requireMain(); return engineFailure; }
        Throwable primary() { requireMain(); return primary; }
        Error firstFatal() { requireMain(); return firstFatal; }
    }
    private final Activity activity;
    private final FrameLayout root;
    private final NativeRenderer renderer;
    private final NativeOwnerV2.Fence fence;
    private final CleanupLedger ledger = new CleanupLedger();
    private long session;
    private byte[] committedPacket;
    private boolean active, retired, disposed, cancellation;
    private long cancellationSerial, requestedSerial;
    private OwnerLifecycleV2.Token operation;

    NativeCoordinatorV2(Activity activity, FrameLayout root, NativeEnvironmentV2.Observer observer,
                        NativeOwnerV2.Fence fence, NativeRenderer.Events nativeInput) {
        requireMain();
        if (activity == null || root == null || observer == null || fence == null || nativeInput == null ||
            observer.activity != activity || observer.root != root)
            throw new IllegalArgumentException("V2 bound window required");
        this.activity = activity; this.root = root; this.fence = fence;
        renderer = new NativeRenderer(activity, nativeInput, observer, fence);
        observer.bindRenderer(renderer);
    }
    void renderInitial() {
        enter();
        try {
            if (session != 0 || committedPacket != null) throw new IllegalStateException("V2 already initialized");
            session = NativeBridge.create();
            checkOperation();
            if (session == 0) throw new IllegalStateException("V2 session creation failed");
            transact(0, null);
        } catch (RuntimeException | Error failure) { remember(failure); retireScalar(); throw failure; }
        finally { leave(); }
    }
    void dispatchInput(byte[] envelope) {
        enter();
        try {
            if (committedPacket == null) throw new IllegalStateException("V2 requires initial render");
            transact(1, envelope);
        } catch (RuntimeException | Error failure) { remember(failure); retireScalar(); throw failure; }
        finally { leave(); }
    }
    private void transact(int engineOperation, byte[] input) {
        long token = 0;
        boolean prepareAttempted = false, delivered = false, commitAttempted = false, knownRejection = false;
        NativeRenderer.Candidate candidate = null;
        NativeRenderer.AttachmentJournal journal = null;
        try {
            InstalledAppearanceV2 installed = renderer.captureInstalledV2(); checkOperation();
            NativeEnvironmentV2 environment = renderer.captureEnvironmentV2(activity, root); checkOperation();
            prepareAttempted = true;
            NativeBridge.Candidate prepared = NativeBridge.prepareV2(session, engineOperation, input);
            token = prepared.token();
            delivered = true; checkOperation();
            if (token == 0) throw new IllegalStateException("V2 invalid engine token");
            byte[] packet = prepared.packet();
            candidate = renderer.prepareV2(packet, installed, environment); checkOperation();
            if (!environment.current(renderer)) throw new IllegalStateException("V2 environment changed during preparation");
            checkOperation();
            journal = renderer.attachV2(candidate, root); checkOperation();
            renderer.validateAttachedV2(candidate, journal); checkOperation();
            commitAttempted = true;
            fence.commitFinish = true;
            try {
                int status = NativeBridge.commitV2(session, token);
                if (status == 0) {
                    renderer.finishV2(candidate, journal);
                    committedPacket = packet;
                    return;
                }
                knownRejection = status >= 1 && status <= 7;
                throw new IllegalStateException("V2 engine commit rejected: " + status);
            } finally { fence.commitFinish = false; }
        } catch (RuntimeException | Error failure) {
            remember(failure);
            try { renderer.reportDeferredTerminalV2(); } catch (RuntimeException | Error cleanup) { remember(cleanup); }
            boolean unknown = prepareAttempted && !delivered || commitAttempted && !knownRejection;
            if (!unknown && token != 0) {
                try { if (NativeBridge.abortV2(session, token) != 0) retireScalar(); }
                catch (RuntimeException | Error cleanup) { remember(cleanup); }
            }
            if (!fence.terminal && !unknown && candidate != null) {
                try {
                    if (journal != null) renderer.rollbackV2(candidate, journal);
                    else renderer.discardV2(candidate);
                } catch (RuntimeException | Error cleanup) { remember(cleanup); }
            }
            retireScalar();
            if (ledger.firstFatal != null) throw ledger.firstFatal;
            throw failure;
        }
    }
    /** Uses this exact retained byte[] and performs no engine operation or revision advance. */
    void refreshEnvironment() {
        enter();
        try {
            if (committedPacket == null) throw new IllegalStateException("V2 requires initial render");
            InstalledAppearanceV2 installed = renderer.captureInstalledV2(); checkOperation();
            NativeEnvironmentV2 environment = renderer.captureEnvironmentV2(activity, root); checkOperation();
            NativeRenderer.Candidate candidate = renderer.prepareV2(committedPacket, installed, environment); checkOperation();
            if (!environment.current(renderer)) throw new IllegalStateException("V2 environment changed during refresh");
            NativeRenderer.AttachmentJournal journal = renderer.attachV2(candidate, root); checkOperation();
            renderer.validateAttachedV2(candidate, journal); checkOperation();
            renderer.finishV2(candidate, journal);
        } catch (RuntimeException | Error failure) {
            remember(failure); retireScalar();
            try { renderer.reportDeferredTerminalV2(); } catch (RuntimeException | Error cleanup) { remember(cleanup); }
            if (ledger.firstFatal != null) throw ledger.firstFatal;
            throw failure;
        } finally { leave(); }
    }
    void sealGatesScalar() { renderer.sealScalarV2(); }
    void cancelInputFromOwner(long serial) {
        requireMain();
        if (serial != fence.sealSerial || fence.drawAllowed || fence.inputAllowed)
            throw new IllegalStateException("V2 cancellation requires exact sealed serial");
        if (serial > requestedSerial) requestedSerial = serial;
        if (cancellation || serial <= cancellationSerial) return;
        cancellation = true;
        try {
            cancellationSerial = serial;
            renderer.cancelInputV2(serial);
            cancellationSerial = requestedSerial;
        } catch (RuntimeException | Error failure) { remember(failure); throw failure; }
        finally { cancellation = false; }
    }
    boolean busyForOwnerDisposal() { requireMain(); return active || cancellation || fence.rendererReportActive; }
    boolean isRetired() { requireMain(); return retired; }
    boolean hasCommittedPresentation() { requireMain(); return !retired && committedPacket != null; }
    CleanupLedger cleanupLedger() { requireMain(); return ledger; }
    void closeFromOwner() {
        requireMain();
        if (busyForOwnerDisposal()) throw new IllegalStateException("V2 coordinator disposal deferred");
        retireScalar(); disposeOnce();
        if (ledger.firstFatal != null) throw ledger.firstFatal;
        if (ledger.primary instanceof RuntimeException failure) throw failure;
    }
    private void enter() {
        requireMain();
        if (retired || fence.terminal) throw new IllegalStateException("V2 coordinator retired");
        if (active || cancellation || fence.rendererReportActive) throw new IllegalStateException("V2 coordinator reentrant call");
        operation = fence.operation;
        if (operation == null) throw new IllegalStateException("V2 owner operation required");
        active = true; sealGatesScalar();
    }
    private void checkOperation() {
        if (fence.terminal || operation == null || operation != fence.operation)
            throw new IllegalStateException("V2 transaction authority lost");
    }
    private void leave() {
        active = false; operation = null;
        if (retired && !cancellation && !fence.rendererReportActive) disposeOnce();
        if (ledger.firstFatal != null) throw ledger.firstFatal;
    }
    private void retireScalar() {
        retired = true; fence.terminal = true; fence.drawAllowed = false; fence.inputAllowed = false;
        sealGatesScalar(); committedPacket = null;
    }
    private void disposeOnce() {
        if (disposed) return;
        disposed = true;
        long owned = session; session = 0; committedPacket = null;
        ledger.renderer = Outcome.ATTEMPTED;
        try { renderer.disposeV2(); ledger.renderer = Outcome.RETURNED; }
        catch (RuntimeException | Error failure) { ledger.rendererFailure = failure; ledger.renderer = Outcome.FAILED_UNCERTAIN; remember(failure); }
        if (owned != 0) {
            ledger.engine = Outcome.ATTEMPTED;
            try { NativeBridge.destroy(owned); ledger.engine = Outcome.RETURNED; }
            catch (RuntimeException | Error failure) { ledger.engineFailure = failure; ledger.engine = Outcome.FAILED_UNCERTAIN; remember(failure); }
        }
    }
    private void remember(Throwable failure) {
        if (failure == null) return;
        if (ledger.primary == null) ledger.primary = failure;
        if (failure instanceof Error fatal && ledger.firstFatal == null) ledger.firstFatal = fatal;
    }
    private static void requireMain() {
        if (Looper.myLooper() != Looper.getMainLooper()) throw new IllegalStateException("V2 coordinator requires main Looper");
    }
}
