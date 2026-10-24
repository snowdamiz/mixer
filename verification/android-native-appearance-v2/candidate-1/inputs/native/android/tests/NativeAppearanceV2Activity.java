package dev.mixer.android;

import android.app.Activity;
import android.os.Bundle;
import android.widget.FrameLayout;

/** Repository-only window for the actual private renderer. No engine/JNI integration. */
@SuppressWarnings("deprecation")
public final class NativeAppearanceV2Activity extends Activity {
    FrameLayout root;
    @Override public void onCreate(Bundle state){super.onCreate(state);getWindow().setDecorFitsSystemWindows(false);
        root=new FrameLayout(this);setContentView(root);}
}
