package android.util;
public final class TypedValue {
    public static final int COMPLEX_UNIT_DIP = 1, COMPLEX_UNIT_SP = 2;
    public static float applyDimension(int kind, float value, DisplayMetrics metrics) { return value * metrics.density; }
}
