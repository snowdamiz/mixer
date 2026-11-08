package android.app;
public final class Activity extends android.content.Context {
    public UiModeManager modes = new UiModeManager();
    public android.view.accessibility.AccessibilityManager accessibility = new android.view.accessibility.AccessibilityManager();
    public android.content.ContentResolver resolver = new android.content.ContentResolver();
    private final android.content.res.Resources resources = new android.content.res.Resources();
    private final android.view.Window window = new android.view.Window(this);
    public <T> T getSystemService(Class<T> type) { return type.cast(type == UiModeManager.class ? modes : accessibility); }
    public android.content.ContentResolver getContentResolver() { return resolver; }
    public java.util.concurrent.Executor executor=Runnable::run;
    public boolean destroyed;
    public java.util.concurrent.Executor getMainExecutor() { return executor; }
    public void registerComponentCallbacks(android.content.ComponentCallbacks callback) { dev.mixer.android.ObserverHostProbe.add(0, this, callback); }
    public void unregisterComponentCallbacks(android.content.ComponentCallbacks callback) { dev.mixer.android.ObserverHostProbe.remove(0, this, callback); }
    public boolean isDestroyed() { return destroyed; }
    public android.content.res.Resources getResources() { return resources; }
    public android.view.Window getWindow() { return window; }
}
