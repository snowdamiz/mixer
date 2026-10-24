package dev.mixer.android;

import android.app.Activity;
import android.app.UiModeManager;
import android.content.ComponentCallbacks;
import android.content.res.Configuration;
import android.database.ContentObserver;
import android.graphics.Insets;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.util.DisplayMetrics;
import android.util.TypedValue;
import android.view.View;
import android.view.WindowInsets;
import android.view.accessibility.AccessibilityManager;
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
        try { return value.equals(source.read()); }
        catch (RuntimeException unavailable) { return false; }
    }
    FrameLayout root() { return source.root; }
    static void requireMain() {
        if (Looper.myLooper() != Looper.getMainLooper()) throw new IllegalStateException("V2 requires UI owner thread");
    }
    static void unsupported() { throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation); }

    /** Listeners invalidate one complete tuple; a second synchronous read closes queued-listener races. */
    static final class Observer implements AutoCloseable, ComponentCallbacks {
        final Object owner;
        final Activity activity;
        final FrameLayout root;
        private long generation = 1;
        private boolean retired;
        private final UiModeManager modes;
        private final AccessibilityManager accessibility;
        private final UiModeManager.ContrastChangeListener contrast = ignored -> invalidate();
        private final AccessibilityManager.HighContrastTextStateChangeListener highContrast = ignored -> invalidate();
        private final View.OnLayoutChangeListener layout = (v,l,t,r,b,ol,ot,or,ob) -> {
            if (l != ol || t != ot || r != or || b != ob) invalidate();
        };
        private final View.OnAttachStateChangeListener attachment=new View.OnAttachStateChangeListener(){
            public void onViewAttachedToWindow(View view){invalidate();}
            public void onViewDetachedFromWindow(View view){invalidate();}
        };
        private final android.view.ViewTreeObserver.OnWindowFocusChangeListener windowFocus=focused->invalidate();
        private final ContentObserver motion = new ContentObserver(new Handler(Looper.getMainLooper())) {
            @Override public void onChange(boolean selfChange) { invalidate(); }
        };

        Observer(Object owner, Activity activity, FrameLayout root) {
            requireMain();
            // Public high-contrast read/listener first exists on API36. Never invent false on earlier OSes.
            if (Build.VERSION.SDK_INT < 36 || root.getContext() != activity) unsupported();
            this.owner = owner; this.activity = activity; this.root = root;
            modes = Objects.requireNonNull(activity.getSystemService(UiModeManager.class));
            accessibility = Objects.requireNonNull(activity.getSystemService(AccessibilityManager.class));
            activity.registerComponentCallbacks(this);
            root.addOnLayoutChangeListener(layout);root.addOnAttachStateChangeListener(attachment);
            root.getViewTreeObserver().addOnWindowFocusChangeListener(windowFocus);
            root.setOnApplyWindowInsetsListener((view, insets) -> { invalidate(); return insets; });
            modes.addContrastChangeListener(activity.getMainExecutor(), contrast);
            accessibility.addHighContrastTextStateChangeListener(activity.getMainExecutor(), highContrast);
            activity.getContentResolver().registerContentObserver(
                Settings.Global.getUriFor(Settings.Global.ANIMATOR_DURATION_SCALE), false, motion);
        }
        void invalidate() {
            requireMain();
            if (generation == Long.MAX_VALUE) { retired = true; return; }
            generation++;
        }
        NativeEnvironmentV2 capture() {
            requireMain();
            if (retired) unsupported();
            return new NativeEnvironmentV2(this, read(), root.getWidth(), root.getHeight(), root.getWindowToken());
        }
        AppearanceResolverV2.Environment read() {
            requireMain();
            if (retired || activity.isDestroyed() || !root.isAttachedToWindow() || root.getWindowToken() == null ||
                root.getWidth() <= 0 || root.getHeight() <= 0) unsupported();
            Configuration config = activity.getResources().getConfiguration();
            DisplayMetrics metrics = activity.getResources().getDisplayMetrics();
            int density = AppearanceGeometryV2.normalizeDensity(metrics.density);
            double dp = TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, 1, metrics);
            double sp = TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, 17, metrics);
            double body = sp / dp;
            if (!Double.isFinite(dp) || dp <= 0 || !Double.isFinite(sp) || sp <= 0 ||
                !Double.isFinite(body) || body < 14 || body > 53) unsupported();
            int body64 = (int)Math.floor(body * 64 + .5);
            int[] anchors = {896,960,1024,1088,1216,1344,1472,1792,2112,2560,3008,3392};
            int selected = 0;
            for (int i=1;i<anchors.length;i++)
                if (Math.abs(anchors[i]-body64) <= Math.abs(anchors[selected]-body64)) selected=i;
            WindowInsets captured = root.getRootWindowInsets();
            if (captured == null) unsupported();
            Insets insets = captured.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
            int[] location = new int[2]; root.getLocationInWindow(location);
            View decor = activity.getWindow().getDecorView();
            // Intersect actual window safe boundaries with this root. Already-inset roots do not pay twice.
            int top = Math.max(0,insets.top-location[1]);
            int left = Math.max(0,insets.left-location[0]);
            int right = Math.max(0,location[0]+root.getWidth()-(decor.getWidth()-insets.right));
            int bottom = Math.max(0,location[1]+root.getHeight()-(decor.getHeight()-insets.bottom));
            boolean rtl = root.getLayoutDirection() == View.LAYOUT_DIRECTION_RTL;
            int adjustment = config.fontWeightAdjustment;
            if (adjustment != Configuration.FONT_WEIGHT_ADJUSTMENT_UNDEFINED && adjustment != 0 ||
                accessibility.isHighContrastTextEnabled() || modes.getContrast() > 0) unsupported();
            float animator = Settings.Global.getFloat(activity.getContentResolver(), Settings.Global.ANIMATOR_DURATION_SCALE, 1);
            if (!Float.isFinite(animator) || animator < 0) unsupported();
            return new AppearanceResolverV2.Environment(
                (config.uiMode & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES ?
                    AppearanceResolverV2.Scheme.dark : AppearanceResolverV2.Scheme.light,
                rtl ? AppearanceResolverV2.Direction.rightToLeft : AppearanceResolverV2.Direction.leftToRight,
                AppearanceDescriptorV2.Profile.values()[selected], density,
                new AppearanceResolverV2.Viewport(logical(root.getWidth(),density),logical(root.getHeight(),density)),
                new AppearanceResolverV2.SafeArea(logical(top,density),logical(rtl?right:left,density),
                    logical(bottom,density),logical(rtl?left:right,density)),
                config.getLocales().get(0).toLanguageTag(),
                new AppearanceResolverV2.Accessibility(false,false,animator == 0), Long.toString(generation));
        }
        @Override public void onConfigurationChanged(Configuration configuration) { invalidate(); }
        @Override public void onLowMemory() { /* no capture fields change */ }
        @Override public void close() {
            requireMain(); retired = true;
            activity.unregisterComponentCallbacks(this); root.removeOnLayoutChangeListener(layout);root.removeOnAttachStateChangeListener(attachment);
            if(root.getViewTreeObserver().isAlive())root.getViewTreeObserver().removeOnWindowFocusChangeListener(windowFocus);
            root.setOnApplyWindowInsetsListener(null);
            modes.removeContrastChangeListener(contrast);
            accessibility.removeHighContrastTextStateChangeListener(highContrast);
            activity.getContentResolver().unregisterContentObserver(motion);
        }
    }
    private static int logical(int pixel, int density) {
        long value = (long)pixel * 65536L / density;
        if (value > AppearanceGeometryV2.MAXIMUM_EXTENT64) unsupported();
        return (int)value;
    }
}
