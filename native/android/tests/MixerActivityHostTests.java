package dev.mixer.android;

import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.WindowInsetsController;

public final class MixerActivityHostTests {
    public static void main(String[] args) {
        for (int api : new int[] {36, 30, 28}) {
            Build.VERSION.SDK_INT = api;
            MixerActivity activity = new MixerActivity();
            activity.onCreate(new Bundle());

            check(activity.content != null && activity.content.child != null, api, "starter did not render");
            check(NativeBridge.session != 0, api, "session was not created");
            if (api >= 30) {
                int expected = WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                        | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS;
                check(activity.getWindow().getInsetsController().appearance == expected, api, "missing light bars");
            } else {
                int expected = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;
                check(activity.getWindow().getDecorView().systemUiVisibility == expected, api, "missing legacy light bars");
            }

            activity.onDestroy();
            check(NativeBridge.session == 0, api, "session was not destroyed");
            System.out.println("PASS default starter lifecycle API " + api);
        }
    }

    private static void check(boolean condition, int api, String message) {
        if (!condition) throw new AssertionError("API " + api + ": " + message);
    }
}
