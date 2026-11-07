package dev.mixer.android;
final class NativeBridge {
    static { System.loadLibrary("mixer_android_jni"); }
    static native long create();
    static native byte[] exchange(long handle,int operation,byte[] input);
    static native void destroy(long handle);
    // Private ordinary-native staging only. A token is an opaque UInt64 bit
    // pattern: Java's sign bit has no meaning, and only zero is invalid.
    static final class Candidate {
        private final long token;
        private final byte[] packet;
        private Candidate(long token,byte[] packet) {
            if(token==0 || packet==null) throw new IllegalArgumentException("Mixer invalid candidate");
            this.token=token;
            this.packet=packet.clone();
        }
        long token() { return token; }
        byte[] packet() { return packet.clone(); }
    }
    static native Candidate prepareV2(long handle,int operation,byte[] input);
    static native int commitV2(long handle,long token);
    static native int abortV2(long handle,long token);
    private NativeBridge() {}
}
