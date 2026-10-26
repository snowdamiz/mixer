package android.view;
import dev.mixer.android.IndependentFaults;
public final class ViewTreeObserver {
    public interface OnWindowFocusChangeListener { void onWindowFocusChanged(boolean focused); }
    public boolean alive = true;
    public OnWindowFocusChangeListener savedFocus;
    public boolean isAlive() { return alive; }
    public void addOnWindowFocusChangeListener(OnWindowFocusChangeListener listener) {
        savedFocus = listener; IndependentFaults.add("window-focus", this, listener);
    }
    public void removeOnWindowFocusChangeListener(OnWindowFocusChangeListener listener) {
        if (!alive) throw new IllegalStateException("independent dead VTO removal");
        IndependentFaults.remove("window-focus", this, listener);
    }
}
