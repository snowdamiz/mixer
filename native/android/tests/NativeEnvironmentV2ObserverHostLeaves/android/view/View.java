package android.view;
public class View {
    public interface OnLayoutChangeListener { void onLayoutChange(View v, int l, int t, int r, int b, int ol, int ot, int or, int ob); }
    public interface OnAttachStateChangeListener { void onViewAttachedToWindow(View view); void onViewDetachedFromWindow(View view); }
    public interface OnApplyWindowInsetsListener { WindowInsets onApplyWindowInsets(View view, WindowInsets insets); }
    public static final int LAYOUT_DIRECTION_RTL = 1, LAYOUT_DIRECTION_LTR = 0;
    public int width=320,height=640,direction,x,y;
    public boolean attached=true;
    public Object windowToken=new Object();
    public WindowInsets rootInsets=new WindowInsets();
    private final android.content.Context context;
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
    public Object getWindowToken() { dev.mixer.android.ObserverHostProbe.tokenReads++; dev.mixer.android.ObserverHostProbe.read("token",28); return windowToken; }
    public boolean isAttachedToWindow() { return attached; }
    public int getWidth() { return width; }
    public int getHeight() { return height; }
    public int getLayoutDirection() { dev.mixer.android.ObserverHostProbe.read("direction",28); return direction; }
    public WindowInsets getRootWindowInsets() { return rootInsets; }
    public void getLocationInWindow(int[] result) { result[0] = x; result[1] = y; }
}
