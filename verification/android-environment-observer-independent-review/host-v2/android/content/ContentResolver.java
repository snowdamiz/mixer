package android.content;
import android.database.ContentObserver;
import android.net.Uri;
import dev.mixer.android.IndependentFaults;
public final class ContentResolver {
    public ContentObserver savedObserver;
    public float animator = 1;
    public void registerContentObserver(Uri uri, boolean descendants, ContentObserver observer) {
        savedObserver = observer;
        IndependentFaults.add("animator-settings", this, observer);
    }
    public void unregisterContentObserver(ContentObserver observer) {
        IndependentFaults.remove("animator-settings", this, observer);
    }
}
