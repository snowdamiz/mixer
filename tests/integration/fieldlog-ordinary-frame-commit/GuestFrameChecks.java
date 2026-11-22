import java.util.ArrayList;
import java.util.List;

final class GuestFrameChecks {
    private final long context = 7;
    private int frameSerial;
    private boolean closing, enabled, closeAfterOperation, awaitingReply;
    private int closeRetries, remaining, requestedCycle;
    private long teardownDeadline;
    private Runnable afterClose;
    private final Activity activity = new Activity();
    private final Dialog dialog = new Dialog();
    private final Handler handler = new Handler();
    private GuestFrame current;
    private final Button done = new Button(activity);

    GuestFrameChecks() {
        // PRODUCTION DONE WIRING
    }

    private void start(int action) { requestedCycle = action; }
    private void schedulePoll() { throw new AssertionError("Done unexpectedly resumed polling"); }
    private final List<String> witnesses = new ArrayList<>();

    private int witness(long facade, long attachment, long token, boolean display) {
        witnesses.add(facade + ":" + attachment + ":" + token + ":" + display);
        return 0;
    }

    // PRODUCTION GUEST FRAME

    private GuestFrame attach(long token) {
        if (current != null) {
            current.disarm();
            current.onDetachedFromWindow();
        }
        current = new GuestFrame(1, 2, token, token + 1);
        current.onAttachedToWindow();
        return current;
    }

    private Canvas draw(boolean hardware) {
        var canvas = new Canvas(hardware);
        current.observer.preDraw();
        current.dispatchDraw(canvas);
        // Deliver both ordinary animation callbacks without committing a buffer.
        for (int i = 0; i < 2; i++) current.stepAnimation();
        return canvas;
    }

    private static void expect(boolean condition, String detail) {
        if (!condition) throw new AssertionError(detail);
    }

    public static void main(String[] args) {
        GuestFrameChecks check = new GuestFrameChecks();
        GuestFrame original = check.attach(10);
        check.draw(true);
        expect(check.witnesses.isEmpty(), "draw without a committed buffer called the display witness");
        if (Boolean.getBoolean("noBuffer")) return;

        Runnable lateCommit = original.observer.takeCommit();
        check.handler.expire();
        lateCommit.run();
        expect(!PixelCopy.pending(), "expired commit requested readback");

        Canvas exact = check.draw(true);
        original.observer.takeCommit().run();
        expect(check.witnesses.isEmpty(), "commit callback alone called the display witness");
        PixelCopy.finish(PixelCopy.SUCCESS, exact);
        expect(check.witnesses.equals(List.of("1:2:11:true")), "same traversal was not witnessed exactly once");
        expect(!original.action.enabled, "native enable fence was bypassed");
        expect(!check.enableGuest(99, true) && !original.action.enabled, "wrong facade enabled the action");
        expect(check.enableGuest(1, true) && original.action.enabled, "current facade could not enable the action");
        original.action.click();
        expect(check.witnesses.equals(List.of("1:2:11:true", "1:2:10:false")), "action tuple or dispatch changed");
        expect(!original.action.enabled, "accepted action remained enabled");

        Canvas clean = check.draw(true);
        expect(clean.colors.isEmpty() && !PixelCopy.pending() && check.handler.timers.isEmpty()
            && original.observer.commits.isEmpty() && original.observer.listeners.isEmpty(), "idle frame retained marker or witness work");

        GuestFrame next = check.attach(20);
        check.draw(true);
        next.observer.takeCommit().run();
        PixelCopy.finish(PixelCopy.SUCCESS, exact);
        expect(check.witnesses.size() == 2, "previous frame pixels were accepted");

        Canvas uncommitted = check.draw(true);
        next.observer.takeCommit().run();
        PixelCopy.finish(1, uncommitted);
        expect(check.witnesses.size() == 2, "PixelCopy error was accepted");

        Canvas old = check.draw(true);
        next.observer.takeCommit().run();
        GuestFrame replacement = check.attach(30);
        PixelCopy.finish(PixelCopy.SUCCESS, old);
        expect(check.witnesses.size() == 2 && check.handler.timers.isEmpty(), "refresh accepted a late old sample");
        expect(next.observer.listeners.isEmpty() && !next.action.enabled, "refresh retained a listener or action");
        expect(PixelCopy.recycles == 4, "readback bitmap was not released");

        Canvas retiring = check.draw(true);
        replacement.observer.takeCommit().run();
        check.done.setEnabled(true);
        check.done.click();
        expect(check.requestedCycle == 2 && check.afterClose != null && check.closeRetries == 1,
            "Done did not start the existing native retirement cycle");
        PixelCopy.finish(PixelCopy.SUCCESS, retiring);
        expect(check.witnesses.size() == 2 && check.handler.timers.isEmpty(), "retirement accepted pending readback");
        expect(replacement.observer.listeners.isEmpty(), "retirement retained pre-draw listener");

        check.closeAfterOperation = false;
        GuestFrame focused = check.attach(40);
        check.draw(true);
        Runnable beforeFocusLoss = focused.observer.takeCommit();
        focused.focused = false;
        focused.onWindowFocusChanged(false);
        beforeFocusLoss.run();
        expect(!PixelCopy.pending() && check.handler.timers.isEmpty(), "focus loss retained frame authority");
        focused.focused = true;
        focused.onWindowFocusChanged(true);
        Canvas resumed = check.draw(true);
        focused.observer.takeCommit().run();
        PixelCopy.finish(PixelCopy.SUCCESS, resumed);
        expect(check.witnesses.get(check.witnesses.size() - 1).equals("1:2:41:true"), "focus regain did not witness its exact frame");

        GuestFrame paused = check.attach(45);
        Canvas beforePause = check.draw(true);
        paused.observer.takeCommit().run();
        check.activity.resumed = false;
        check.foregroundChanged();
        check.activity.resumed = true;
        check.foregroundChanged();
        PixelCopy.finish(PixelCopy.SUCCESS, beforePause);
        expect(check.witnesses.size() == 3 && check.handler.timers.isEmpty(),
            "pause and resume revived an old readback");

        GuestFrame moved = check.attach(48);
        Canvas beforeMovement = check.draw(true);
        moved.observer.takeCommit().run();
        moved.windowLeft++;
        PixelCopy.finish(PixelCopy.SUCCESS, beforeMovement);
        expect(check.witnesses.size() == 3, "moved guest accepted old sample coordinates");

        GuestFrame ownerChanged = check.attach(49);
        Canvas oldOwner = check.draw(true);
        ownerChanged.observer.takeCommit().run();
        check.activity.context++;
        PixelCopy.finish(PixelCopy.SUCCESS, oldOwner);
        expect(check.witnesses.size() == 3, "changed owner accepted an old sample");
        check.activity.context--;

        GuestFrame partial = check.attach(49);
        partial.observer.preDraw();
        partial.observer.takeCommit().run();
        expect(!PixelCopy.pending(), "commit callback with no hardware draw requested readback");
        Canvas oneWrongPixel = check.draw(true);
        partial.observer.takeCommit().run();
        oneWrongPixel.colors.set(1, oneWrongPixel.colors.get(0));
        PixelCopy.finish(PixelCopy.SUCCESS, oneWrongPixel);
        expect(check.witnesses.size() == 3, "one matching marker color was accepted");

        GuestFrame limited = check.attach(50);
        for (int i = 0; i < 4; i++) {
            check.draw(true);
            limited.observer.takeCommit();
            check.handler.expire();
        }
        expect(check.draw(true).colors.isEmpty() && limited.observer.commits.isEmpty()
            && check.handler.timers.isEmpty(), "missing commit left unbounded retries");

        Build.VERSION.SDK_INT = 28;
        GuestFrame older = check.attach(60);
        expect(check.draw(true).colors.isEmpty() && older.observer.commits.isEmpty() && check.handler.timers.isEmpty(),
            "SDK 28 entered the hardware witness path");
        Build.VERSION.SDK_INT = 29;
        GuestFrame software = check.attach(70);
        software.hardware = false;
        expect(check.draw(false).colors.isEmpty() && software.observer.commits.isEmpty(),
            "software renderer entered the hardware witness path");
        GuestFrame earlier = check.attach(80);
        Canvas on29 = check.draw(true);
        earlier.observer.takeCommit().run();
        PixelCopy.finish(PixelCopy.SUCCESS, on29);
        expect(check.witnesses.get(check.witnesses.size() - 1).equals("1:2:81:true"), "SDK 29 hardware proof failed");
        System.out.println("PASS ordinary GuestFrame display, action, refresh, retirement, focus, bounded idle and API controls");
    }

    static final class android {
        static final class util {
            static final class Log { static void w(String tag, String message) {} }
        }
    }
    static final class Build {
        static final class VERSION { static int SDK_INT = 36; }
        static final class VERSION_CODES { static final int Q = 29; }
    }
    static final class Activity {
        long context = 7;
        boolean destroyed, failed;
        boolean resumed = true;
        boolean isFinishing() { return false; }
    }
    static final class Dialog {
        Object getWindow() { return this; }
        void dismiss() {}
    }
    static final class SystemClock { static long elapsedRealtime() { return 0; } }
    static final class Handler {
        final List<Runnable> timers = new ArrayList<>();
        boolean postDelayed(Runnable task, long delay) { return timers.add(task); }
        void removeCallbacks(Runnable task) { timers.remove(task); }
        void expire() { List.copyOf(timers).forEach(Runnable::run); }
    }
    static class View {
        static final int VISIBLE = 0;
        boolean focused = true, hardware = true;
        int windowLeft = 13;
        final ViewTreeObserver observer = new ViewTreeObserver();
        private final List<Runnable> animation = new ArrayList<>();
        int getWidth() { return 200; }
        int getHeight() { return 80; }
        void getLocationInWindow(int[] xy) { xy[0] = windowLeft; xy[1] = 19; }
        ViewTreeObserver getViewTreeObserver() { return observer; }
        boolean isAttachedToWindow() { return true; }
        boolean isShown() { return true; }
        boolean hasWindowFocus() { return focused; }
        boolean isHardwareAccelerated() { return hardware; }
        int getWindowVisibility() { return VISIBLE; }
        boolean getGlobalVisibleRect(Rect rect) { return getLocalVisibleRect(rect); }
        boolean getLocalVisibleRect(Rect rect) { rect.right = getWidth(); rect.bottom = getHeight(); return true; }
        void postOnAnimation(Runnable task) { animation.add(task); }
        void invalidate() {}
        void removeCallbacks(Runnable task) { animation.remove(task); }
        void stepAnimation() {
            List<Runnable> ready = List.copyOf(animation);
            animation.clear();
            ready.forEach(Runnable::run);
        }
        protected void onAttachedToWindow() {}
        protected void onDetachedFromWindow() {}
        public void onWindowFocusChanged(boolean hasFocus) {}
    }
    static class LinearLayout extends View {
        static final int VERTICAL = 1;
        LinearLayout(Activity activity) {}
        void setOrientation(int direction) {}
        protected void dispatchDraw(Canvas canvas) {}
    }
    static final class Button extends View {
        java.util.function.Consumer<View> click;
        boolean enabled;
        Button(Activity activity) {}
        void setAllCaps(boolean enabled) {}
        void setEnabled(boolean value) { enabled = value; }
        void setOnClickListener(java.util.function.Consumer<View> listener) { click = listener; }
        void click() { if (enabled && click != null) click.accept(this); }
    }
    static final class ViewTreeObserver {
        interface OnPreDrawListener { boolean onPreDraw(); }
        final List<OnPreDrawListener> listeners = new ArrayList<>();
        final List<Runnable> commits = new ArrayList<>();
        boolean isAlive() { return true; }
        void addOnPreDrawListener(OnPreDrawListener listener) { listeners.add(listener); }
        void removeOnPreDrawListener(OnPreDrawListener listener) { listeners.remove(listener); }
        void registerFrameCommitCallback(Runnable callback) { commits.add(callback); }
        boolean unregisterFrameCommitCallback(Runnable callback) { return commits.remove(callback); }
        void preDraw() { List.copyOf(listeners).forEach(OnPreDrawListener::onPreDraw); }
        Runnable takeCommit() { return commits.remove(0); }
    }
    static final class Rect {
        int left, top, right, bottom;
        Rect() {}
        Rect(Rect rect) { this(rect.left, rect.top, rect.right, rect.bottom); }
        Rect(int left, int top, int right, int bottom) {
            this.left = left; this.top = top; this.right = right; this.bottom = bottom;
        }
        int width() { return right - left; }
        int height() { return bottom - top; }
        boolean contains(Rect rect) {
            return left <= rect.left && top <= rect.top && right >= rect.right && bottom >= rect.bottom;
        }
        void offset(int x, int y) { left += x; right += x; top += y; bottom += y; }
        @Override public boolean equals(Object other) {
            return other instanceof Rect r && left == r.left && top == r.top && right == r.right && bottom == r.bottom;
        }
        @Override public int hashCode() { return java.util.Objects.hash(left, top, right, bottom); }
    }
    static final class Paint {
        int color;
        void setColor(int color) { this.color = color; }
    }
    static final class Canvas {
        final List<Integer> colors = new ArrayList<>();
        private final boolean hardware;
        Canvas(boolean hardware) { this.hardware = hardware; }
        boolean isHardwareAccelerated() { return hardware; }
        void drawRect(float left, float top, float right, float bottom, Paint paint) { colors.add(paint.color); }
    }
    static final class Bitmap {
        enum Config { ARGB_8888 }
        List<Integer> pixels;
        boolean recycled;
        static Bitmap createBitmap(int width, int height, Config config) { return new Bitmap(); }
        int getPixel(int x, int y) {
            expect(!recycled, "read recycled bitmap");
            return pixels.size() == 2 ? pixels.get(x < 4 ? 0 : 1) : 0;
        }
        void recycle() {
            expect(!recycled, "duplicate bitmap release");
            recycled = true;
            PixelCopy.recycles++;
        }
    }
    static final class PixelCopy {
        static final int SUCCESS = 0;
        static int recycles;
        private record Copy(Bitmap bitmap, java.util.function.IntConsumer listener) {}
        private static Copy copy;
        static void request(Object window, Rect region, Bitmap bitmap, java.util.function.IntConsumer listener, Handler handler) {
            expect(!pending() && region.width() == 8 && region.height() == 4, "readback bounds or concurrency changed");
            copy = new Copy(bitmap, listener);
        }
        static boolean pending() { return copy != null; }
        static void finish(int result, Canvas buffer) {
            Copy finished = copy;
            copy = null;
            finished.bitmap.pixels = buffer.colors;
            finished.listener.accept(result);
        }
    }
}
