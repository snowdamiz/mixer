package android.view.accessibility;
public final class AccessibilityManager {
    public interface HighContrastTextStateChangeListener { void onHighContrastTextStateChanged(boolean enabled); }
    public void addHighContrastTextStateChangeListener(java.util.concurrent.Executor executor, HighContrastTextStateChangeListener listener) { dev.mixer.android.ObserverHostProbe.add(6, this, listener); }
    public void removeHighContrastTextStateChangeListener(HighContrastTextStateChangeListener listener) { dev.mixer.android.ObserverHostProbe.remove(6, this, listener); }
    public boolean isHighContrastTextEnabled() { return false; }
}
