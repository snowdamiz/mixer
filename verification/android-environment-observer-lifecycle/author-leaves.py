from pathlib import Path
root=Path('native/android/tests/NativeEnvironmentV2ObserverHostLeaves')
files={
'android/os/Looper.java':'''package android.os;
public final class Looper {
    private static final Looper MAIN = new Looper();
    public static boolean mainThread = true;
    public static Looper getMainLooper() { return MAIN; }
    public static Looper myLooper() { return mainThread ? MAIN : null; }
}''',
'android/os/Handler.java':'''package android.os;
public final class Handler { public Handler(Looper looper) {} }''',
'android/os/Build.java':'''package android.os;
public final class Build { public static final class VERSION { public static int SDK_INT = 37; } }''',
'android/os/LocaleList.java':'''package android.os;
public final class LocaleList { public java.util.Locale get(int index) { return java.util.Locale.US; } }''',
'android/content/ComponentCallbacks.java':'''package android.content;
public interface ComponentCallbacks { void onConfigurationChanged(android.content.res.Configuration value); void onLowMemory(); }''',
'android/content/Context.java':'''package android.content;
public class Context {}''',
'android/content/res/Configuration.java':'''package android.content.res;
public final class Configuration {
    public static final int FONT_WEIGHT_ADJUSTMENT_UNDEFINED = Integer.MAX_VALUE, UI_MODE_NIGHT_MASK = 48, UI_MODE_NIGHT_YES = 32;
    public int fontWeightAdjustment, uiMode;
    public android.os.LocaleList getLocales() { return new android.os.LocaleList(); }
}''',
'android/content/res/Resources.java':'''package android.content.res;
public final class Resources {
    private final Configuration config = new Configuration();
    private final android.util.DisplayMetrics metrics = new android.util.DisplayMetrics();
    public Configuration getConfiguration() { dev.mixer.android.ObserverHostProbe.reads++; return config; }
    public android.util.DisplayMetrics getDisplayMetrics() { return metrics; }
}''',
'android/database/ContentObserver.java':'''package android.database;
public abstract class ContentObserver { public ContentObserver(android.os.Handler handler) {} public void onChange(boolean selfChange) {} }''',
'android/net/Uri.java':'''package android.net;
public final class Uri {}''',
'android/content/ContentResolver.java':'''package android.content;
public final class ContentResolver {
    public void registerContentObserver(android.net.Uri uri, boolean descendants, android.database.ContentObserver observer) { dev.mixer.android.ObserverHostProbe.add(7, this, observer); }
    public void unregisterContentObserver(android.database.ContentObserver observer) { dev.mixer.android.ObserverHostProbe.remove(7, this, observer); }
}''',
'android/app/Activity.java':'''package android.app;
public final class Activity extends android.content.Context {
    public final UiModeManager modes = new UiModeManager();
    public final android.view.accessibility.AccessibilityManager accessibility = new android.view.accessibility.AccessibilityManager();
    public android.content.ContentResolver resolver = new android.content.ContentResolver();
    private final android.content.res.Resources resources = new android.content.res.Resources();
    private final android.view.Window window = new android.view.Window(this);
    public <T> T getSystemService(Class<T> type) { return type.cast(type == UiModeManager.class ? modes : accessibility); }
    public android.content.ContentResolver getContentResolver() { return resolver; }
    public java.util.concurrent.Executor getMainExecutor() { return Runnable::run; }
    public void registerComponentCallbacks(android.content.ComponentCallbacks callback) { dev.mixer.android.ObserverHostProbe.add(0, this, callback); }
    public void unregisterComponentCallbacks(android.content.ComponentCallbacks callback) { dev.mixer.android.ObserverHostProbe.remove(0, this, callback); }
    public boolean isDestroyed() { return false; }
    public android.content.res.Resources getResources() { return resources; }
    public android.view.Window getWindow() { return window; }
}''',
'android/app/UiModeManager.java':'''package android.app;
public final class UiModeManager {
    public interface ContrastChangeListener { void onContrastChanged(float contrast); }
    public void addContrastChangeListener(java.util.concurrent.Executor executor, ContrastChangeListener listener) { dev.mixer.android.ObserverHostProbe.add(5, this, listener); }
    public void removeContrastChangeListener(ContrastChangeListener listener) { dev.mixer.android.ObserverHostProbe.remove(5, this, listener); }
    public float getContrast() { return 0; }
}''',
'android/view/accessibility/AccessibilityManager.java':'''package android.view.accessibility;
public final class AccessibilityManager {
    public interface HighContrastTextStateChangeListener { void onHighContrastTextStateChanged(boolean enabled); }
    public void addHighContrastTextStateChangeListener(java.util.concurrent.Executor executor, HighContrastTextStateChangeListener listener) { dev.mixer.android.ObserverHostProbe.add(6, this, listener); }
    public void removeHighContrastTextStateChangeListener(HighContrastTextStateChangeListener listener) { dev.mixer.android.ObserverHostProbe.remove(6, this, listener); }
    public boolean isHighContrastTextEnabled() { return false; }
}''',
'android/graphics/Insets.java':'''package android.graphics;
public final class Insets { public int left, top, right, bottom; }''',
'android/provider/Settings.java':'''package android.provider;
public final class Settings { public static final class Global {
    public static final String ANIMATOR_DURATION_SCALE = "animator";
    public static android.net.Uri getUriFor(String name) { return new android.net.Uri(); }
    public static float getFloat(android.content.ContentResolver resolver, String name, float fallback) { return 1; }
} }''',
'android/util/DisplayMetrics.java':'''package android.util;
public final class DisplayMetrics { public float density = 1; }''',
'android/util/TypedValue.java':'''package android.util;
public final class TypedValue {
    public static final int COMPLEX_UNIT_DIP = 1, COMPLEX_UNIT_SP = 2;
    public static float applyDimension(int kind, float value, DisplayMetrics metrics) { return value * metrics.density; }
}''',
'android/view/WindowInsets.java':'''package android.view;
public final class WindowInsets {
    public android.graphics.Insets getInsets(int mask) { return new android.graphics.Insets(); }
    public static final class Type { public static int systemBars() { return 1; } public static int displayCutout() { return 2; } }
}''',
'android/view/ViewTreeObserver.java':'''package android.view;
public final class ViewTreeObserver {
    public interface OnWindowFocusChangeListener { void onWindowFocusChanged(boolean focused); }
    public boolean alive = true;
    public int adds, removes;
    public boolean isAlive() { return alive; }
    public void addOnWindowFocusChangeListener(OnWindowFocusChangeListener listener) { adds++; dev.mixer.android.ObserverHostProbe.add(3, this, listener); }
    public void removeOnWindowFocusChangeListener(OnWindowFocusChangeListener listener) { removes++; dev.mixer.android.ObserverHostProbe.remove(3, this, listener); }
}''',
'android/view/View.java':'''package android.view;
public class View {
    public interface OnLayoutChangeListener { void onLayoutChange(View v, int l, int t, int r, int b, int ol, int ot, int or, int ob); }
    public interface OnAttachStateChangeListener { void onViewAttachedToWindow(View view); void onViewDetachedFromWindow(View view); }
    public interface OnApplyWindowInsetsListener { WindowInsets onApplyWindowInsets(View view, WindowInsets insets); }
    public static final int LAYOUT_DIRECTION_RTL = 1;
    private final android.content.Context context;
    private final Object token = new Object();
    public ViewTreeObserver tree = new ViewTreeObserver();
    public OnApplyWindowInsetsListener insetListener;
    public View(android.content.Context context) { this.context = context; }
    public android.content.Context getContext() { return context; }
    public void addOnLayoutChangeListener(OnLayoutChangeListener listener) { dev.mixer.android.ObserverHostProbe.add(1, this, listener); }
    public void removeOnLayoutChangeListener(OnLayoutChangeListener listener) { dev.mixer.android.ObserverHostProbe.remove(1, this, listener); }
    public void addOnAttachStateChangeListener(OnAttachStateChangeListener listener) { dev.mixer.android.ObserverHostProbe.add(2, this, listener); }
    public void removeOnAttachStateChangeListener(OnAttachStateChangeListener listener) { dev.mixer.android.ObserverHostProbe.remove(2, this, listener); }
    public ViewTreeObserver getViewTreeObserver() { return tree; }
    public void setOnApplyWindowInsetsListener(OnApplyWindowInsetsListener listener) {
        if (listener == null) { dev.mixer.android.ObserverHostProbe.remove(4, this, insetListener); insetListener = null; }
        else { insetListener = listener; dev.mixer.android.ObserverHostProbe.add(4, this, listener); }
    }
    public Object getWindowToken() { dev.mixer.android.ObserverHostProbe.tokenReads++; return token; }
    public boolean isAttachedToWindow() { return true; }
    public int getWidth() { return 320; }
    public int getHeight() { return 640; }
    public int getLayoutDirection() { return 0; }
    public WindowInsets getRootWindowInsets() { return new WindowInsets(); }
    public void getLocationInWindow(int[] result) { result[0] = 0; result[1] = 0; }
}''',
'android/view/Window.java':'''package android.view;
public final class Window { private final View decor; public Window(android.content.Context context) { decor = new View(context); } public View getDecorView() { return decor; } }''',
'android/widget/FrameLayout.java':'''package android.widget;
public final class FrameLayout extends android.view.View { public FrameLayout(android.content.Context context) { super(context); } }''',
'dev/mixer/android/AppearanceGeometryV2.java':'''package dev.mixer.android;
final class AppearanceGeometryV2 { static final int MAXIMUM_EXTENT64 = 10000000; static int normalizeDensity(float value) { return (int)(value * 1024); } }''',
'dev/mixer/android/AppearanceDescriptorV2.java':'''package dev.mixer.android;
final class AppearanceDescriptorV2 {
    enum Error { unsupportedNativeOperation }
    static final class Failure extends RuntimeException { private static final long serialVersionUID = 1L; Failure(Error value) { super(value.toString()); } }
    enum Profile { p0,p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11 }
}''',
'dev/mixer/android/AppearanceResolverV2.java':'''package dev.mixer.android;
final class AppearanceResolverV2 {
    enum Scheme { light,dark } enum Direction { leftToRight,rightToLeft }
    record Viewport(int width, int height) {} record SafeArea(int top,int leading,int bottom,int trailing) {}
    record Accessibility(boolean highContrast, boolean bold, boolean reducedMotion) {}
    record Environment(Scheme scheme, Direction direction, AppearanceDescriptorV2.Profile profile, int density,
        Viewport viewport, SafeArea safeArea, String locale, Accessibility accessibility, String epoch) {}
}''',
'dev/mixer/android/NativeRenderer.java':'''package dev.mixer.android;
final class NativeRenderer {
    int invalidations;
    Runnable notification;
    void environmentInvalidatedV2() { invalidations++; if (notification != null) notification.run(); }
}''',
'dev/mixer/android/ObserverHostProbe.java':'''package dev.mixer.android;
import java.util.ArrayList;
import java.util.List;
public final class ObserverHostProbe {
    public static final List<String> calls = new ArrayList<>();
    public static final Object[] live = new Object[8], last = new Object[8], targets = new Object[8];
    public static final Runnable[][] hooks = new Runnable[4][8];
    public static final Throwable[][] faults = new Throwable[4][8];
    public static int reads, tokenReads;
    public static void reset() {
        calls.clear(); reads = tokenReads = 0;
        java.util.Arrays.fill(live, null); java.util.Arrays.fill(last, null); java.util.Arrays.fill(targets, null);
        for (Runnable[] row : hooks) java.util.Arrays.fill(row, null);
        for (Throwable[] row : faults) java.util.Arrays.fill(row, null);
        android.os.Looper.mainThread = true;
    }
    private static void event(int phase, int slot) {
        Runnable hook = hooks[phase][slot]; if (hook != null) { hooks[phase][slot] = null; hook.run(); }
        Throwable failure = faults[phase][slot];
        if (failure instanceof Error) throw (Error)failure;
        if (failure != null) throw (RuntimeException)failure;
    }
    public static void add(int slot, Object target, Object listener) {
        calls.add("add" + slot); last[slot] = listener; targets[slot] = target;
        event(0,slot); live[slot] = listener; event(1,slot);
    }
    public static void remove(int slot, Object target, Object listener) {
        calls.add("remove" + slot);
        if (targets[slot] != target || last[slot] != listener) throw new AssertionError("wrong removal identity " + slot);
        event(2,slot); live[slot] = null; event(3,slot);
    }
}'''
}
for relative,source in files.items():
    p=root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(source+'\n')
print(len(files),'independently authored leaf sources')
