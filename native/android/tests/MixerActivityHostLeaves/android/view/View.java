package android.view;

public class View {
    public static final int SYSTEM_UI_FLAG_LIGHT_STATUS_BAR = 8192;
    public static final int SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR = 16;
    public int systemUiVisibility;
    public Object parent;

    public interface OnApplyWindowInsetsListener {
        WindowInsets onApplyWindowInsets(View view, WindowInsets insets);
    }

    public void setOnApplyWindowInsetsListener(OnApplyWindowInsetsListener listener) {}
    public void setPadding(int left, int top, int right, int bottom) {}
    public void setSystemUiVisibility(int flags) { systemUiVisibility = flags; }
    public Object getParent() { return parent; }
}
