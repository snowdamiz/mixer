package dev.mixer.android;
final class NativeBridge {
    static { System.loadLibrary("mixer_android_jni"); }
    static native long create();
    static native byte[] exchange(long handle,int operation,byte[] input);
    static native void destroy(long handle);
    private NativeBridge() {}
}
