package android.view.accessibility;
import java.util.concurrent.Executor;
import dev.mixer.android.IndependentFaults;
public final class AccessibilityManager {
    public interface HighContrastTextStateChangeListener { void onHighContrastTextStateChanged(boolean enabled); }
    public HighContrastTextStateChangeListener savedHighContrast;
    public boolean highContrast;
    public void addHighContrastTextStateChangeListener(Executor executor, HighContrastTextStateChangeListener listener) {
        savedHighContrast = listener; IndependentFaults.add("high-contrast", this, listener);
    }
    public void removeHighContrastTextStateChangeListener(HighContrastTextStateChangeListener listener) {
        IndependentFaults.remove("high-contrast", this, listener);
    }
    public boolean isHighContrastTextEnabled() { IndependentFaults.read(); return highContrast; }
}
