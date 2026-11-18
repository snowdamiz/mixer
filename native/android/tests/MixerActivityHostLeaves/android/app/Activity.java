package android.app;

import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.widget.FrameLayout;

public class Activity {
    private final Window window = new Window();
    public FrameLayout content;

    public void onCreate(Bundle saved) {}
    public void onDestroy() {}
    public Window getWindow() { return window; }

    public void setContentView(View view) {
        window.getDecorView();
        content = (FrameLayout) view;
    }
}
