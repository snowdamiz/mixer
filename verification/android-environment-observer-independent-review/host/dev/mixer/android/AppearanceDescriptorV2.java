package dev.mixer.android;
final class AppearanceDescriptorV2 {
    private AppearanceDescriptorV2() { }
    enum Error { unsupportedNativeOperation }
    enum Profile { p0, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11 }
    static final class Failure extends RuntimeException {
        private static final long serialVersionUID = 1L;
        final Error error;
        Failure(Error value) { super(value.name()); error = value; }
    }
}
