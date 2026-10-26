package dev.mixer.android;

import android.app.Activity;
import android.content.ComponentCallbacks;
import android.content.ContentResolver;
import android.content.res.Configuration;
import android.database.ContentObserver;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.view.View;
import android.view.ViewTreeObserver;
import android.widget.FrameLayout;
import java.util.Objects;

/** A capture can only be minted by the concrete native window owner. */
@SuppressWarnings("deprecation")
final class NativeEnvironmentV2 {
    final AppearanceResolverV2.Environment value;
    final int width, height;
    private final Observer source;
    private final long generation;
    private final Object windowToken;
    private NativeEnvironmentV2(Observer source, AppearanceResolverV2.Environment value,
                                int width, int height, Object token) {
        this.source = source; this.value = value; this.width = width; this.height = height;
        generation = source.generation; windowToken = token;
    }
    boolean current(Object owner) {
        requireMain();
        if (source.owner != owner || source.retired || generation != source.generation ||
            source.root.getWindowToken() != windowToken) return false;
        try {
            boolean equal = value.equals(source.read());
            return equal && !source.retired && source.owner == owner && generation == source.generation;
        }
        catch (RuntimeException unavailable) { return false; }
    }
    FrameLayout root() { requireMain(); return source.root; }
    static void requireMain() {
        if (Looper.myLooper() != Looper.getMainLooper()) throw new IllegalStateException("V2 requires UI owner thread");
    }
    static void unsupported() { throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation); }

    enum Change { INVALIDATED, DETACHED, EPOCH_EXHAUSTED, REGISTRATION_FAILED, RENDERER_TERMINAL }
    enum RendererCause { INTERACTION_EXHAUSTED, CAPTURE_FAILED, ROLLBACK_FAILED,
        CURRENT_CHECK_FATAL, CANCELLATION_FAILED, TERMINAL_VALIDATION_FAILED }
    interface Sink {
        void changed(Observer source, Change change, RendererCause cause, Throwable primary, Error firstFatal);
    }

    /** Listeners invalidate one complete tuple; a second synchronous read closes queued-listener races. */
    static final class Observer implements AutoCloseable, ComponentCallbacks {
        private NativeRenderer owner;
        private final Sink sink;
        private boolean registrationStarted, terminalReported;
        private RendererCause rendererCause;
        final Activity activity;
        final FrameLayout root;
        private long generation = 1;
        private boolean retired, initialized;
        private final ContentResolver resolver;
        private final ViewTreeObserver focusTarget;
        private int pending, acquiring = -1;
        // Fixed, bounded diagnostics: a returned removal does not establish reclamation.
        static final int UNATTEMPTED = 0, POSSIBLY_OWNED = 1, REMOVING = 2,
            RETURNED = 3, FAILED_UNCERTAIN = 4, DEAD_TARGET_UNCERTAIN = 5;
        private final int[] cleanup = new int[8];
        private final Throwable[] cleanupFailures = new Throwable[8];
        private Throwable primaryFailure;
        private Error fatalFailure;
        private boolean diagnosticsAttached;
        private final NativeEnvironmentPlatformV2.Listener contrast;
        private final NativeEnvironmentPlatformV2.Listener highContrast;
        private final View.OnLayoutChangeListener layout = (v,l,t,r,b,ol,ot,or,ob) -> {
            requireMain();
            if (retired) return;
            if (l != ol || t != ot || r != or || b != ob) invalidate();
        };
        private final View.OnAttachStateChangeListener attachment = new View.OnAttachStateChangeListener() {
            public void onViewAttachedToWindow(View view) { invalidate(); }
            public void onViewDetachedFromWindow(View view) { terminalNotification(Change.DETACHED); }
        };
        private final ViewTreeObserver.OnWindowFocusChangeListener windowFocus = focused -> invalidate();
        private final View.OnApplyWindowInsetsListener insets = (view, value) -> { invalidate(); return value; };
        private final ContentObserver motion = new ContentObserver(new Handler(Looper.getMainLooper())) {
            @Override public void onChange(boolean selfChange) { invalidate(); }
        };

        /** The private V2 root has one inset setter owner; no competing setter is permitted. */
        Observer(Activity activity, FrameLayout root, Sink sink) {
            requireMain();
            // Public high-contrast read/listener first exists on API36. Never invent false on earlier OSes.
            if (Build.VERSION.SDK_INT < 36 || root.getContext() != activity) unsupported();
            this.sink = Objects.requireNonNull(sink); this.activity = activity; this.root = root;
            contrast = NativeEnvironmentPlatformV2.contrastListener(activity, this::invalidate);
            highContrast = NativeEnvironmentPlatformV2.highContrastListener(activity, this::invalidate);
            resolver = Objects.requireNonNull(activity.getContentResolver());
            focusTarget = Objects.requireNonNull(root.getViewTreeObserver());
        }
        void register() {
            requireMain();
            if (registrationStarted || retired) throw new IllegalStateException("V2 observer registration is one shot");
            registrationStarted = true;
            try {
                begin(0); activity.registerComponentCallbacks(this); completed();
                begin(1); root.addOnLayoutChangeListener(layout); completed();
                begin(2); root.addOnAttachStateChangeListener(attachment); completed();
                begin(3); focusTarget.addOnWindowFocusChangeListener(windowFocus); completed();
                begin(4); root.setOnApplyWindowInsetsListener(insets); completed();
                begin(5); contrast.add(); completed();
                begin(6); highContrast.add(); completed();
                begin(7); resolver.registerContentObserver(
                    Settings.Global.getUriFor(Settings.Global.ANIMATOR_DURATION_SCALE), false, motion); completed();
                initialized = true;
            } catch (RuntimeException | Error failure) {
                retired = true; acquiring = -1;
                remember(failure);
                try { sink.changed(this, Change.REGISTRATION_FAILED, null, primaryFailure, fatalFailure); }
                catch (RuntimeException | Error report) { remember(report); }
                cleanupAll(); throwFailure();
            }
        }
        private void begin(int slot) {
            if (retired) throw new IllegalStateException("V2 observer retired during registration");
            acquiring = slot; pending |= 1 << slot; cleanup[slot] = POSSIBLY_OWNED;
        }
        private void completed() {
            acquiring = -1;
            if (retired) throw new IllegalStateException("V2 observer retired during registration");
        }
        private void remember(Throwable failure) {
            diagnosticsAttached = false;
            if (primaryFailure == null) primaryFailure = failure;
            if (failure instanceof Error && fatalFailure == null) fatalFailure = (Error)failure;
        }
        private static void suppress(Throwable target, Throwable detail) {
            if (detail == null || detail == target) return;
            try { target.addSuppressed(detail); }
            catch (Throwable unavailable) { /* Best effort only, after every cleanup was attempted. */ }
        }
        private void throwFailure() {
            Throwable failure = fatalFailure == null ? primaryFailure : fatalFailure;
            if (failure == null) return;
            if (!diagnosticsAttached) {
                diagnosticsAttached = true;
                suppress(failure, primaryFailure);
                for (Throwable detail : cleanupFailures) suppress(failure, detail);
            }
            if (failure instanceof Error) throw (Error)failure;
            throw (RuntimeException)failure;
        }
        void bindRenderer(NativeRenderer renderer) {
            requireMain();
            if (renderer == null || retired || !initialized || owner != null || !renderer.belongsToV2(activity, this))
                throw new IllegalStateException("V2 observer renderer binding rejected");
            owner = renderer;
        }
        /** Trusted scalar barrier after the owner's main check; listener disposition may still be active. */
        void retireScalarFromOwner() { retired = true; }
        boolean ready() { requireMain(); return initialized && !retired; }
        void invalidate() {
            requireMain();
            if (retired) return;
            if (generation == Long.MAX_VALUE) { terminalNotification(Change.EPOCH_EXHAUSTED); return; }
            generation++;
            notifyOwner(Change.INVALIDATED);
        }
        private void terminalNotification(Change change) {
            requireMain();
            if (retired) return;
            retired = true;
            notifyOwner(change);
        }
        private void notifyOwner(Change change) {
            try { sink.changed(this, change, null, null, null); }
            catch (RuntimeException | Error failure) {
                retired = true; remember(failure); cleanupAll(); throwFailure();
            }
        }
        void rendererTerminal(NativeRenderer renderer, RendererCause cause, Throwable primary, Error firstFatal) {
            requireMain();
            if (retired || terminalReported) return;
            if (renderer != owner || renderer == null || cause == null)
                throw new IllegalArgumentException("foreign V2 renderer terminal report");
            rendererCause = cause; terminalReported = true; retired = true;
            if (primary != null) remember(primary);
            if (firstFatal != null && fatalFailure == null) fatalFailure = firstFatal;
            sink.changed(this, Change.RENDERER_TERMINAL, rendererCause, primary, firstFatal);
        }
        static final class CleanupLedger {
            private final Observer source;
            private CleanupLedger(Observer source) { this.source = source; }
            int state(int slot) { requireMain(); return source.cleanup[slot]; }
            Throwable failure(int slot) { requireMain(); return source.cleanupFailures[slot]; }
            Throwable primary() { requireMain(); return source.primaryFailure; }
            Error firstFatal() { requireMain(); return source.fatalFailure; }
        }
        private final CleanupLedger ledger = new CleanupLedger(this);
        CleanupLedger cleanupLedger() { requireMain(); return ledger; }
        private void cleanupAll() {
            retired = true;
            for (int slot = 0; slot < 8; slot++) {
                int bit = 1 << slot;
                // An add may reenter before acquiring. Its final outcome is cleaned by constructor unwind.
                if ((pending & bit) == 0 || acquiring == slot) continue;
                pending &= ~bit; cleanup[slot] = REMOVING;
                try {
                    switch (slot) {
                    case 0: activity.unregisterComponentCallbacks(this); break;
                    case 1: root.removeOnLayoutChangeListener(layout); break;
                    case 2: root.removeOnAttachStateChangeListener(attachment); break;
                    case 3:
                        if (!focusTarget.isAlive()) { cleanup[slot] = DEAD_TARGET_UNCERTAIN; continue; }
                        focusTarget.removeOnWindowFocusChangeListener(windowFocus); break;
                    case 4: root.setOnApplyWindowInsetsListener(null); break;
                    case 5: contrast.remove(); break;
                    case 6: highContrast.remove(); break;
                    case 7: resolver.unregisterContentObserver(motion); break;
                    default: throw new AssertionError("Unknown observer slot");
                    }
                    cleanup[slot] = RETURNED;
                } catch (RuntimeException | Error failure) {
                    cleanup[slot] = FAILED_UNCERTAIN; cleanupFailures[slot] = failure; remember(failure);
                }
            }
        }
        NativeEnvironmentV2 capture() {
            requireMain();
            if (retired || !initialized || owner == null) unsupported();
            return new NativeEnvironmentV2(this, read(), root.getWidth(), root.getHeight(), root.getWindowToken());
        }
        AppearanceResolverV2.Environment read() {
            requireMain();
            if (retired || !initialized) unsupported();
            NativeEnvironmentPlatformV2.Snapshot observed = NativeEnvironmentPlatformV2.snapshot(activity, root);
            NativeEnvironmentPlatformV2.Frame frame = requireKnown(observed.frame);
            int density = requireKnown(observed.density1024);
            int selected = requireKnown(observed.bodyProfile);
            boolean dark = requireKnown(observed.dark), rtl = requireKnown(observed.rtl);
            String locale = requireKnown(observed.locale);
            NativeEnvironmentPlatformV2.Insets4 insets = requireKnown(observed.insets);
            if (requireKnown(observed.fontAdjustment) != 0 || requireKnown(observed.highContrast) ||
                requireKnown(observed.contrast) != 0) unsupported();
            float animator = requireKnown(observed.animator);
            // Intersect exact window safe boundaries with this root once.
            int top = Math.max(0,insets.top-frame.y);
            int left = Math.max(0,insets.left-frame.x);
            int right = Math.max(0,frame.x+frame.width-(frame.windowWidth-insets.right));
            int bottom = Math.max(0,frame.y+frame.height-(frame.windowHeight-insets.bottom));
            return new AppearanceResolverV2.Environment(
                dark ? AppearanceResolverV2.Scheme.dark : AppearanceResolverV2.Scheme.light,
                rtl ? AppearanceResolverV2.Direction.rightToLeft : AppearanceResolverV2.Direction.leftToRight,
                AppearanceDescriptorV2.Profile.values()[selected], density,
                new AppearanceResolverV2.Viewport(logical(frame.width,density),logical(frame.height,density)),
                new AppearanceResolverV2.SafeArea(logical(top,density),logical(rtl?right:left,density),
                    logical(bottom,density),logical(rtl?left:right,density)), locale,
                new AppearanceResolverV2.Accessibility(false,false,animator == 0), Long.toString(generation));
        }
        private static <T> T requireKnown(NativeEnvironmentPlatformV2.Observed<T> observed) {
            if (observed.status == NativeEnvironmentPlatformV2.Status.READ_FAILED) throw observed.failure;
            if (observed.status != NativeEnvironmentPlatformV2.Status.KNOWN) unsupported();
            return observed.value;
        }

        @Override public void onConfigurationChanged(Configuration configuration) { invalidate(); }
        @Override public void onLowMemory() { requireMain(); /* no capture fields change */ }
        @Override public void close() {
            requireMain(); retired = true;
            cleanupAll(); throwFailure();
        }
    }
    private static int logical(int pixel, int density) {
        long value = (long)pixel * 65536L / density;
        if (value > AppearanceGeometryV2.MAXIMUM_EXTENT64) unsupported();
        return (int)value;
    }
}
