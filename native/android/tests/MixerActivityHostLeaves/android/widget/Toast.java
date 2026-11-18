package android.widget;

import android.app.Activity;

public class Toast {
    public static final int LENGTH_SHORT = 0;

    public static Toast makeText(Activity owner, String message, int duration) {
        throw new AssertionError(message);
    }

    public void show() {}
}
