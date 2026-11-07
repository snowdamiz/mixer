package android.animation;
import java.util.ArrayList;
import java.util.List;
import dev.mixer.android.OwnerHostProbe;
public final class ValueAnimator {
    public interface DurationScaleChangeListener { void onChanged(float scale); }
    private static final List<DurationScaleChangeListener> listeners=new ArrayList<>();
    public static float getDurationScale() {
        OwnerHostProbe.hit("ValueAnimator.getDurationScale");
        float value=1;
        OwnerHostProbe.hit("ValueAnimator.getDurationScale","beforeReturn");
        return value;
    }
    public static boolean registerDurationScaleChangeListener(DurationScaleChangeListener listener) {
        OwnerHostProbe.hit("ValueAnimator.registerDurationScaleChangeListener","entry",ValueAnimator.class);
        boolean added=!listeners.contains(listener);if(added)listeners.add(listener);
        OwnerHostProbe.hit("ValueAnimator.registerDurationScaleChangeListener","beforeReturn",ValueAnimator.class);
        return added;
    }
    public static boolean unregisterDurationScaleChangeListener(DurationScaleChangeListener listener) {
        OwnerHostProbe.hit("ValueAnimator.unregisterDurationScaleChangeListener","entry",ValueAnimator.class);
        boolean removed=listeners.remove(listener);
        OwnerHostProbe.hit("ValueAnimator.unregisterDurationScaleChangeListener","beforeReturn",ValueAnimator.class);
        return removed;
    }
}
