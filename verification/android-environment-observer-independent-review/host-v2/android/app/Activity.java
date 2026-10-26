package android.app;
import android.content.ComponentCallbacks;
import android.content.ContentResolver;
import android.content.Context;
import android.content.res.Resources;
import android.view.Window;
import android.view.accessibility.AccessibilityManager;
import dev.mixer.android.IndependentFaults;
import java.util.concurrent.Executor;
public final class Activity extends Context {
    public final UiModeManager modes = new UiModeManager();
    public final AccessibilityManager accessibility = new AccessibilityManager();
    public final Resources resources = new Resources();
    public final Window window = new Window(this);
    public ContentResolver resolver = new ContentResolver();
    public ComponentCallbacks savedComponent;
    public boolean destroyed;
    public <T> T getSystemService(Class<T> type) {
        IndependentFaults.read();
        if (type == UiModeManager.class) return type.cast(modes);
        if (type == AccessibilityManager.class) return type.cast(accessibility);
        return null;
    }
    public void registerComponentCallbacks(ComponentCallbacks listener) {
        savedComponent = listener; IndependentFaults.add("component", this, listener);
    }
    public void unregisterComponentCallbacks(ComponentCallbacks listener) {
        IndependentFaults.remove("component", this, listener);
    }
    public Executor getMainExecutor() { return Runnable::run; }
    public ContentResolver getContentResolver() { IndependentFaults.read(); return resolver; }
    public Resources getResources() { IndependentFaults.read(); return resources; }
    public Window getWindow() { IndependentFaults.read(); return window; }
    public boolean isDestroyed() { IndependentFaults.read(); return destroyed; }
}
