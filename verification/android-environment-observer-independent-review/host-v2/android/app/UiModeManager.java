package android.app;
import java.util.concurrent.Executor;
import dev.mixer.android.IndependentFaults;
public final class UiModeManager {
    public interface ContrastChangeListener { void onContrastChanged(float contrast); }
    public ContrastChangeListener savedContrast;
    public float contrast;
    public void addContrastChangeListener(Executor executor, ContrastChangeListener listener) {
        savedContrast = listener; IndependentFaults.add("contrast", this, listener);
    }
    public void removeContrastChangeListener(ContrastChangeListener listener) {
        IndependentFaults.remove("contrast", this, listener);
    }
    public float getContrast() { IndependentFaults.read(); return contrast; }
}
