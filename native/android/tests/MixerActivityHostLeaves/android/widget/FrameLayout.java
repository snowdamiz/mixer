package android.widget;

import android.app.Activity;
import android.view.View;

public class FrameLayout extends View {
    public View child;

    public FrameLayout(Activity owner) {}
    public void setBackgroundColor(int color) {}
    public void removeAllViews() { child = null; }

    public void addView(View view, LayoutParams params) {
        child = view;
        view.parent = this;
    }

    public static class LayoutParams {
        public LayoutParams(int width, int height) {}
    }
}
