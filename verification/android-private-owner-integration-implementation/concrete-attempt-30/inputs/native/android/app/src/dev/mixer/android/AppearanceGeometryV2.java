package dev.mixer.android;

import java.util.List;

/** Closed authored measuredShared2 paths and checked coordinate conversions.
 * Contains no Android framework calls or arbitrary descriptor path parser. */
final class AppearanceGeometryV2 {
    private AppearanceGeometryV2() {}
    static final int MAXIMUM_EXTENT64 = 2147483647;
    enum Shape { fullGroupContinuousCubic2, track63x28Continuous2, thumb37x24Continuous2 }
    enum Direction { leftToRight, rightToLeft }
    enum Error { extent, radius, density, spacing }
    static final class Failure extends IllegalArgumentException {
        private static final long serialVersionUID = 1L;
        final Error code;
        Failure(Error code) { super(code.name()); this.code = code; }
    }
    record Point(int x64, int y64) {}
    enum Op { move, line, cubic, close }
    record Command(Op op, List<Point> points) {
        Command { points = List.copyOf(points); }
    }
    static final class Path {
        final Shape shape;
        final int width64, height64;
        final List<Command> commands;
        private Path(Shape shape, int width64, int height64, List<Command> commands) {
            this.shape = shape; this.width64 = width64; this.height64 = height64;
            this.commands = List.copyOf(commands);
        }
    }

    static Path group(long width64, long height64, long radius64) {
        extent(width64); extent(height64);
        admit(radius64 >= 0 && radius64 <= 65536, Error.radius);
        int w = (int)width64, h = (int)height64;
        if (w == 0 || h == 0) return new Path(Shape.fullGroupContinuousCubic2,w,h,List.of());
        // Inputs are nonnegative <= Int32.max. The largest product is below 2^51;
        // Java's signed long therefore preserves the contract's UInt64 arithmetic.
        long radius = Math.min(radius64, Math.min(width64,height64) * 1000000L / 3057330L);
        int a = offset(radius,1528665), b = offset(radius,1088490), c = offset(radius,868407);
        int d = offset(radius,631494), e = offset(radius,74911), f = offset(radius,169060), g = offset(radius,372824);
        return new Path(Shape.fullGroupContinuousCubic2,w,h,List.of(
            m(w,h / 2 + h % 2), l(w,h-a),
            c(w,h-b,w,h-c,w-e,h-d), c(w-f,h-g,w-g,h-f,w-d,h-e), c(w-c,h,w-b,h,w-a,h),
            l(a,h), c(b,h,c,h,d,h-e), c(g,h-f,f,h-g,e,h-d), c(0,h-c,0,h-b,0,h-a),
            l(0,a), c(0,b,0,c,e,d), c(f,g,g,f,d,e), c(c,0,b,0,a,0),
            l(w-a,0), c(w-b,0,w-c,0,w-d,e), c(w-g,f,w-f,g,w-e,d), c(w,c,w,b,w,a), close()));
    }
    private static int offset(long radius, int coefficient) { return (int)((radius * coefficient + 500000L) / 1000000L); }

    static Path track() {
        return new Path(Shape.track63x28Continuous2,4032,1792,List.of(
            m(4032,896),l(4032,896),
            c(4032,932,4032,1057,3965,1226), c(3881,1458,3698,1641,3466,1725), c(3254,1792,3057,1792,2662,1792),
            l(1370,1792), c(975,1792,778,1792,566,1725), c(334,1641,151,1458,67,1226), c(0,1057,0,932,0,896),
            l(0,896), c(0,860,0,735,67,566), c(151,334,334,151,566,67), c(778,0,975,0,1370,0),
            l(2662,0), c(3057,0,3254,0,3466,67), c(3698,151,3881,334,3965,566), c(4032,735,4032,860,4032,896), close()));
    }
    static Path thumb() {
        return new Path(Shape.thumb37x24Continuous2,2368,1536,List.of(
            m(2368,768),l(2368,768),
            c(2368,799,2368,906,2310,1051), c(2238,1250,2082,1406,1883,1478), c(1701,1536,1532,1536,1194,1536),
            l(1174,1536), c(836,1536,667,1536,485,1478), c(286,1406,130,1250,58,1051), c(0,906,0,799,0,768),
            l(0,768), c(0,737,0,630,58,485), c(130,286,286,130,485,58), c(667,0,836,0,1174,0),
            l(1194,0), c(1532,0,1701,0,1883,58), c(2082,130,2238,286,2310,485), c(2368,630,2368,737,2368,768), close()));
    }
    static Point thumbOrigin(boolean checked, Direction direction) {
        admit(direction != null, Error.extent);
        return p(checked != (direction == Direction.rightToLeft) ? 1536 : 128,128);
    }
    static int measuredExtent64(double value) {
        admit(Double.isFinite(value) && value >= 0 && value <= (double)MAXIMUM_EXTENT64 / 64, Error.extent);
        return (int)Math.ceil(value * 64);
    }
    static int spacing64(double value) {
        admit(Double.isFinite(value) && value >= 0 && value <= 256, Error.spacing);
        return nearest(value * 64);
    }
    static int normalizeDensity(double value) {
        admit(Double.isFinite(value) && value >= 0.125 && value <= 16, Error.density);
        return nearest(value * 1024);
    }
    private static int nearest(double value) {
        double floor = Math.floor(value);
        return (int)(floor + (value - floor >= 0.5 ? 1 : 0));
    }
    static int pixelEdge(long coordinate64, int density1024) {
        coordinate(coordinate64,density1024);
        return (int)((coordinate64 * density1024 + 32768L) / 65536L);
    }
    static double pixelCoordinate(long coordinate64, int density1024) {
        coordinate(coordinate64,density1024);
        return (double)(coordinate64 * density1024) / 65536;
    }
    private static void coordinate(long coordinate64, int density1024) {
        extent(coordinate64); admit(density1024 >= 128 && density1024 <= 16384, Error.density);
    }
    private static void extent(long value) { admit(value >= 0 && value <= MAXIMUM_EXTENT64, Error.extent); }
    private static void admit(boolean value, Error error) { if (!value) throw new Failure(error); }
    private static Point p(int x, int y) { return new Point(x,y); }
    private static Command m(int x, int y) { return new Command(Op.move,List.of(p(x,y))); }
    private static Command l(int x, int y) { return new Command(Op.line,List.of(p(x,y))); }
    private static Command c(int x1, int y1, int x2, int y2, int x3, int y3) { return new Command(Op.cubic,List.of(p(x1,y1),p(x2,y2),p(x3,y3))); }
    private static Command close() { return new Command(Op.close,List.of()); }
}
