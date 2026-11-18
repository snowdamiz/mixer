package android.view;

public class WindowInsetsController {
    public static final int APPEARANCE_LIGHT_STATUS_BARS = 8;
    public static final int APPEARANCE_LIGHT_NAVIGATION_BARS = 16;
    public int appearance;

    public void setSystemBarsAppearance(int value, int mask) {
        appearance = (appearance & ~mask) | (value & mask);
    }
}
