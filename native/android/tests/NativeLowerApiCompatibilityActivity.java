package dev.mixer.android;

import android.app.Activity;
import android.os.Bundle;
import android.widget.FrameLayout;

/** Private ordinary window; all rendering and platform reads use the retained product DEX. */
public final class NativeLowerApiCompatibilityActivity extends Activity {
    FrameLayout root;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        root = new FrameLayout(this);
        setContentView(root);
    }
}
