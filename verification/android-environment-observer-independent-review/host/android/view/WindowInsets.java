package android.view;
import android.graphics.Insets;
import dev.mixer.android.IndependentFaults;
public final class WindowInsets {
    public Insets value = new Insets(0, 0, 0, 0);
    public Insets getInsets(int mask) { IndependentFaults.read(); return value; }
    public static final class Type {
        private Type() { }
        public static int systemBars() { return 1; }
        public static int displayCutout() { return 2; }
    }
}
