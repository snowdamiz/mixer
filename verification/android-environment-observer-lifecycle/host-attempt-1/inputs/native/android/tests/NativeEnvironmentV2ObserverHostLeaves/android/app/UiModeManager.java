package android.app;
public final class UiModeManager {
    public interface ContrastChangeListener { void onContrastChanged(float contrast); }
    public void addContrastChangeListener(java.util.concurrent.Executor executor, ContrastChangeListener listener) { dev.mixer.android.ObserverHostProbe.add(5, this, listener); }
    public void removeContrastChangeListener(ContrastChangeListener listener) { dev.mixer.android.ObserverHostProbe.remove(5, this, listener); }
    public float getContrast() { return 0; }
}
