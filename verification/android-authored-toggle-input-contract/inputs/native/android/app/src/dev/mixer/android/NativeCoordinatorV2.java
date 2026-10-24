package dev.mixer.android;

import android.app.Activity;
import android.os.Looper;
import android.widget.FrameLayout;

/** Private ordinary JNI/native owner. Public Activity and signed transport do not use it. */
final class NativeCoordinatorV2 implements AutoCloseable {
    private final Activity activity;
    private final FrameLayout root;
    private final NativeRenderer renderer;
    private long session;
    private byte[] committedPacket;
    private RuntimeException lastNativeInputFailure;
    private boolean active;
    private boolean retired;

    NativeCoordinatorV2(Activity activity, FrameLayout root) {
        requireMain();
        if (activity == null || root == null) throw new IllegalArgumentException("V2 window required");
        this.activity = activity;
        this.root = root;
        renderer = new NativeRenderer(activity, this::nativeInput);
        try {
            session = NativeBridge.create();
            if (session == 0) throw new IllegalStateException("V2 session creation failed");
        } catch (RuntimeException | Error failure) {
            retire(failure);
            throw failure;
        }
    }

    void renderInitial() {
        enter();
        try {
            if (committedPacket != null) throw new IllegalStateException("V2 already initialized");
            transact(0, null, false);
        } finally {
            active = false;
        }
    }

    /** Programmatic ordinary input transaction; the native callback contains retired rejections. */
    void dispatchInput(byte[] envelope) {
        enter();
        try {
            if (committedPacket == null) throw new IllegalStateException("V2 requires initial render");
            transact(1, envelope, true);
        } finally {
            active = false;
        }
    }

    /** Contain an ordinary rejected control edit only after both owners have retired. */
    private void nativeInput(byte[] envelope) {
        requireMain();
        if (active) {
            IllegalStateException failure = new IllegalStateException("V2 reentrant native input");
            retire(failure);
            rethrowNestedError(failure);
            throw failure;
        }
        if (retired) throw new IllegalStateException("V2 coordinator retired");
        try {
            dispatchInput(envelope);
        } catch (RuntimeException failure) {
            if (!retired) throw failure;
            lastNativeInputFailure = failure;
            rethrowNestedError(failure);
        }
    }

    private void transact(int operation, byte[] input, boolean nativeInput) {
        long token = 0;
        boolean prepareAttempted = false;
        boolean delivered = false;
        boolean attachAttempted = false;
        boolean commitAttempted = false;
        boolean knownRejection = false;
        boolean engineClosed = false;
        NativeRenderer.Candidate candidate = null;
        NativeRenderer.AttachmentJournal journal = null;
        try {
            InstalledAppearanceV2 installed = renderer.captureInstalledV2();
            NativeEnvironmentV2 environment = renderer.captureEnvironmentV2(activity, root);
            prepareAttempted = true;
            NativeBridge.Candidate prepared = NativeBridge.prepareV2(session, operation, input);
            // Retain the opaque bit pattern before any defensive packet-copy allocation.
            token = prepared.token();
            if (token == 0) throw new IllegalStateException("V2 invalid engine token");
            delivered = true;
            byte[] packet = prepared.packet();
            candidate = renderer.prepareV2(packet, installed, environment);
            if (!environment.current(renderer))
                throw new IllegalStateException("V2 environment changed during preparation");
            attachAttempted = true;
            journal = renderer.attachV2(candidate, root);
            renderer.validateAttachedV2(candidate, journal);
            commitAttempted = true;
            int status = NativeBridge.commitV2(session, token);
            if (status == 0) {
                // No callbacks, captures, allocations or native mutation between these calls.
                renderer.finishV2(candidate, journal);
                committedPacket = packet;
                return;
            }
            knownRejection = status >= 1 && status <= 7;
            engineClosed = status == 2;
            throw new IllegalStateException("V2 engine commit rejected: " + status);
        } catch (RuntimeException | Error failure) {
            // A reentrant native callback may already have retired both owned sides.
            if (retired) throw failure;
            // JNI delivery can destroy the session; a thrown commit may already have committed.
            boolean unknown = (prepareAttempted && !delivered)
                || (commitAttempted && !knownRejection);
            boolean mustRetire = unknown || engineClosed || nativeInput || !prepareAttempted;
            boolean abortConfirmed = false;
            Throwable abortFailure = null;
            Throwable cleanupFailure = null;
            if (!unknown && token != 0) {
                try {
                    abortConfirmed = NativeBridge.abortV2(session, token) == 0;
                } catch (RuntimeException | Error cleanup) {
                    abortFailure = cleanup;
                }
                if (!abortConfirmed) mustRetire = true;
            }
            // An attach throw may precede its consuming catch. Null journal proves nothing.
            if (attachAttempted && journal == null) mustRetire = true;
            else if (!unknown && abortConfirmed && !engineClosed && candidate != null) {
                try {
                    if (journal != null) renderer.rollbackV2(candidate, journal);
                    else renderer.discardV2(candidate);
                } catch (RuntimeException | Error cleanup) {
                    cleanupFailure = cleanup;
                    mustRetire = true;
                }
            }
            if (mustRetire) retire(failure);
            suppress(failure, abortFailure);
            suppress(failure, cleanupFailure);
            throw failure;
        }
    }

    /** Reapply exactly the retained packet using a fresh concrete capture; no engine transaction. */
    void refreshEnvironment() {
        enter();
        try {
            if (committedPacket == null) throw new IllegalStateException("V2 requires initial render");
            NativeRenderer.Candidate candidate = null;
            NativeRenderer.AttachmentJournal journal = null;
            boolean attachAttempted = false;
            boolean finishAttempted = false;
            try {
                InstalledAppearanceV2 installed = renderer.captureInstalledV2();
                NativeEnvironmentV2 environment = renderer.captureEnvironmentV2(activity, root);
                candidate = renderer.prepareV2(committedPacket, installed, environment);
                if (!environment.current(renderer))
                    throw new IllegalStateException("V2 environment changed during preparation");
                attachAttempted = true;
                journal = renderer.attachV2(candidate, root);
                renderer.validateAttachedV2(candidate, journal);
                finishAttempted = true;
                renderer.finishV2(candidate, journal);
            } catch (RuntimeException | Error failure) {
                if (retired) throw failure;
                Throwable cleanupFailure = null;
                // Never guess whether a throwing attach or finish consumed its candidate.
                if (!finishAttempted && candidate != null && (!attachAttempted || journal != null)) {
                    try {
                        if (journal != null) renderer.rollbackV2(candidate, journal);
                        else renderer.discardV2(candidate);
                    } catch (RuntimeException | Error cleanup) {
                        cleanupFailure = cleanup;
                    }
                }
                // A stale/unsupported environment cannot reopen an old capture as current.
                retire(failure);
                suppress(failure, cleanupFailure);
                throw failure;
            }
        } finally {
            active = false;
        }
    }

    boolean isRetired() { requireMain(); return retired; }
    boolean hasCommittedPresentation() { requireMain(); return !retired && committedPacket != null; }
    RuntimeException lastNativeInputFailure() { requireMain(); return lastNativeInputFailure; }

    @Override public void close() {
        enter();
        try {
            retire(null);
        } finally {
            active = false;
        }
    }

    private void enter() {
        requireMain();
        if (retired) throw new IllegalStateException("V2 coordinator retired");
        if (active) throw new IllegalStateException("V2 coordinator reentrant call");
        active = true;
    }

    private static void requireMain() {
        if (Looper.myLooper() != Looper.getMainLooper())
            throw new IllegalStateException("V2 coordinator requires main Looper");
    }

    /** Publish closure first, then attempt both owners even if either disposal fails. */
    private void retire(Throwable primary) {
        if (retired) return;
        retired = true;
        committedPacket = null;
        long ownedSession = session;
        session = 0;
        Throwable nativeFailure = null;
        Throwable engineFailure = null;
        try {
            renderer.disposeV2();
        } catch (RuntimeException | Error failure) {
            nativeFailure = failure;
        }
        try {
            if (ownedSession != 0) NativeBridge.destroy(ownedSession);
        } catch (RuntimeException | Error failure) {
            engineFailure = failure;
        }
        if (primary != null) {
            suppress(primary, nativeFailure);
            suppress(primary, engineFailure);
        } else if (nativeFailure != null) {
            suppress(nativeFailure, engineFailure);
            if (nativeFailure instanceof RuntimeException runtime) throw runtime;
            throw (Error) nativeFailure;
        } else if (engineFailure instanceof RuntimeException runtime) {
            throw runtime;
        } else if (engineFailure != null) {
            throw (Error) engineFailure;
        }
    }

    private static void suppress(Throwable primary, Throwable secondary) {
        if (secondary != null && secondary != primary) primary.addSuppressed(secondary);
    }

    /** A RuntimeException wrapper must not turn a cleanup Error/OOM into an ordinary rejection. */
    private static void rethrowNestedError(Throwable failure) {
        java.util.ArrayDeque<Throwable> pending = new java.util.ArrayDeque<>();
        java.util.IdentityHashMap<Throwable, Boolean> seen = new java.util.IdentityHashMap<>();
        pending.add(failure);
        while (!pending.isEmpty()) {
            Throwable current = pending.removeFirst();
            if (seen.put(current, Boolean.TRUE) != null) continue;
            if (current instanceof Error fatal) throw fatal;
            Throwable cause = current.getCause();
            if (cause != null) pending.add(cause);
            for (Throwable secondary : current.getSuppressed()) pending.add(secondary);
        }
    }
}
