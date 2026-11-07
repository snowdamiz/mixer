package android.view;
public class View {
    public interface OnLayoutChangeListener { void onLayoutChange(View v, int l, int t, int r, int b, int ol, int ot, int or, int ob); }
    public interface OnAttachStateChangeListener { void onViewAttachedToWindow(View view); void onViewDetachedFromWindow(View view); }
    public interface OnApplyWindowInsetsListener { WindowInsets onApplyWindowInsets(View view, WindowInsets insets); }
    public static final int LAYOUT_DIRECTION_RTL = 1;
    private final android.content.Context context;
    private final Object token = new Object();
    public ViewTreeObserver tree = new ViewTreeObserver();
    public OnApplyWindowInsetsListener insetListener;
    public View(android.content.Context context) { this.context = context; }
    public android.content.Context getContext() { return context; }
    public void addOnLayoutChangeListener(OnLayoutChangeListener listener) { dev.mixer.android.ObserverHostProbe.add(1, this, listener); }
    public void removeOnLayoutChangeListener(OnLayoutChangeListener listener) { dev.mixer.android.ObserverHostProbe.remove(1, this, listener); }
    public void addOnAttachStateChangeListener(OnAttachStateChangeListener listener) { dev.mixer.android.ObserverHostProbe.add(2, this, listener); }
    public void removeOnAttachStateChangeListener(OnAttachStateChangeListener listener) { dev.mixer.android.ObserverHostProbe.remove(2, this, listener); }
    public ViewTreeObserver getViewTreeObserver() { return tree; }
    public void setOnApplyWindowInsetsListener(OnApplyWindowInsetsListener listener) {
        if (listener == null) { dev.mixer.android.ObserverHostProbe.remove(4, this, insetListener); insetListener = null; }
        else { insetListener = listener; dev.mixer.android.ObserverHostProbe.add(4, this, listener); }
    }
    public Object getWindowToken() { dev.mixer.android.ObserverHostProbe.tokenReads++; return token; }
    public boolean isAttachedToWindow() { return true; }
    public int getWidth() { return 320; }
    public int getHeight() { return 640; }
    public int getLayoutDirection() { return 0; }
    public WindowInsets getRootWindowInsets() { return new WindowInsets(); }
    public void getLocationInWindow(int[] result) { result[0] = 0; result[1] = 0; }
}
