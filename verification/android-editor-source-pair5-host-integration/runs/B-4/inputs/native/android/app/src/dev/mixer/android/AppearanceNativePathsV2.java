package dev.mixer.android;

import android.graphics.Path;

/** Native paths for the closed measuredShared2 geometry. No renderer authority. */
final class AppearanceNativePathsV2 {
    private AppearanceNativePathsV2() {}

    /**
     * Returns a fresh caller-owned mutable path in local pixels, with origin (0,0).
     * The caller supplies normalized density and owns later placement and clipping;
     * applying another density transform would scale this geometry twice.
     */
    static Path make(AppearanceGeometryV2.Path geometry, int density1024) {
        if (geometry == null) throw new IllegalArgumentException("geometry is required");
        // Validate even empty geometry before allocating a native object.
        AppearanceGeometryV2.pixelCoordinate(0, density1024);
        Path result = new Path();
        result.setFillType(Path.FillType.WINDING);
        for (var command : geometry.commands) {
            var points = command.points();
            switch (command.op()) {
                case move -> {
                    var point = points.get(0);
                    result.moveTo(pixel(point.x64(), density1024), pixel(point.y64(), density1024));
                }
                case line -> {
                    var point = points.get(0);
                    result.lineTo(pixel(point.x64(), density1024), pixel(point.y64(), density1024));
                }
                case cubic -> {
                    var first = points.get(0);
                    var second = points.get(1);
                    var end = points.get(2);
                    result.cubicTo(pixel(first.x64(), density1024), pixel(first.y64(), density1024),
                        pixel(second.x64(), density1024), pixel(second.y64(), density1024),
                        pixel(end.x64(), density1024), pixel(end.y64(), density1024));
                }
                case close -> result.close();
                default -> throw new IllegalArgumentException("unsupported geometry operation");
            }
        }
        return result;
    }

    private static float pixel(int coordinate64, int density1024) {
        // Android Path stores floats. Preserve fractional controls until this one
        // required double-to-float conversion; integer pixel-edge rounding is separate.
        return (float) AppearanceGeometryV2.pixelCoordinate(coordinate64, density1024);
    }
}
