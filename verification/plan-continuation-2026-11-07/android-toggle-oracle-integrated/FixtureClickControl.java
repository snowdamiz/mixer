package dev.mixer.android;

public final class FixtureClickControl {
    private FixtureClickControl() {}
    public static void main(String[] arguments) {
        System.out.println("PASS controlled fixture checks=" + NativeAndroidFixtureHostTests.run());
    }
}
