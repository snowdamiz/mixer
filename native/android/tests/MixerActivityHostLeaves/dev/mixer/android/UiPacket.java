package dev.mixer.android;

class UiPacket {
    static UiPacket decode(byte[] bytes) {
        if (bytes.length != 1 || bytes[0] != 42) throw new AssertionError("Initial render expected");
        return new UiPacket();
    }
}
