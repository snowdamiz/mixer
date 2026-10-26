package android.content;
public final class ContentResolver {
    public void registerContentObserver(android.net.Uri uri, boolean descendants, android.database.ContentObserver observer) { dev.mixer.android.ObserverHostProbe.add(7, this, observer); }
    public void unregisterContentObserver(android.database.ContentObserver observer) { dev.mixer.android.ObserverHostProbe.remove(7, this, observer); }
}
