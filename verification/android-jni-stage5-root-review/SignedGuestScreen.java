package dev.mixer.android;
// Declaration fixture only. Every Java body is permanently unavailable.
final class SignedGuestScreen {
    private SignedGuestScreen(android.app.Activity activity, long lifecycle, long presentation) {
        throw new UnsupportedOperationException("declaration-only");
    }
    private static native int nativeInstall();
    private static native int nativeAttach(long arg0, long arg1, dev.mixer.android.SignedGuestScreen arg2);
    private static native int nativeActivate(long arg0, long arg1, long arg2, long arg3, byte[] arg4, long arg5);
    private static native int nativeObserve(long arg0, long arg1, long arg2, long arg3, long arg4);
    private static native int nativeRequestClose(long arg0, int arg1);
    private static native int nativeDetachUI(long arg0, long arg1);
    private int applySigned(long arg0, long arg1, long arg2, byte[] arg3) { throw new UnsupportedOperationException("declaration-only"); }
    private int setInteraction(int arg0) { throw new UnsupportedOperationException("declaration-only"); }
    private int retireSigned(int arg0) { throw new UnsupportedOperationException("declaration-only"); }
    private int consumeObservation(long arg0, long arg1, long arg2, long arg3) { throw new UnsupportedOperationException("declaration-only"); }
}
