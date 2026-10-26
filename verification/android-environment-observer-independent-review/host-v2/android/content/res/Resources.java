package android.content.res;
import android.util.DisplayMetrics;
import dev.mixer.android.IndependentFaults;
public final class Resources {
    public final Configuration configuration = new Configuration();
    public final DisplayMetrics metrics = new DisplayMetrics();
    public Configuration getConfiguration() { IndependentFaults.read(); return configuration; }
    public DisplayMetrics getDisplayMetrics() { IndependentFaults.read(); return metrics; }
}
