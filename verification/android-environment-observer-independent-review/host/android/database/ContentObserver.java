package android.database;
import android.os.Handler;
public abstract class ContentObserver {
    public final Handler handler;
    protected ContentObserver(Handler value) { handler = value; }
    public void onChange(boolean selfChange) { }
}
