package android.view.accessibility;
public final class AccessibilityManager {
 public boolean local;
 public interface HighContrastTextStateChangeListener { void onHighContrastTextStateChanged(boolean enabled); }
 public void addHighContrastTextStateChangeListener(java.util.concurrent.Executor executor,HighContrastTextStateChangeListener listener) { dev.mixer.android.ObserverHostProbe.executors[6]=executor;dev.mixer.android.ObserverHostProbe.add(6,this,listener); }
 public void removeHighContrastTextStateChangeListener(HighContrastTextStateChangeListener listener) { dev.mixer.android.ObserverHostProbe.remove(6,this,listener); }
 public boolean isHighContrastTextEnabled() { dev.mixer.android.ObserverHostProbe.read("high",36);return local||dev.mixer.android.ObserverHostProbe.highContrast; }
}
