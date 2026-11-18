package android.view;

import android.os.Build;

public class Window {
    private Decor decor;

    public View getDecorView() {
        if (decor == null) decor = new Decor();
        return decor;
    }

    public WindowInsetsController getInsetsController() {
        if (Build.VERSION.SDK_INT < 30) throw new AssertionError("API 30 controller on an older device");
        return decor.insetsController; // PhoneWindow assumes the decor was installed.
    }

    private static class Decor extends View {
        final WindowInsetsController insetsController = new WindowInsetsController();
    }
}
