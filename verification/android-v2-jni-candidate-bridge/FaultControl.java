package dev.mixer.android;

/** Test-derived bridge only. This class and hooks never enter the application. */
final class FaultControl {
    static { System.loadLibrary("mixer_android_jni"); }
    private static Throwable constructorFailure;
    private static int point;
    static native void configure(int point,int cleanup,Throwable failure);
    static native long[] stats();
    static void arm(int value,int cleanup,Throwable failure) {
        point=value;constructorFailure=failure;configure(value,cleanup,failure);
    }
    static byte[] clonePacket(byte[] packet) {
        if(point==9) throw (OutOfMemoryError)constructorFailure;
        return packet.clone();
    }
    private FaultControl() {}
}
