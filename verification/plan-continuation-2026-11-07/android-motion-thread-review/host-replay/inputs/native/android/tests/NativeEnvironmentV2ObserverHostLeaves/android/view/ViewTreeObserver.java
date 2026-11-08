package android.view;
public final class ViewTreeObserver {
    public interface OnWindowFocusChangeListener { void onWindowFocusChanged(boolean focused); }
    public boolean alive = true;
    public int adds, removes;
    public boolean isAlive() { return alive; }
    public void addOnWindowFocusChangeListener(OnWindowFocusChangeListener listener) { adds++; dev.mixer.android.ObserverHostProbe.add(3, this, listener); }
    public void removeOnWindowFocusChangeListener(OnWindowFocusChangeListener listener) { removes++; dev.mixer.android.ObserverHostProbe.remove(3, this, listener); }
}
