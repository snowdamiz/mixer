package android.app;
public final class UiModeManager {
    public interface ContrastChangeListener { void onContrastChanged(float contrast); }
    public void addContrastChangeListener(java.util.concurrent.Executor executor,ContrastChangeListener listener) {
        dev.mixer.android.ObserverHostProbe.executors[5]=executor;
        dev.mixer.android.ObserverHostProbe.add(5,this,listener);
    }
    public void removeContrastChangeListener(ContrastChangeListener listener) { dev.mixer.android.ObserverHostProbe.remove(5,this,listener); }
    public float getContrast() { dev.mixer.android.ObserverHostProbe.read("contrast",34); return dev.mixer.android.ObserverHostProbe.contrast; }
}
