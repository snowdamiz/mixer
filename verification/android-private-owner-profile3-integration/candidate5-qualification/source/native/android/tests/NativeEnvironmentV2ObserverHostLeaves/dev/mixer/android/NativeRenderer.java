package dev.mixer.android;
final class NativeRenderer {
    android.content.Context context;
    boolean belongsToV2(android.content.Context candidate,NativeEnvironmentV2.Observer observer){return context==candidate;}
    int invalidations;
    Runnable notification;
    void environmentInvalidatedV2() { invalidations++; if (notification != null) notification.run(); }
}
