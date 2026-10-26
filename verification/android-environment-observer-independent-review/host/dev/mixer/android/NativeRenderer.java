package dev.mixer.android;
final class NativeRenderer {
    int notifications;
    Runnable invalidationHook;
    void environmentInvalidatedV2() {
        notifications++;
        if (invalidationHook != null) invalidationHook.run();
    }
}
