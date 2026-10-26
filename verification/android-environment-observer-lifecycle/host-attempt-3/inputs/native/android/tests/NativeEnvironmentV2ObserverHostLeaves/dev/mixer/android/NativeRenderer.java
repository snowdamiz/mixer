package dev.mixer.android;
final class NativeRenderer {
    int invalidations;
    Runnable notification;
    void environmentInvalidatedV2() { invalidations++; if (notification != null) notification.run(); }
}
