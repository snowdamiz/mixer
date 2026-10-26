package android.provider;
import android.content.ContentResolver;
import android.net.Uri;
import dev.mixer.android.IndependentFaults;
public final class Settings {
    private Settings() { }
    public static final class Global {
        private Global() { }
        public static final String ANIMATOR_DURATION_SCALE = "animator_duration_scale";
        public static Uri getUriFor(String name) { return new Uri(name); }
        public static float getFloat(ContentResolver resolver, String name, float fallback) {
            IndependentFaults.read(); return resolver.animator;
        }
    }
}
