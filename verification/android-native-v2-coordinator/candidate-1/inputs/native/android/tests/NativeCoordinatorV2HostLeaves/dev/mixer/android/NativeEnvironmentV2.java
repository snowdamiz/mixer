package dev.mixer.android;
/** TEST ONLY: controlled capture freshness, not a window/environment implementation. */
final class NativeEnvironmentV2 {
    boolean current(Object owner) {
        NativeCoordinatorV2HostTests.Rig.step("environment.current");
        return NativeCoordinatorV2HostTests.Rig.environmentCurrent;
    }
}
