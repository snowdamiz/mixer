package android.animation;
import dev.mixer.android.ObserverHostProbe;
public final class ValueAnimator {
    public interface DurationScaleChangeListener { void onChanged(float scale); }
    private static void main() {
        if (android.os.Looper.myLooper() != android.os.Looper.getMainLooper() || android.os.Build.VERSION.SDK_INT < 33)
            throw new AssertionError("effective animator API/thread guard");
    }
    public static float getDurationScale() {
        main(); ObserverHostProbe.read("animator",33); return ObserverHostProbe.animator;
    }
    public static void changeFromProducer(float effective, float callback,
                                           DurationScaleChangeListener listener) {
        if (android.os.Looper.myLooper() == android.os.Looper.getMainLooper())
            throw new AssertionError("effective scale producer must be background");
        ObserverHostProbe.animator = effective; // Deliberately plain, as in the platform getter.
        listener.onChanged(callback);
    }
    public static boolean registerDurationScaleChangeListener(DurationScaleChangeListener listener) {
        main(); ObserverHostProbe.add(7,ValueAnimator.class,listener); return ObserverHostProbe.motionAdd;
    }
    public static boolean unregisterDurationScaleChangeListener(DurationScaleChangeListener listener) {
        main(); ObserverHostProbe.remove(7,ValueAnimator.class,listener); return ObserverHostProbe.motionRemove;
    }
}
