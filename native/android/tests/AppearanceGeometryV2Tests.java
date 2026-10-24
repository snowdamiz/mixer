package dev.mixer.android;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public final class AppearanceGeometryV2Tests {
    private static String path(AppearanceGeometryV2.Path path) {
        StringBuilder result = new StringBuilder(path.shape.name()).append('|').append(path.width64).append(',').append(path.height64);
        try { path.commands.clear(); throw new AssertionError("mutable path"); } catch (UnsupportedOperationException expected) { /* immutable */ }
        for (var command : path.commands) {
            result.append('|').append(command.op().name());
            try { command.points().clear(); throw new AssertionError("mutable command"); } catch (UnsupportedOperationException expected) { /* immutable */ }
            for (var point : command.points()) {
                if (point.x64() < 0 || point.y64() < 0 || point.x64() > path.width64 || point.y64() > path.height64) throw new AssertionError("point outside extent");
                result.append(':').append(point.x64()).append(',').append(point.y64());
            }
        }
        return result.toString();
    }
    private static double input(String hex) { return Double.longBitsToDouble(Long.parseUnsignedLong(hex,16)); }
    private static String output(double value) { return String.format(java.util.Locale.ROOT,"%016x",Double.doubleToRawLongBits(value)); }
    private static String evaluate(String[] f) {
        return switch (f[1]) {
            case "group" -> path(AppearanceGeometryV2.group(Long.parseLong(f[2]),Long.parseLong(f[3]),Long.parseLong(f[4])));
            case "track" -> path(AppearanceGeometryV2.track());
            case "thumb" -> path(AppearanceGeometryV2.thumb());
            case "origin" -> {
                var point = AppearanceGeometryV2.thumbOrigin(f[2].equals("1"),AppearanceGeometryV2.Direction.valueOf(f[3]));
                yield point.x64() + "," + point.y64();
            }
            case "measure" -> Integer.toString(AppearanceGeometryV2.measuredExtent64(input(f[2])));
            case "spacing" -> Integer.toString(AppearanceGeometryV2.spacing64(input(f[2])));
            case "density" -> Integer.toString(AppearanceGeometryV2.normalizeDensity(input(f[2])));
            case "edge" -> Integer.toString(AppearanceGeometryV2.pixelEdge(Long.parseLong(f[2]),Integer.parseInt(f[3])));
            case "coordinate" -> output(AppearanceGeometryV2.pixelCoordinate(Long.parseLong(f[2]),Integer.parseInt(f[3])));
            default -> throw new AssertionError("unknown operation");
        };
    }
    public static void main(String[] args) throws Exception {
        int total = 0, failures = 0;
        for (String line : Files.readAllLines(Path.of(args[0]),StandardCharsets.US_ASCII)) {
            String[] f = line.split("\t",-1); String result;
            try { result = evaluate(f); } catch (AppearanceGeometryV2.Failure error) { result = "error:" + error.code.name(); failures++; }
            System.out.println(f[0] + "\t" + result); total++;
        }
        // Java's signed caller domain is wider than Swift's UInt32 signatures.
        for (long invalid : new long[]{-1,Long.MIN_VALUE,Long.MAX_VALUE,4294967296L}) {
            try { AppearanceGeometryV2.group(invalid,1,1); throw new AssertionError("bad width accepted"); } catch (AppearanceGeometryV2.Failure expected) { /* closed */ }
            try { AppearanceGeometryV2.pixelEdge(invalid,1024); throw new AssertionError("bad coordinate accepted"); } catch (AppearanceGeometryV2.Failure expected) { /* closed */ }
        }
        try { AppearanceGeometryV2.group(1,1,-1); throw new AssertionError("negative radius"); } catch (AppearanceGeometryV2.Failure expected) { /* closed */ }
        try { AppearanceGeometryV2.thumbOrigin(true,null); throw new AssertionError("null direction"); } catch (AppearanceGeometryV2.Failure expected) { /* closed */ }
        // Round absolute edges before subtracting: width 1 at x=31 differs from rounding width alone.
        int width = AppearanceGeometryV2.pixelEdge(32,1024) - AppearanceGeometryV2.pixelEdge(31,1024);
        if (width != 1 || AppearanceGeometryV2.pixelEdge(1,1024) != 0) throw new AssertionError("edge policy");
        System.err.println("PASS geometry cases=" + total + " rejected=" + failures + " signed-domain-and-immutability-checks=passed");
    }
}
