package dev.mixer.android;
final class AppearanceGeometryV2 {
    private AppearanceGeometryV2() { }
    static final int MAXIMUM_EXTENT64 = 16_777_216;
    static int normalizeDensity(float density) {
        if (!Float.isFinite(density) || density <= 0) throw new IllegalArgumentException("density");
        return (int) Math.floor(density * 1024 + .5);
    }
}
