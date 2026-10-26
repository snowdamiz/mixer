package dev.mixer.android;
final class AppearanceDescriptorV2 {
    enum Error { unsupportedNativeOperation }
    static final class Failure extends RuntimeException { private static final long serialVersionUID = 1L; Failure(Error value) { super(value.toString()); } }
    enum Profile { p0,p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11 }
}
