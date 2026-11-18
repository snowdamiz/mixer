package dev.mixer.android;

import android.app.Activity;
import android.view.View;
import java.util.function.Consumer;

class NativeRenderer {
    NativeRenderer(Activity owner, Consumer<byte[]> events) {}

    View apply(UiPacket packet) {
        return new View();
    }
}
