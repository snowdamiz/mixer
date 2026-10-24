package dev.mixer.android;

import android.app.Instrumentation;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PathIterator;
import android.graphics.PathMeasure;
import android.graphics.RectF;
import android.os.Bundle;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;

/** Standalone API34+ native tests; never compiled into the application renderer. */
public final class AppearanceNativePathsV2Instrumentation extends Instrumentation {
    private int checks;
    private int paths;
    private int nativeVerbs;

    @Override public void onCreate(Bundle arguments) { super.onCreate(arguments); start(); }

    private void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
        checks++;
    }

    private void equal(float actual, float expected, String message) {
        check(Float.floatToIntBits(actual) == Float.floatToIntBits(expected),
            message + ": " + actual + " != " + expected);
    }

    private static float expected(int value64, int density1024) {
        return (float) (((long) value64 * density1024) / 65536.0);
    }

    private void point(float[] nativePoints, int offset, AppearanceGeometryV2.Point point,
                       int density1024, String message) {
        equal(nativePoints[offset], expected(point.x64(), density1024), message + " x");
        equal(nativePoints[offset + 1], expected(point.y64(), density1024), message + " y");
    }

    private void inspect(AppearanceGeometryV2.Path source, int density1024) {
        Path nativePath = AppearanceNativePathsV2.make(source, density1024);
        check(nativePath.getFillType() == Path.FillType.WINDING, "nonzero fill");
        check(nativePath.isEmpty() == source.commands.isEmpty(), "empty iff zero-area geometry");
        PathIterator iterator = nativePath.getPathIterator();
        float[] points = new float[8];
        AppearanceGeometryV2.Point previous = null;
        int count = 0;
        for (var command : source.commands) {
            check(iterator.hasNext(), "native verb present");
            int verb = iterator.next(points, 0);
            int expectedVerb = switch (command.op()) {
                case move -> PathIterator.VERB_MOVE;
                case line -> PathIterator.VERB_LINE;
                case cubic -> PathIterator.VERB_CUBIC;
                case close -> PathIterator.VERB_CLOSE;
            };
            check(verb == expectedVerb, "closed operation " + command.op() + " got native " + verb);
            if (command.op() == AppearanceGeometryV2.Op.move) {
                point(points, 0, command.points().get(0), density1024, "move endpoint");
                previous = command.points().get(0);
            } else if (command.op() == AppearanceGeometryV2.Op.line) {
                point(points, 0, previous, density1024, "line start");
                point(points, 2, command.points().get(0), density1024, "line endpoint");
                previous = command.points().get(0);
            } else if (command.op() == AppearanceGeometryV2.Op.cubic) {
                point(points, 0, previous, density1024, "cubic start");
                for (int index = 0; index < 3; index++)
                    point(points, 2 + index * 2, command.points().get(index), density1024,
                        "cubic control/endpoint " + index);
                previous = command.points().get(2);
            }
            count++;
        }
        check(!iterator.hasNext(), "no injected shape/contour/verb");
        check(iterator.next(points, 0) == PathIterator.VERB_DONE, "native iterator done");
        if (!source.commands.isEmpty()) {
            check(count == 18, "complete closed 18-command recipe");
            PathMeasure measure = new PathMeasure(nativePath, false);
            check(measure.isClosed(), "native contour closed without forceClosed");
            check(Float.isFinite(measure.getLength()) && measure.getLength() > 0, "native finite perimeter");
            check(!measure.nextContour(), "one native contour");
        }
        paths++;
        nativeVerbs += count;
    }

    private void nativeControlCorpus() {
        AppearanceGeometryV2.Path[] corpus = {
            AppearanceGeometryV2.track(), AppearanceGeometryV2.thumb(),
            AppearanceGeometryV2.group(320 * 64, 59 * 64, 26 * 64),
            AppearanceGeometryV2.group(7 * 64, 5 * 64, 26 * 64),
            AppearanceGeometryV2.group(1001, 1003, 65),
            AppearanceGeometryV2.group(64, 128, 0),
            AppearanceGeometryV2.group(2147483647L, 2147483647L, 65536),
            AppearanceGeometryV2.group(0, 128, 64), AppearanceGeometryV2.group(64, 0, 64)
        };
        for (int density : new int[] {128, 1024, 1536, 2731, 16384})
            for (var source : corpus) inspect(source, density);

        // Literal controls exercise fractional native pixels independently of the formula corpus.
        PathIterator iterator = AppearanceNativePathsV2.make(AppearanceGeometryV2.track(), 1536)
            .getPathIterator();
        float[] points = new float[8];
        iterator.next(points, 0); iterator.next(points, 0);
        check(iterator.next(points, 0) == PathIterator.VERB_CUBIC, "literal first track cubic");
        equal(points[2], 94.5f, "literal control x");
        equal(points[3], 21.84375f, "fractional control y");
        equal(points[5], 24.7734375f, "fractional second control y");
        equal(points[6], 92.9296875f, "fractional endpoint x");
        equal(points[7], 28.734375f, "fractional endpoint y");
    }

    private void admissionAndOwnership() {
        for (int invalid : new int[] {Integer.MIN_VALUE, -1, 0, 127, 16385, Integer.MAX_VALUE}) {
            for (var source : new AppearanceGeometryV2.Path[] {
                AppearanceGeometryV2.track(), AppearanceGeometryV2.group(0, 64, 0)}) {
                try {
                    AppearanceNativePathsV2.make(source, invalid);
                    throw new AssertionError("invalid normalized density accepted");
                } catch (AppearanceGeometryV2.Failure failure) {
                    check(failure.code == AppearanceGeometryV2.Error.density, "exact density failure");
                }
            }
        }
        try {
            AppearanceNativePathsV2.make(null, 1024);
            throw new AssertionError("null geometry accepted");
        } catch (IllegalArgumentException expectedFailure) { checks++; }

        var source = AppearanceGeometryV2.track();
        Path first = AppearanceNativePathsV2.make(source, 1024);
        Path second = AppearanceNativePathsV2.make(source, 1024);
        check(first != second, "fresh native identity");
        first.reset(); first.setFillType(Path.FillType.INVERSE_EVEN_ODD);
        check(!second.isEmpty(), "reset cannot mutate another result");
        check(second.getFillType() == Path.FillType.WINDING, "fill mutation isolated");
        Path third = AppearanceNativePathsV2.make(source, 1024);
        RectF before = new RectF(); third.computeBounds(before);
        second.offset(500, 600);
        RectF after = new RectF(); third.computeBounds(after);
        check(before.equals(after), "offset cannot mutate another result");
        equal(after.left, 0, "local left origin"); equal(after.top, 0, "local top origin");
        equal(after.right, 63, "local pixel width"); equal(after.bottom, 28, "local pixel height");
        check(source.commands.size() == 18, "immutable source preserved");
    }

    private Bitmap bitmap() { return Bitmap.createBitmap(120, 85, Bitmap.Config.ARGB_8888); }

    private void drawAndClip() throws IOException {
        Path path = AppearanceNativePathsV2.make(AppearanceGeometryV2.track(), 1024);
        Bitmap fill = bitmap();
        Canvas canvas = new Canvas(fill);
        canvas.translate(11, 13);
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setColor(Color.WHITE); paint.setStyle(Paint.Style.FILL);
        canvas.drawPath(path, paint);
        check(fill.getPixel(42, 27) == Color.WHITE, "native path fill contains center");
        check(Color.alpha(fill.getPixel(11, 13)) == 0, "authored curved corner excludes local origin");
        check(Color.alpha(fill.getPixel(10, 27)) == 0, "caller translation leaves exterior clear");
        check(Color.alpha(fill.getPixel(75, 27)) == 0, "one density transform has exact extent");

        Bitmap clip = bitmap();
        Canvas clipped = new Canvas(clip);
        clipped.translate(11, 13);
        check(clipped.clipPath(path), "native path is a nonempty clip");
        clipped.drawColor(Color.WHITE);
        check(clip.getPixel(42, 27) == Color.WHITE, "native path clips fill at center");
        check(Color.alpha(clip.getPixel(11, 13)) == 0, "native clip excludes curved corner");
        check(Color.alpha(clip.getPixel(5, 5)) == 0, "native clip excludes exterior");

        Bitmap rectangle = bitmap();
        Canvas rectangleCanvas = new Canvas(rectangle);
        rectangleCanvas.translate(11, 13);
        rectangleCanvas.drawPath(AppearanceNativePathsV2.make(AppearanceGeometryV2.group(64 * 20, 64 * 10, 0), 1024), paint);
        check(rectangle.getPixel(11, 13) == Color.WHITE, "zero-radius group fills corner");
        check(Color.alpha(rectangle.getPixel(31, 18)) == 0, "zero-radius group remains in extent");

        RectF retained = new RectF(); path.computeBounds(retained);
        check(retained.equals(new RectF(0, 0, 63, 28)), "draw and clip preserve returned path");
        try (var output = new FileOutputStream(new File(getTargetContext().getFilesDir(), "native-path-fill.png"))) {
            check(fill.compress(Bitmap.CompressFormat.PNG, 100, output), "retained native raster fixture");
        }
        fill.recycle(); clip.recycle(); rectangle.recycle();
    }

    @Override public void onStart() {
        Bundle result = new Bundle();
        try {
            nativeControlCorpus(); admissionAndOwnership(); drawAndClip();
            result.putString("status", "passed");
            result.putInt("checks", checks); result.putInt("native_paths", paths);
            result.putInt("native_verbs", nativeVerbs);
            result.putString("scope", "API37 emulator native PathIterator/PathMeasure and software Canvas bitmap fill/clip only");
            finish(0, result);
        } catch (Throwable failure) {
            result.putString("status", "failed");
            result.putInt("checks_before_failure", checks);
            result.putString("failure", android.util.Log.getStackTraceString(failure));
            finish(1, result);
        }
    }
}
