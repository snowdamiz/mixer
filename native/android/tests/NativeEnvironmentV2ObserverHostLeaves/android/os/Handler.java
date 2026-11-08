package android.os;
import java.util.concurrent.ConcurrentLinkedQueue;
/** A real cross-thread queue; only its creating UI thread may drain it. */
public final class Handler {
    private static final ConcurrentLinkedQueue<Runnable> WORK = new ConcurrentLinkedQueue<>();
    public static boolean postResult = true;
    public static Throwable postFailure;
    public static Runnable beforeEnqueue;
    public Handler(Looper looper) {
        if (looper != Looper.getMainLooper()) throw new AssertionError("wrong UI looper");
    }
    public boolean post(Runnable work) {
        if (postFailure instanceof Error) throw (Error)postFailure;
        if (postFailure != null) throw (RuntimeException)postFailure;
        if (beforeEnqueue != null) beforeEnqueue.run();
        if (postResult) WORK.add(work);
        return postResult;
    }
    public static int pending() { return WORK.size(); }
    public static void drain() {
        if (Looper.myLooper() != Looper.getMainLooper()) throw new AssertionError("background queue drain");
        int count = 0;
        for (Runnable work; (work = WORK.poll()) != null;) {
            if (++count > 32) throw new AssertionError("queue bound");
            work.run();
        }
    }
    public static void reset() { WORK.clear(); postResult = true; postFailure = null; beforeEnqueue = null; }
}
