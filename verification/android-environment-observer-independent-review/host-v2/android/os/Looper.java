package android.os;
public final class Looper {
    private static final Looper MAIN = new Looper();
    private static final Looper OTHER = new Looper();
    private static boolean main = true;
    private Looper() { }
    public static Looper getMainLooper() { return MAIN; }
    public static Looper myLooper() { return main ? MAIN : OTHER; }
    public static void setMain(boolean value) { main = value; }
}
