package android.animation;
import java.util.ArrayList;
import java.util.List;
import dev.mixer.android.ConcreteHostProbe;
public final class ValueAnimator {
    public interface DurationScaleChangeListener { void onChanged(float scale); }
    public static float effectiveScale=1;
    private static final List<DurationScaleChangeListener> listeners=new ArrayList<>();
    public static float getDurationScale() {
        ConcreteHostProbe.hit("ValueAnimator.getDurationScale");
        if(android.os.Looper.myLooper()!=android.os.Looper.getMainLooper())throw new AssertionError("background effective getter");
        float value=effectiveScale;
        ConcreteHostProbe.hit("ValueAnimator.getDurationScale","beforeReturn");
        return value;
    }
    public static boolean registerDurationScaleChangeListener(DurationScaleChangeListener listener) {
        ConcreteHostProbe.hit("ValueAnimator.registerDurationScaleChangeListener","entry",ValueAnimator.class);
        boolean added=!listeners.contains(listener);if(added)listeners.add(listener);
        ConcreteHostProbe.hit("ValueAnimator.registerDurationScaleChangeListener","beforeReturn",ValueAnimator.class);
        return added;
    }
    public static boolean unregisterDurationScaleChangeListener(DurationScaleChangeListener listener) {
        ConcreteHostProbe.hit("ValueAnimator.unregisterDurationScaleChangeListener","entry",ValueAnimator.class);
        boolean removed=listeners.remove(listener);
        ConcreteHostProbe.hit("ValueAnimator.unregisterDurationScaleChangeListener","beforeReturn",ValueAnimator.class);
        return removed;
    }
}
