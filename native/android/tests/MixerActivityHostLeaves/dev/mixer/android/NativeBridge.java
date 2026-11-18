package dev.mixer.android;

class NativeBridge {
    static long session;

    static long create() {
        if (session != 0) throw new AssertionError("Previous session was not destroyed");
        session = 1;
        return session;
    }

    static byte[] exchange(long handle, int action, byte[] input) {
        if (handle != session || session == 0 || action != 0) throw new AssertionError("Expected initial render");
        return new byte[] {42};
    }

    static void destroy(long handle) {
        if (handle != session || session == 0) throw new AssertionError("Invalid session teardown");
        session = 0;
    }
}
