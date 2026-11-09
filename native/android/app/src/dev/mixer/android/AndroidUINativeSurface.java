package dev.mixer.android;

import android.app.Activity;
import android.widget.FrameLayout;
import java.util.Arrays;
import java.util.Objects;

/** Main-thread external-frame adapter for the explicitly selected retirement V3 profile.
 * One instance owns one lifetime. Allocate a fresh instance after revoke or close.
 * This adapter does not create an engine session or authorize app effects. */
public final class AndroidUINativeSurface implements AutoCloseable {
    /** Enqueue these captured bytes unchanged; do not dispatch app work on this stack. */
    @FunctionalInterface
    public interface Events {
        void enqueue(byte[] owner, byte[] envelope);
    }

    /** Immutable delivery of the existing AndroidUIFrame domain contract. */
    public static final class Frame {
        private final byte[] owner, packet, appearance;

        public Frame(byte[] owner, byte[] packet, byte[] appearance) {
            requireOwner(owner);
            Objects.requireNonNull(packet);
            Objects.requireNonNull(appearance);
            if (packet.length == 0 || packet.length > 1_048_576)
                throw new IllegalArgumentException("native packet byte limit");
            if (appearance.length == 0 || appearance.length > 65_536)
                throw new IllegalArgumentException("appearance descriptor byte limit");
            this.owner = owner.clone();
            this.packet = packet.clone();
            this.appearance = appearance.clone();
        }
    }

    private final Activity activity;
    private final FrameLayout root;
    private final Events events;
    private byte[] identity;
    private NativeOwnerV2 nativeOwner;
    private boolean closed;
    private Throwable closeFailure;

    public AndroidUINativeSurface(Activity activity, FrameLayout root,
                                  AndroidUIProfile profile, Events events) {
        NativeEnvironmentV2.requireMain();
        if (profile != AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3)
            throw new IllegalArgumentException("external surface requires explicit retirement V3 profile");
        this.activity = Objects.requireNonNull(activity);
        this.root = Objects.requireNonNull(root);
        if (root.getContext() != activity) throw new IllegalArgumentException("foreign surface root context");
        this.events = Objects.requireNonNull(events);
    }

    public AndroidUIProfile profile() { return AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3; }

    public void activate(byte[] owner) {
        NativeEnvironmentV2.requireMain();
        if (closed || nativeOwner != null) throw new IllegalStateException("surface lifetime already bound or closed");
        byte[] captured = copyOwner(owner);
        nativeOwner = NativeOwnerV2.external(activity, root, new ExternalFrameSourceV2(envelope -> {
            if (!closed) events.enqueue(captured.clone(), envelope.clone());
        }));
        identity = captured;
    }

    /** Returns only after validation and attachment through the real native owner.
     * A rejected install leaves input gated. No automatic retry is scheduled. */
    public void install(Frame frame) {
        requireActive();
        nativeOwner.gateExternalInput();
        Objects.requireNonNull(frame);
        if (!Arrays.equals(identity, frame.owner)) throw new IllegalStateException("stale surface owner");
        nativeOwner.installExternal(frame.packet, frame.appearance);
    }

    public void gateInput() { NativeEnvironmentV2.requireMain(); if (!closed) { requireActive(); nativeOwner.gateExternalInput(); } }

    public boolean isCurrent() {
        NativeEnvironmentV2.requireMain();
        return !closed && nativeOwner != null && nativeOwner.externalCurrent();
    }

    public void onResume() { NativeEnvironmentV2.requireMain(); if (!closed && nativeOwner != null) nativeOwner.onResume(); }
    public void onPause() { NativeEnvironmentV2.requireMain(); if (!closed && nativeOwner != null) nativeOwner.onPause(); }
    public void onStop() { NativeEnvironmentV2.requireMain(); if (!closed && nativeOwner != null) nativeOwner.onStop(); }

    public void revoke(byte[] owner) {
        NativeEnvironmentV2.requireMain();
        if (identity == null || !Arrays.equals(identity, Objects.requireNonNull(owner)))
            throw new IllegalStateException("stale surface revocation");
        close();
    }

    /** Terminal even when cleanup throws. Retains the owner's exact cleanup state;
     * repeated close never retries an uncertain platform operation. */
    @Override public void close() {
        NativeEnvironmentV2.requireMain();
        if (!closed) {
            closed = true;
            try {
                if (nativeOwner != null) {
                    nativeOwner.close();
                    NativeOwnerV2.CleanupLedger ledger = nativeOwner.cleanupLedger();
                    if (ledger.primary() != null || ledger.coreCompletionUnreported() ||
                        !settled(ledger.handler()) || !settled(ledger.input()) ||
                        !settled(ledger.unregister()) || !settled(ledger.coordinator()) ||
                        !observerSettled(nativeOwner.externalObserver()))
                        throw new IllegalStateException("native surface cleanup failed or remains incomplete", ledger.primary());
                }
            } catch (RuntimeException | Error failure) { closeFailure = failure; }
        }
        if (closeFailure instanceof RuntimeException failure) throw failure;
        if (closeFailure instanceof Error failure) throw failure;
    }

    private void requireActive() {
        NativeEnvironmentV2.requireMain();
        if (closed || nativeOwner == null) throw new IllegalStateException("surface is not active");
    }

    private static byte[] copyOwner(byte[] owner) {
        requireOwner(owner);
        return owner.clone();
    }

    private static void requireOwner(byte[] owner) {
        Objects.requireNonNull(owner);
        if (owner.length == 0 || owner.length > 64) throw new IllegalArgumentException("invalid owner identity length");
    }

    private static boolean settled(NativeOwnerV2.Outcome outcome) {
        return outcome == NativeOwnerV2.Outcome.RETURNED || outcome == NativeOwnerV2.Outcome.NOT_REQUESTED;
    }

    private static boolean observerSettled(NativeEnvironmentV2.Observer observer) {
        if (observer == null) return true;
        NativeEnvironmentV2.Observer.CleanupLedger ledger = observer.cleanupLedger();
        if (ledger.primary() != null || ledger.firstFatal() != null) return false;
        for (int slot = 0; slot < 8; slot++) {
            int state = ledger.state(slot);
            if (state != NativeEnvironmentV2.Observer.UNATTEMPTED &&
                state != NativeEnvironmentV2.Observer.RETURNED) return false;
        }
        return true;
    }
}
