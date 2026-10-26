package dev.mixer.android;

import android.app.Activity;
import android.os.Bundle;
import android.widget.FrameLayout;

/** FUTURE NATIVE TEST ONLY. Not declared by the public app and not launched during the pause. */
@SuppressWarnings("deprecation")
public final class NativeCoordinatorV2IntegrationActivity extends Activity {
    FrameLayout root;
    NativeCoordinatorV2 coordinator;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setDecorFitsSystemWindows(false);
        root = new FrameLayout(this);
        setContentView(root);
    }

    @Override public void onDestroy() {
        try {
            if (coordinator != null && !coordinator.isRetired()) coordinator.close();
        } finally {
            super.onDestroy();
        }
    }
}
