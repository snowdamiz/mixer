package android.view;
import android.content.Context;
import dev.mixer.android.IndependentFaults;
public class View {
    public interface OnLayoutChangeListener {
        void onLayoutChange(View view, int l, int t, int r, int b, int ol, int ot, int or, int ob);
    }
    public interface OnAttachStateChangeListener {
        void onViewAttachedToWindow(View view);
        void onViewDetachedFromWindow(View view);
    }
    public interface OnApplyWindowInsetsListener { WindowInsets onApplyWindowInsets(View view, WindowInsets insets); }
    public static final int LAYOUT_DIRECTION_RTL = 1;
    public final Context context;
    public int width = 320, height = 640, direction;
    public boolean attached = true;
    public Object token = new Object();
    public WindowInsets insets = new WindowInsets();
    public ViewTreeObserver tree = new ViewTreeObserver();
    public OnLayoutChangeListener savedLayout;
    public OnAttachStateChangeListener savedAttach;
    public OnApplyWindowInsetsListener savedInsets;
    public OnApplyWindowInsetsListener currentInsets;
    public View(Context value) { context = value; }
    public Context getContext() { IndependentFaults.read(); return context; }
    public int getWidth() { IndependentFaults.read(); return width; }
    public int getHeight() { IndependentFaults.read(); return height; }
    public Object getWindowToken() { IndependentFaults.read(); return token; }
    public boolean isAttachedToWindow() { IndependentFaults.read(); return attached; }
    public int getLayoutDirection() { IndependentFaults.read(); return direction; }
    public WindowInsets getRootWindowInsets() { IndependentFaults.read(); return insets; }
    public void getLocationInWindow(int[] destination) { IndependentFaults.read(); destination[0] = 0; destination[1] = 0; }
    public ViewTreeObserver getViewTreeObserver() { IndependentFaults.read(); return tree; }
    public void addOnLayoutChangeListener(OnLayoutChangeListener listener) {
        savedLayout = listener; IndependentFaults.add("layout", this, listener);
    }
    public void removeOnLayoutChangeListener(OnLayoutChangeListener listener) {
        IndependentFaults.remove("layout", this, listener);
    }
    public void addOnAttachStateChangeListener(OnAttachStateChangeListener listener) {
        savedAttach = listener; IndependentFaults.add("attach", this, listener);
    }
    public void removeOnAttachStateChangeListener(OnAttachStateChangeListener listener) {
        IndependentFaults.remove("attach", this, listener);
    }
    public void setOnApplyWindowInsetsListener(OnApplyWindowInsetsListener listener) {
        if (listener != null) {
            savedInsets = listener;
            IndependentFaults.add("insets", this, listener, () -> currentInsets = listener);
        } else {
            IndependentFaults.remove("insets", this, savedInsets, () -> currentInsets = null);
        }
    }
}
