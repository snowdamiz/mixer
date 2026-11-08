package dev.mixer.android;

import android.app.Activity;
import android.app.UiModeManager;
import android.content.res.Configuration;
import android.content.res.Resources;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.util.DisplayMetrics;
import android.util.TypedValue;
import android.view.View;
import android.view.WindowInsets;
import android.view.accessibility.AccessibilityManager;
import android.widget.FrameLayout;
import java.nio.charset.StandardCharsets;
import java.util.Objects;
import java.util.concurrent.Executor;
import java.util.concurrent.atomic.AtomicBoolean;

/** Public observations only. Neither snapshots nor listener handles confer capture authority. */
final class NativeEnvironmentPlatformV2 {
    private NativeEnvironmentPlatformV2() {}
    enum Status { KNOWN, UNAVAILABLE_API, UNAVAILABLE_SEMANTICS, UNDEFINED, READ_FAILED }
    static final class Observed<T> {
        final Status status;
        final T value;
        final String reason;
        final RuntimeException failure;
        private Observed(Status status, T value, String reason, RuntimeException failure) {
            if ((status == Status.KNOWN) != (value != null)) throw new IllegalArgumentException("observation value/status");
            if ((status == Status.READ_FAILED) != (failure != null)) throw new IllegalArgumentException("observation failure/status");
            this.status = status; this.value = value; this.reason = Objects.requireNonNull(reason); this.failure = failure;
        }
    }
    private static <T> Observed<T> known(T value) { return new Observed<>(Status.KNOWN, Objects.requireNonNull(value), "actual public read", null); }
    private static <T> Observed<T> absent(Status status, String reason) { return new Observed<>(status, null, reason, null); }
    private interface Read<T> { Observed<T> read(); }
    private static <T> Observed<T> attempt(Read<T> read) {
        try { return read.read(); }
        catch (RuntimeException failure) { return new Observed<>(Status.READ_FAILED, null, failure.getClass().getName(), failure); }
    }
    private static <T> Observed<T> missing(Observed<?> source) { return new Observed<>(source.status, null, source.reason, source.failure); }

    static final class Frame {
        final Object token;
        final int width, height, x, y, windowWidth, windowHeight;
        private Frame(Object token, int width, int height, int x, int y, int windowWidth, int windowHeight) {
            this.token = token; this.width = width; this.height = height; this.x = x; this.y = y;
            this.windowWidth = windowWidth; this.windowHeight = windowHeight;
        }
    }
    static final class Insets4 {
        final int top, left, bottom, right;
        private Insets4(int top, int left, int bottom, int right) {
            this.top = top; this.left = left; this.bottom = bottom; this.right = right;
        }
    }
    static final class Snapshot {
        final Observed<Frame> frame;
        final Observed<Boolean> dark, rtl;
        final Observed<String> locale;
        final Observed<Integer> density1024, bodyProfile, fontAdjustment;
        final Observed<Insets4> insets;
        final Observed<Float> contrast, animator;
        final Observed<Boolean> highContrast;
        private Snapshot(Observed<Frame> frame, Observed<Boolean> dark, Observed<Boolean> rtl,
                         Observed<String> locale, Observed<Integer> density, Observed<Integer> body,
                         Observed<Insets4> insets, Observed<Integer> weight, Observed<Float> contrast,
                         Observed<Boolean> highContrast, Observed<Float> animator) {
            this.frame=frame; this.dark=dark; this.rtl=rtl; this.locale=locale; density1024=density;
            bodyProfile=body; this.insets=insets; fontAdjustment=weight; this.contrast=contrast;
            this.highContrast=highContrast; this.animator=animator;
        }
    }
    /** Read-only on every SDK. No subscription, owner, readiness, session or capture is created. */
    static Snapshot snapshot(Activity activity, FrameLayout root) {
        NativeEnvironmentV2.requireMain();
        Objects.requireNonNull(activity); Objects.requireNonNull(root);
        Observed<Configuration> config=attempt(() -> {
            Resources resources=activity.getResources();
            Configuration value=resources == null ? null : resources.getConfiguration();
            return value == null ? absent(Status.UNDEFINED,"missing window configuration") : known(value);
        });
        Observed<DisplayMetrics> metrics=attempt(() -> {
            Resources resources=activity.getResources();
            DisplayMetrics value=resources == null ? null : resources.getDisplayMetrics();
            return value == null ? absent(Status.UNDEFINED,"missing window metrics") : known(value);
        });
        Observed<Frame> frame=attempt(() -> {
            Object token=root.getWindowToken();
            int width=root.getWidth(), height=root.getHeight();
            if (root.getContext()!=activity || activity.isDestroyed() || !root.isAttachedToWindow() || token==null || width<=0 || height<=0)
                return absent(Status.UNDEFINED,"unavailable current root");
            int[] location=new int[2]; root.getLocationInWindow(location);
            View decor=activity.getWindow().getDecorView();
            if (decor==null || decor.getWidth()<=0 || decor.getHeight()<=0) return absent(Status.UNDEFINED,"unavailable window extent");
            return known(new Frame(token,width,height,location[0],location[1],decor.getWidth(),decor.getHeight()));
        });
        Observed<Boolean> dark=config.status!=Status.KNOWN ? missing(config) : attempt(() -> {
            int mask=config.value.uiMode & Configuration.UI_MODE_NIGHT_MASK;
            if (mask!=Configuration.UI_MODE_NIGHT_YES && mask!=Configuration.UI_MODE_NIGHT_NO)
                return absent(Status.UNDEFINED,"night mode is not explicit");
            return known(mask==Configuration.UI_MODE_NIGHT_YES);
        });
        Observed<Boolean> rtl=attempt(() -> {
            int direction=root.getLayoutDirection();
            if (direction!=View.LAYOUT_DIRECTION_LTR && direction!=View.LAYOUT_DIRECTION_RTL)
                return absent(Status.UNDEFINED,"direction is not resolved");
            return known(direction==View.LAYOUT_DIRECTION_RTL);
        });
        Observed<String> locale=config.status!=Status.KNOWN ? missing(config) : attempt(() -> {
            if (config.value.getLocales()==null || config.value.getLocales().isEmpty() || config.value.getLocales().get(0)==null)
                return absent(Status.UNDEFINED,"missing first locale");
            String tag=config.value.getLocales().get(0).toLanguageTag();
            return validLocale(tag) ? known(tag) : absent(Status.UNDEFINED,"malformed bounded locale");
        });
        Observed<Integer> density=metrics.status!=Status.KNOWN ? missing(metrics) : attempt(() -> {
            double value=metrics.value.density;
            if (!Double.isFinite(value) || value < .125 || value > 16) return absent(Status.UNDEFINED,"density outside bounds");
            return known(AppearanceGeometryV2.normalizeDensity(value));
        });
        Observed<Integer> body=metrics.status!=Status.KNOWN ? missing(metrics) : attempt(() -> {
            double dp=TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP,1,metrics.value);
            double sp=TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP,17,metrics.value);
            double value=sp/dp;
            if (!Double.isFinite(dp) || dp<=0 || !Double.isFinite(sp) || sp<=0 || !Double.isFinite(value) || value<14 || value>53)
                return absent(Status.UNDEFINED,"body conversion outside bounds");
            int body64=(int)Math.floor(value*64+.5), selected=0;
            int[] anchors={896,960,1024,1088,1216,1344,1472,1792,2112,2560,3008,3392};
            for(int i=1;i<anchors.length;i++) if(Math.abs(anchors[i]-body64)<=Math.abs(anchors[selected]-body64)) selected=i;
            return known(selected);
        });
        Observed<Insets4> insets=Build.VERSION.SDK_INT<30 ? absent(Status.UNAVAILABLE_SEMANTICS,"exact systemBars|displayCutout requires API30") : attempt(() -> Api30.insets(root));
        Observed<Integer> weight=Build.VERSION.SDK_INT<31 ? absent(Status.UNAVAILABLE_API,"font adjustment requires API31") :
            config.status!=Status.KNOWN ? missing(config) : attempt(() -> Api31.weight(config.value));
        Observed<Float> contrast=Build.VERSION.SDK_INT<34 ? absent(Status.UNAVAILABLE_API,"system contrast requires API34") : attempt(() -> Api34.contrast(activity));
        Observed<Boolean> high=Build.VERSION.SDK_INT<36 ? absent(Status.UNAVAILABLE_API,"high contrast requires API36") : attempt(() -> Api36.highContrast(activity));
        Observed<Float> animator=Build.VERSION.SDK_INT<33 ? absent(Status.UNAVAILABLE_API,"effective animator scale requires API33") : attempt(Api33::animator);
        return new Snapshot(frame,dark,rtl,locale,density,body,insets,weight,contrast,high,animator);
    }
    private static boolean validLocale(String value) {
        if(value==null || value.isEmpty() || value.length()>128) return false;
        for(int i=0;i<value.length();i++) {
            char c=value.charAt(i);
            if(Character.isHighSurrogate(c)) { if(i+1>=value.length() || !Character.isLowSurrogate(value.charAt(++i))) return false; }
            else if(Character.isLowSurrogate(c)) return false;
        }
        if(value.getBytes(StandardCharsets.UTF_8).length>128) return false;
        for(int i=0;i<value.length();) {
            int point=value.codePointAt(i), category=Character.getType(point);
            if(category==Character.CONTROL || category==Character.FORMAT) return false;
            i+=Character.charCount(point);
        }
        return true;
    }
    /** Immutable exact target/listener/executor; only Observer decides when add/remove is attempted. */
    interface Listener { void add(); void remove(); }
    static Listener motionListener(Runnable changed) {
        NativeEnvironmentV2.requireMain();
        if(Build.VERSION.SDK_INT<33) throw new IllegalStateException("effective animator listener requires API33");
        return new Api33(Objects.requireNonNull(changed));
    }
    static Listener contrastListener(Activity activity, Runnable changed) {
        if(Build.VERSION.SDK_INT<34) throw new IllegalStateException("contrast listener requires API34");
        return Api34.listener(activity,changed);
    }
    static Listener highContrastListener(Activity activity, Runnable changed) {
        if(Build.VERSION.SDK_INT<36) throw new IllegalStateException("high contrast listener requires API36");
        return Api36.listener(activity,changed);
    }
    private static final class Api30 {
        static Observed<Insets4> insets(FrameLayout root) {
            WindowInsets source=root.getRootWindowInsets();
            if(source==null) return absent(Status.UNDEFINED,"missing typed window insets");
            android.graphics.Insets value=source.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
            if(value==null || value.top<0 || value.left<0 || value.bottom<0 || value.right<0)
                return absent(Status.UNDEFINED,"invalid typed window insets");
            return known(new Insets4(value.top,value.left,value.bottom,value.right));
        }
    }
    private static final class Api31 {
        static Observed<Integer> weight(Configuration config) {
            int value=config.fontWeightAdjustment;
            return value==Configuration.FONT_WEIGHT_ADJUSTMENT_UNDEFINED ? absent(Status.UNDEFINED,"undefined font adjustment") : known(value);
        }
    }
    private static final class Api33 implements Listener {
        private enum Phase { NEW, REGISTERING, ACTIVE, CLOSED }
        private final Handler main = new Handler(Looper.getMainLooper());
        private final AtomicBoolean queued = new AtomicBoolean();
        private volatile Phase phase = Phase.NEW;
        private boolean started, registering, removeRequested, removalAttempted;
        private final android.animation.ValueAnimator.DurationScaleChangeListener listener;
        private Api33(Runnable changed) {
            Runnable delivery = () -> {
                NativeEnvironmentV2.requireMain();
                queued.set(false);
                if (phase == Phase.ACTIVE) changed.run();
            };
            listener = ignored -> {
                Phase observed = phase;
                if ((observed != Phase.REGISTERING && observed != Phase.ACTIVE) || !queued.compareAndSet(false, true)) return;
                try {
                    if (!main.post(delivery)) throw new IllegalStateException("effective animator UI dispatch failed");
                } catch (RuntimeException | Error failure) {
                    queued.set(false);
                    throw failure;
                }
            };
        }
        static Observed<Float> animator() {
            float value=android.animation.ValueAnimator.getDurationScale();
            return Float.isFinite(value) && value>=0 ? known(value) : absent(Status.UNDEFINED,"invalid effective animator scale");
        }
        public void add() {
            NativeEnvironmentV2.requireMain();
            if (phase != Phase.NEW) throw new IllegalStateException("effective animator listener is one shot");
            started = true; phase = Phase.REGISTERING; registering = true;
            Throwable failure = null;
            try {
                if (!android.animation.ValueAnimator.registerDurationScaleChangeListener(listener))
                    throw new IllegalStateException("effective animator listener registration failed");
            } catch (RuntimeException | Error caught) { failure = caught; }
            finally {
                registering = false;
                if (phase != Phase.CLOSED) phase = failure == null ? Phase.ACTIVE : Phase.CLOSED;
            }
            // Reentrant removal cannot precede the platform's final acquisition side effect.
            if (removeRequested) {
                try { unregister(); }
                catch (RuntimeException | Error cleanup) {
                    if (failure == null) failure = cleanup;
                    else if (cleanup != failure) {
                        if (cleanup instanceof Error && !(failure instanceof Error)) {
                            cleanup.addSuppressed(failure); failure = cleanup;
                        } else failure.addSuppressed(cleanup);
                    }
                }
            }
            if (failure instanceof Error) throw (Error)failure;
            if (failure != null) throw (RuntimeException)failure;
        }
        public void remove() {
            NativeEnvironmentV2.requireMain();
            phase = Phase.CLOSED;
            if (!started || removeRequested) return;
            removeRequested = true;
            if (!registering) unregister();
        }
        private void unregister() {
            if (removalAttempted) return;
            removalAttempted = true;
            if(!android.animation.ValueAnimator.unregisterDurationScaleChangeListener(listener))
                throw new IllegalStateException("effective animator listener removal failed");
        }
    }
    private static final class Api34 implements Listener {
        private final UiModeManager target;
        private final Executor executor;
        private final UiModeManager.ContrastChangeListener listener;
        private Api34(UiModeManager target, Executor executor, Runnable changed) {
            this.target=target; this.executor=executor; listener=ignored -> changed.run();
        }
        static Listener listener(Activity activity,Runnable changed) {
            return new Api34(Objects.requireNonNull(activity.getSystemService(UiModeManager.class)),Objects.requireNonNull(activity.getMainExecutor()),Objects.requireNonNull(changed));
        }
        static Observed<Float> contrast(Activity activity) {
            float value=Objects.requireNonNull(activity.getSystemService(UiModeManager.class)).getContrast();
            return Float.isFinite(value) && value>=-1 && value<=1 ? known(value) : absent(Status.UNDEFINED,"invalid system contrast");
        }
        public void add() { target.addContrastChangeListener(executor,listener); }
        public void remove() { target.removeContrastChangeListener(listener); }
    }
    private static final class Api36 implements Listener {
        private final AccessibilityManager target;
        private final Executor executor;
        private final AccessibilityManager.HighContrastTextStateChangeListener listener;
        private Api36(AccessibilityManager target,Executor executor,Runnable changed) {
            this.target=target; this.executor=executor; listener=ignored -> changed.run();
        }
        static Listener listener(Activity activity,Runnable changed) {
            return new Api36(Objects.requireNonNull(activity.getSystemService(AccessibilityManager.class)),Objects.requireNonNull(activity.getMainExecutor()),Objects.requireNonNull(changed));
        }
        static Observed<Boolean> highContrast(Activity activity) {
            return known(Objects.requireNonNull(activity.getSystemService(AccessibilityManager.class)).isHighContrastTextEnabled());
        }
        public void add() { target.addHighContrastTextStateChangeListener(executor,listener); }
        public void remove() { target.removeHighContrastTextStateChangeListener(listener); }
    }
}
