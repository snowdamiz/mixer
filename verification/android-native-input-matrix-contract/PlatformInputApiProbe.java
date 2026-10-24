import android.app.Activity;
import android.app.Instrumentation;
import android.graphics.Rect;
import android.os.SystemClock;
import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewConfiguration;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.EditText;

/** Compile-only public SDK linkage witness. No entry point; never executed or packaged. */
final class PlatformInputApiProbe {
    private PlatformInputApiProbe() {}

    static void link(Instrumentation instrumentation, Activity activity, View target,
                     EditText editor, MotionEvent event, KeyEvent key) {
        instrumentation.sendPointerSync(event);
        instrumentation.sendKeySync(key);
        instrumentation.runOnMainSync(() -> target.getLocationOnScreen(new int[2]));
        instrumentation.waitForIdleSync();
        activity.dispatchTouchEvent(event);
        target.getGlobalVisibleRect(new Rect());
        target.isAttachedToWindow();
        target.hasWindowFocus();
        ViewConfiguration configuration = ViewConfiguration.get(activity);
        configuration.getScaledTouchSlop();
        configuration.getScaledMinimumFlingVelocity();
        ViewConfiguration.getLongPressTimeout();
        ViewConfiguration.getTapTimeout();
        MotionEvent.PointerProperties pointer = new MotionEvent.PointerProperties();
        pointer.id = 0;
        pointer.toolType = MotionEvent.TOOL_TYPE_FINGER;
        MotionEvent.PointerCoords coordinates = new MotionEvent.PointerCoords();
        coordinates.x = 1;
        coordinates.y = 1;
        coordinates.pressure = 1;
        long time = SystemClock.uptimeMillis();
        MotionEvent constructed = MotionEvent.obtain(time, time, MotionEvent.ACTION_CANCEL,
            1, new MotionEvent.PointerProperties[]{pointer},
            new MotionEvent.PointerCoords[]{coordinates}, 0, 0, 1, 1,
            0, 0, InputDevice.SOURCE_TOUCHSCREEN, MotionEvent.FLAG_CANCELED);
        try {
            constructed.getActionMasked();
            constructed.getPointerId(0);
            constructed.getRawX();
            constructed.getRawY();
            constructed.getSource();
            constructed.getHistorySize();
            constructed.getHistoricalEventTime(0);
            constructed.getHistoricalX(0, 0);
            constructed.getHistoricalY(0, 0);
        } finally { constructed.recycle(); }
        InputConnection connection = editor.onCreateInputConnection(new EditorInfo());
        if (connection != null) {
            connection.setComposingText("ab", 1);
            connection.setSelection(0, 1);
            connection.finishComposingText();
            connection.deleteSurroundingTextInCodePoints(1, 0);
            connection.commitText("c", 1);
        }
    }
}
