package android.content.res;
public final class Resources {
    public Configuration config=new Configuration();
    public android.util.DisplayMetrics metrics=new android.util.DisplayMetrics();
    public Configuration getConfiguration() { dev.mixer.android.ObserverHostProbe.reads++; dev.mixer.android.ObserverHostProbe.read("config",28); return config; }
    public android.util.DisplayMetrics getDisplayMetrics() { dev.mixer.android.ObserverHostProbe.read("metrics",28); return metrics; }
}
