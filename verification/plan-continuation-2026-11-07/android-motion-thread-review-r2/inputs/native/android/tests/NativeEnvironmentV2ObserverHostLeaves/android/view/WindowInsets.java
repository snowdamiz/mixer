package android.view;
public final class WindowInsets {
    public final android.graphics.Insets value=new android.graphics.Insets();
    public android.graphics.Insets getInsets(int mask) {
        dev.mixer.android.ObserverHostProbe.read("insets",30);
        if(mask!=3) throw new AssertionError("inexact typed mask");
        return value;
    }
    public static final class Type {
        public static int systemBars() { dev.mixer.android.ObserverHostProbe.read("systemBars",30); return 1; }
        public static int displayCutout() { dev.mixer.android.ObserverHostProbe.read("displayCutout",30); return 2; }
    }
}
