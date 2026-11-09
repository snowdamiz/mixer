package dev.mixer.android;

/** Host arithmetic controls against the actual fixed product conversion. */
public final class MeasurementCapacityControl {
    private static long cases;
    private static long oldOverflowCases;
    private MeasurementCapacityControl() {}

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    private static long measured(int pixels, int density) {
        return AppearanceGeometryV2.measuredExtent64(pixels * 1024.0 / density);
    }
    private static void check(long budget, int density) {
        int capacity = AppearanceGeometryV2.measurementCapacity(budget, density);
        long exact = budget * density / 65536L;
        require(capacity == exact, "capacity differs from exact rational floor");
        long converted = measured(capacity, density);
        long exactConverted = ((long) capacity * 65536 + density - 1) / density;
        require(converted == exactConverted, "measuredExtent64 differs from exact rational ceil");
        require(converted <= budget, "in-budget native width rejected");
        long next = ((long) (capacity + 1) * 65536 + density - 1) / density;
        require(next > budget, "floor discarded a permissible whole pixel");
        int placed = AppearanceGeometryV2.pixelEdge(budget, density);
        require(placed == (budget * density + 32768L) / 65536L,
            "pixel placement rounding changed");
        if (placed > capacity) oldOverflowCases++;
        cases++;
    }
    private static void rejected(long budget, int density, AppearanceGeometryV2.Error expected) {
        try {
            AppearanceGeometryV2.measurementCapacity(budget, density);
            throw new AssertionError("invalid input accepted");
        } catch (AppearanceGeometryV2.Failure failure) {
            require(failure.code == expected, "wrong boundary failure");
        }
    }
    public static void main(String[] args) {
        require(AppearanceGeometryV2.pixelEdge(63, 3072) == 3, "old reproducer changed");
        require(measured(3, 3072) == 64, "mandatory ceil changed");
        require(measured(3, 3072) > 63, "old overflow not reproduced");
        require(AppearanceGeometryV2.measurementCapacity(63, 3072) == 2, "fix missed reproducer");
        require(measured(2, 3072) == 43, "fixed reproducer changed");
        System.out.println("old: budget64=63 density1024=3072 maximumPx=3 measured64=64 -> overflow");
        System.out.println("fixed: budget64=63 density1024=3072 maximumPx=2 measured64=43 -> admitted");
        long[] budgets = {0, 1, 2, 31, 32, 63, 64, 65, 127, 128, 129,
            511, 512, 513, 2047, 2048, 2049, 16383, 16384, 16385,
            24575, 24576, 24577, 65535, 65536, 65537,
            2147483646L, 2147483647L};
        for (int density = 128; density <= 16384; density++) {
            for (long budget : budgets) check(budget, density);
            // Native root width from R13; these are synthetic inset controls, not observed row values.
            long root = measured(1080, density);
            for (long inset : new long[] {0, 1, 64, 1024, 2048, 4096}) {
                if (root >= inset) check(root - inset, density);
            }
        }
        for (int density : new int[] {128, 1024, 1536, 2048, 2688, 2816, 3072, 16384}) {
            for (long budget = 0; budget <= 65536; budget++) check(budget, density);
        }
        rejected(-1, 1024, AppearanceGeometryV2.Error.extent);
        rejected(2147483648L, 1024, AppearanceGeometryV2.Error.extent);
        rejected(64, 127, AppearanceGeometryV2.Error.density);
        rejected(64, 16385, AppearanceGeometryV2.Error.density);
        require(AppearanceGeometryV2.measurementCapacity(1, 128) == 0,
            "subpixel budget was expanded instead of preserving caller refusal");
        require(oldOverflowCases > 0, "old rounding premise not exercised");
        System.out.println("PASS actual-product capacity controls=" + cases
            + " old-nearest-overbudget-cases=" + oldOverflowCases
            + " invalid-input-refusals=4");
        System.out.println("SCOPE arithmetic only; Android TextView shaping/minimum-hit/runtime execution pending root");
    }
}
