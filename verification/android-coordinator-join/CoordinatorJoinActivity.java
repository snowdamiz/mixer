package dev.mixer.android;

import android.app.Activity;
import android.os.Bundle;
import android.widget.FrameLayout;

/** Verification owner only; the product coordinator and public Activity are unchanged. */
@SuppressWarnings("deprecation")
public final class CoordinatorJoinActivity extends Activity {
    FrameLayout root;
    NativeCoordinatorV2 coordinator;
    boolean destroyed;

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
            destroyed = true;
            super.onDestroy();
        }
    }
}
