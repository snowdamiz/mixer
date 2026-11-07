package android.animation;
import java.util.ArrayList;
import java.util.List;
import dev.mixer.android.ConcreteHostProbe;
public final class ValueAnimator {
    public interface DurationScaleChangeListener { void onChanged(float scale); }
    private static final List<DurationScaleChangeListener> listeners=new ArrayList<>();
    public static float getDurationScale() {
        ConcreteHostProbe.hit("ValueAnimator.getDurationScale");
        float value=1;
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
