package android.util;
public final class TypedValue {
    public static final int COMPLEX_UNIT_DIP=1, COMPLEX_UNIT_SP=2;
    public static float applyDimension(int kind,float value,DisplayMetrics metrics) {
        dev.mixer.android.ObserverHostProbe.read(kind==COMPLEX_UNIT_DIP?"dp":"sp",28);
        return kind==COMPLEX_UNIT_DIP ? dev.mixer.android.ObserverHostProbe.dp : dev.mixer.android.ObserverHostProbe.sp;
    }
}
