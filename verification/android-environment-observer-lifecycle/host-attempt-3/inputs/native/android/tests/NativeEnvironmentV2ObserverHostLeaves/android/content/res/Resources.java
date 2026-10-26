package android.content.res;
public final class Resources {
    private final Configuration config = new Configuration();
    private final android.util.DisplayMetrics metrics = new android.util.DisplayMetrics();
    public Configuration getConfiguration() { dev.mixer.android.ObserverHostProbe.reads++; return config; }
    public android.util.DisplayMetrics getDisplayMetrics() { return metrics; }
}
