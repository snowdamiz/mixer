package dev.mixer.android;

import android.app.Activity;
import android.app.UiModeManager;
import android.content.ComponentCallbacks;
import android.content.Context;
import android.content.res.Configuration;
import android.database.ContentObserver;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Rect;
import android.os.Handler;
import android.os.Looper;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewTreeObserver;
import android.view.WindowInsets;
import android.view.accessibility.AccessibilityManager;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.CompletionInfo;
import android.view.inputmethod.CorrectionInfo;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.HandwritingGesture;
import android.view.inputmethod.InputConnection;
import android.view.inputmethod.InputConnectionWrapper;
import android.view.inputmethod.InputContentInfo;
import android.view.inputmethod.PreviewableHandwritingGesture;
import android.view.inputmethod.TextAttribute;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.Switch;
import java.lang.reflect.RecordComponent;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Leaf-only controls. No actual product class is compiled or executed. */
public final class IndependentLeafSanity {
    private IndependentLeafSanity() {}
    private static int assertions, controls;
    private static final List<String> passed = new ArrayList<>();
    private static void check(boolean condition, String message) {
        assertions++;
        if (!condition) throw new AssertionError(message);
    }
    private static void done(String name) { controls++; passed.add(name); ConcreteHostProbe.reset(); }
    private static void expect(Throwable expected, Runnable action) {
        try { action.run(); throw new AssertionError("expected identity throw"); }
        catch (RuntimeException | Error actual) { check(actual == expected, "exact failure identity"); }
    }

    private static void probeCallbacks() {
        Paint paint = new Paint();
        List<String> phases = new ArrayList<>();
        ConcreteHostProbe.hook = (method, phase) -> {
            if (method.equals("Paint.setColor")) {
                phases.add(phase);
                check(ConcreteHostProbe.lastEvent().receiver == paint, "receiver identity");
                check(phase.equals("entry") ? paint.color == 0 : paint.color == 19, "entry versus return mutation");
            }
        };
        paint.setColor(19);
        check(phases.equals(List.of("entry", "beforeReturn")), "two callback positions");
        List<ConcreteHostProbe.Event> copy = ConcreteHostProbe.events();
        try { copy.clear(); throw new AssertionError("event copy mutable"); }
        catch (UnsupportedOperationException expected) { check(true, "event snapshot read-only"); }
        RuntimeException ordinary = new IllegalStateException("independent leaf ordinary");
        ConcreteHostProbe.hook = (method, phase) -> { if (phase.equals("entry")) throw ordinary; };
        expect(ordinary, () -> paint.setColor(20));
        check(paint.color == 19, "entry throw precedes mutation");
        ConcreteHostProbe.hook = (method, phase) -> { if (phase.equals("beforeReturn")) throw ordinary; };
        expect(ordinary, () -> paint.setColor(21));
        check(paint.color == 21, "return throw follows mutation");
        done("probe-entry-return-and-fault-position");
    }

    private static void probeBounds() {
        for (int i = 0; i < ConcreteHostProbe.LIMIT; i++) ConcreteHostProbe.hit("independent-bound");
        try { ConcreteHostProbe.hit("independent-bound"); throw new AssertionError("event bound absent"); }
        catch (IllegalStateException expected) { check(ConcreteHostProbe.events().size() == 65536, "fixed event limit"); }
        ConcreteHostProbe.reset();
        for (int i = 0; i < 4096; i++) ConcreteHostProbe.hit("independent-key-" + i);
        try { ConcreteHostProbe.hit("independent-key-overflow"); throw new AssertionError("key bound absent"); }
        catch (IllegalStateException expected) {
            check(ConcreteHostProbe.events().size() == 4097, "overflow event retained before key rejection");
            check(ConcreteHostProbe.count("independent-key-overflow", "entry") == 0, "new key not admitted");
        }
        done("probe-event-and-method-bounds");
    }

    private static void handlerShape() {
        Handler handler = new Handler(Looper.getMainLooper());
        int[] calls = {0}; Runnable first = () -> calls[0]++;
        check(handler.post(first), "post accepted");
        check(calls[0] == 0 && handler.queued() == 1, "post never inline");
        Runnable retained = handler.snapshot().get(0);
        handler.removeEffective = false; handler.removeCallbacks(first);
        check(handler.queued() == 1, "ineffective removal represented");
        handler.removeEffective = true; handler.removeCallbacks(first);
        check(handler.queued() == 0, "exact queued identity removal");
        retained.run(); check(calls[0] == 1, "retained stale delivery independently possible");
        handler.postResult = false; check(!handler.post(first) && handler.queued() == 0, "false post no enqueue");
        RuntimeException post = new IllegalStateException("post"); handler.postFailure = post;
        expect(post, () -> handler.post(first)); check(handler.queued() == 0, "throwing post no enqueue");
        handler.postFailure = null; handler.postResult = true; handler.post(first);
        Error remove = new AssertionError("remove"); handler.removeFailure = remove;
        expect(remove, () -> handler.removeCallbacks(first)); check(handler.queued() == 1, "throwing removal keeps work");
        handler.removeFailure = null; check(handler.drainAll(1) == 1 && calls[0] == 2, "explicit bounded delivery");
        done("handler-noninline-false-throw-and-stale-identity");
    }

    private static void registrationShape() {
        Activity activity = new Activity(); FrameLayout root = new FrameLayout(activity);
        UiModeManager modes = activity.getSystemService(UiModeManager.class);
        AccessibilityManager access = activity.getSystemService(AccessibilityManager.class);
        int[] notices = new int[8];
        ComponentCallbacks configuration = new ComponentCallbacks() {
            public void onConfigurationChanged(Configuration value) { notices[0]++; }
            public void onLowMemory() {}
        };
        View.OnLayoutChangeListener layout = (view,l,t,r,b,ol,ot,or,ob) -> notices[1]++;
        View.OnAttachStateChangeListener attachment = new View.OnAttachStateChangeListener() {
            public void onViewAttachedToWindow(View view) { notices[2]++; }
            public void onViewDetachedFromWindow(View view) { notices[2]++; }
        };
        ViewTreeObserver.OnWindowFocusChangeListener focus = value -> notices[3]++;
        View.OnApplyWindowInsetsListener insets = (view,value) -> { notices[4]++; return value; };
        UiModeManager.ContrastChangeListener contrast = value -> notices[5]++;
        AccessibilityManager.HighContrastTextStateChangeListener high = value -> notices[6]++;
        ContentObserver motion = new ContentObserver(new Handler()) { public void onChange(boolean value) { notices[7]++; } };
        activity.registerComponentCallbacks(configuration); root.addOnLayoutChangeListener(layout);
        root.addOnAttachStateChangeListener(attachment); root.getViewTreeObserver().addOnWindowFocusChangeListener(focus);
        root.setOnApplyWindowInsetsListener(insets); modes.addContrastChangeListener(activity.getMainExecutor(),contrast);
        access.addHighContrastTextStateChangeListener(activity.getMainExecutor(),high);
        activity.getContentResolver().registerContentObserver(android.net.Uri.parse("content://independent"),false,motion);
        activity.hostConfigurationChanged(); root.layout(0,0,100,100); root.hostAttach(new Object());
        root.hostWindowFocus(false); root.hostInsets(new WindowInsets()); modes.hostContrast(.5f);
        access.hostHighContrast(true); activity.getContentResolver().hostNotify();
        for (int i=0;i<8;i++) check(notices[i] == 1, "synchronous platform notice slot " + i);
        activity.unregisterComponentCallbacks(configuration); root.removeOnLayoutChangeListener(layout);
        root.removeOnAttachStateChangeListener(attachment); root.getViewTreeObserver().removeOnWindowFocusChangeListener(focus);
        root.setOnApplyWindowInsetsListener(null); modes.removeContrastChangeListener(contrast);
        access.removeHighContrastTextStateChangeListener(high); activity.getContentResolver().unregisterContentObserver(motion);
        check(activity.componentCallbacks.isEmpty() && root.layoutListeners.isEmpty() && root.attachListeners.isEmpty(), "exact listener release");
        check(root.treeObserver.listeners.isEmpty() && root.insetsListener == null && modes.listeners.isEmpty() && access.listeners.isEmpty() && activity.resolver.observers.isEmpty(), "all eight mechanical slots removable");
        RuntimeException afterAdd = new IllegalStateException("after add");
        ConcreteHostProbe.hook = (method,phase) -> { if (method.equals("View.addOnLayoutChangeListener") && phase.equals("beforeReturn")) throw afterAdd; };
        expect(afterAdd, () -> root.addOnLayoutChangeListener(layout));
        check(root.layoutListeners.size() == 1, "add-then-throw preserves uncertain acquisition");
        ConcreteHostProbe.reset(); root.removeOnLayoutChangeListener(layout);
        done("eight-registration-notice-shapes-and-add-then-throw");
    }

    @SuppressWarnings("this-escape")
    private static final class Early extends Switch {
        private boolean assigned;
        static final int[] counts = new int[11];
        Early(Context context) { super(context); assigned = true; }
        private void mark(int i) { if (!assigned) counts[i]++; }
        @Override public void setEnabled(boolean value) { mark(0); super.setEnabled(value); }
        @Override protected boolean setFrame(int l,int t,int r,int b) { mark(1); return super.setFrame(l,t,r,b); }
        @Override protected void drawableStateChanged() { mark(2); super.drawableStateChanged(); }
        @Override protected void onSelectionChanged(int s,int e) { mark(3); super.onSelectionChanged(s,e); }
        @Override protected void onAttachedToWindow() { mark(4); super.onAttachedToWindow(); }
        @Override protected void onDetachedFromWindow() { mark(5); super.onDetachedFromWindow(); }
        @Override protected void onFocusChanged(boolean value,int direction,Rect old) { mark(6); super.onFocusChanged(value,direction,old); }
        @Override public void onWindowFocusChanged(boolean value) { mark(7); super.onWindowFocusChanged(value); }
        @Override protected void onVisibilityChanged(View changed,int value) { mark(8); super.onVisibilityChanged(changed,value); }
        @Override protected void onWindowVisibilityChanged(int value) { mark(9); super.onWindowVisibilityChanged(value); }
        @Override public void onRtlPropertiesChanged(int value) { mark(10); super.onRtlPropertiesChanged(value); }
    }

    private static void earlyVirtualsAndHierarchy() {
        Context context = new Context(); new Early(context);
        for (int i=0;i<11;i++) check(Early.counts[i] > 0, "deliberate early virtual entry " + i);
        FrameLayout parent = new FrameLayout(context); View child = new View(context); Object token = new Object();
        parent.hostAttach(token); parent.addView(child);
        check(child.getParent() == parent && child.isAttachedToWindow() && child.getWindowToken() == token, "mechanical parent and inherited window facts");
        parent.removeView(child); check(child.getParent() == null && !child.isAttachedToWindow(), "remove detaches child");
        parent.addView(child); parent.scrollTo(3,4); child.layout(5,7,15,17); int[] location = new int[2]; child.getLocationInWindow(location);
        check(location[0] == 2 && location[1] == 3, "simple parent-scroll coordinate accumulation");
        done("adversarial-early-virtuals-and-basic-hierarchy");
    }

    private static void assetBytes() throws Exception {
        Context context = new Context(); byte[] raw = {1,2,3};
        context.assets.put("independent",raw); raw[0] = 9;
        try (var stream = context.assets.open("independent")) { check(stream.read() == 1, "asset put copies bytes"); }
        try { context.assets.open("missing"); throw new AssertionError("missing asset accepted"); }
        catch (java.io.FileNotFoundException expected) { check(true, "missing asset IO failure"); }
        done("asset-byte-stream-no-trusted-capture");
    }

    private static void textWatcherOrder() {
        EditText field = new EditText(new Context()); field.setText("ab"); field.setSelection(1);
        List<String> order = new ArrayList<>();
        field.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence text,int start,int count,int after) { order.add("before"); }
            public void onTextChanged(CharSequence text,int start,int before,int count) { order.add("on"); }
            public void afterTextChanged(Editable text) { order.add("after"); }
        });
        InputConnection target = field.onCreateInputConnection(new EditorInfo());
        InputConnection wrapper = new InputConnectionWrapper(target,false);
        ConcreteHostProbe.hook = (method,phase) -> {
            if (phase.equals("beforeReturn") && (method.equals("BaseInputConnection.commitText") || method.equals("InputConnectionWrapper.commitText")))
                check(order.equals(List.of("before","on","after")), "watcher completed before delegate/wrapper return");
        };
        check(wrapper.commitText("X",1), "host delegate text mutation completes");
        check(field.getText().toString().equals("aXb"), "actual host buffer changed");
        check(order.equals(List.of("before","on","after")), "synchronous watcher order");
        done("actual-leaf-editable-watcher-before-delegate-return");
    }

    private static void compositionAndCodePoints() {
        EditText field = new EditText(new Context()); field.setText("a\ud83d\ude00b"); field.setSelection(3);
        BaseInputConnection connection = new BaseInputConnection(field,true);
        check(connection.deleteSurroundingTextInCodePoints(1,0), "codepoint delete call");
        check(field.getText().toString().equals("ab"), "surrogate pair deleted together in this witness");
        field.setSelection(0); check(connection.setComposingText("Z",1), "compose Z");
        check(BaseInputConnection.getComposingSpanStart(field.getText()) == 0 && BaseInputConnection.getComposingSpanEnd(field.getText()) == 1, "simple composing span");
        check(connection.setComposingText("Q",1) && field.getText().toString().equals("Qab"), "replace simple composition");
        check(connection.finishComposingText() && BaseInputConnection.getComposingSpanStart(field.getText()) == -1, "finish composition");
        done("simple-composition-and-codepoint-witness-only");
    }

    private static void forwardingSurface() {
        BaseInputConnection target = new BaseInputConnection(null,true); InputConnection w = new InputConnectionWrapper(target,false);
        TextAttribute attribute = new TextAttribute();
        w.commitText("x",1);w.setComposingText("x",1);w.commitText("x",1,attribute);w.setComposingText("x",1,attribute);
        w.setComposingRegion(0,0);w.setComposingRegion(0,0,attribute);w.finishComposingText();
        w.deleteSurroundingText(0,0);w.deleteSurroundingTextInCodePoints(0,0);w.setSelection(0,0);w.performEditorAction(6);
        w.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_UP,KeyEvent.KEYCODE_ENTER));w.replaceText(0,0,"",1,attribute);
        w.performPrivateCommand("independent",null);w.setImeConsumesInput(true);w.previewHandwritingGesture(new PreviewableHandwritingGesture(),null);
        w.commitCompletion(new CompletionInfo(1,0,"x"));w.commitCorrection(new CorrectionInfo(0,"x","y"));w.commitContent(new InputContentInfo(),0,null);
        w.beginBatchEdit();w.endBatchEdit();w.clearMetaKeyStates(0);int[] unsupported = {0};
        w.performHandwritingGesture(new HandwritingGesture(),Runnable::run,value -> { check(value == InputConnection.HANDWRITING_GESTURE_RESULT_UNSUPPORTED,"unsupported handwriting value");unsupported[0]++; });
        w.closeConnection(); check(target.mutations == 24 && target.closed && unsupported[0] == 1, "all declared wrapper forwards reach mechanical delegate");
        done("declared-24-wrapper-forwards-no-product-gating-claim");
    }

    private static void nativeBridgeShape() {
        NativeBridge.reset(); byte[] packet = "independent raw bytes".getBytes(StandardCharsets.UTF_8); byte[] input = {7};
        NativeBridge.preparedPacket = packet; NativeBridge.preparedToken = 17; NativeBridge.createResult = 23;
        check(NativeBridge.create() == 23, "supplied engine handle");
        NativeBridge.Candidate candidate = NativeBridge.prepareV2(23,1,input); byte[] first = candidate.packet(); first[0] = 0;
        check(candidate.token() == 17 && candidate.packet()[0] == 'i', "opaque JNI token and defensive packet clone");
        check(NativeBridge.lastInput == input && NativeBridge.lastPreparedPacket == packet && NativeBridge.lastOperation == 1, "single retained primitive JNI diagnostics");
        check(NativeBridge.commitV2(23,17) == 0 && NativeBridge.abortV2(23,17) == 0, "fixture statuses returned"); NativeBridge.destroy(23);
        check(NativeBridge.createCalls == 1 && NativeBridge.prepareCalls == 1 && NativeBridge.commitCalls == 1 && NativeBridge.abortCalls == 1 && NativeBridge.destroyCalls == 1, "actual leaf call counters");
        Error fatal = new AssertionError("independent JNI fatal"); NativeBridge.commitFailure = fatal;
        expect(fatal, () -> NativeBridge.commitV2(23,17)); check(NativeBridge.commitCalls == 2, "attempt counter before configured fatal");
        NativeBridge.reset(); done("JNI-raw-packet-token-counters-and-fatal-identity");
    }

    private static void motionAndGraphics() {
        MotionEvent event = new MotionEvent(MotionEvent.ACTION_POINTER_UP | (1 << 8),2,3,10,20);
        event.pointerId = 4; event.pointerCount = 2; event.history.add(new float[]{1,2}); event.historyTimes.add(15L);
        check(event.getActionMasked() == MotionEvent.ACTION_POINTER_UP && event.getActionIndex() == 1, "action encoding");
        check(event.getPointerId(0) == 4 && event.getPointerCount() == 2 && event.getHistoricalEventTime(0) == 15, "supplied simple motion values");
        Paint paint = new Paint(); paint.setColor(0xff123456); paint.setStrokeWidth(2); paint.setStyle(Paint.Style.STROKE);
        Path path = new Path(); path.moveTo(1,2); path.lineTo(3,4); Canvas canvas = new Canvas(); canvas.drawPath(path,paint);
        check(canvas.draws.size() == 1 && canvas.draws.get(0).color() == 0xff123456 && path.commands.size() == 2, "recorded primitive geometry/paint");
        int save = canvas.save(); canvas.translate(2,4); canvas.restoreToCount(save);
        check(canvas.translationX == 0 && canvas.translationY == 0, "simple save/restore shape");
        done("simple-motion-and-recorded-graphics-not-native-semantics");
    }

    private record Strong(String name,String method,String descriptor,int bci,int line) {}
    private static boolean strongProbe;
    private static void strongSiteWitness() throws Exception {
        List<Strong> hookFrames = new ArrayList<>(); List<ConcreteHostProbe.Site> retained = new ArrayList<>();
        ConcreteHostProbe.hook = (method,phase) -> {
            if (method.equals("Paint.setColor") && phase.equals("entry")) {
                Strong site = StackWalker.getInstance(StackWalker.Option.RETAIN_CLASS_REFERENCE).walk(stream -> stream
                    .filter(frame -> frame.getClassName().equals("dev.mixer.android.NativeRenderer$IndependentLeafTraceWitness") && frame.getMethodName().equals("sameLine"))
                    .findFirst().map(frame -> new Strong(frame.getClassName(),frame.getMethodName(),frame.getDescriptor(),frame.getByteCodeIndex(),frame.getLineNumber())).orElseThrow());
                hookFrames.add(site); retained.add(ConcreteHostProbe.lastEvent().productionFrames.get(0));
            }
        };
        NativeRenderer$IndependentLeafTraceWitness.sameLine(new Paint());
        check(hookFrames.size() == 2, "two exact same-line calls reached");
        Strong a = hookFrames.get(0), b = hookFrames.get(1);
        check(a.name.equals(b.name) && a.method.equals(b.method) && a.descriptor.equals(b.descriptor) && a.line == b.line && a.bci != b.bci, "independent synchronous descriptor/BCI disambiguates same source line");
        check(retained.get(0).className().equals(retained.get(1).className()) && retained.get(0).methodName().equals(retained.get(1).methodName()) && retained.get(0).line() == retained.get(1).line(), "old retained triple deliberately ambiguous");
        Set<String> fields = new HashSet<>(); for (RecordComponent field : ConcreteHostProbe.Site.class.getRecordComponents()) fields.add(field.getName());
        strongProbe = fields.contains("descriptor") && fields.contains("bytecodeIndex");
        if (strongProbe) for (int i=0;i<2;i++) {
            Object descriptor = ConcreteHostProbe.Site.class.getMethod("descriptor").invoke(retained.get(i));
            Object index = ConcreteHostProbe.Site.class.getMethod("bytecodeIndex").invoke(retained.get(i));
            check(descriptor.equals(hookFrames.get(i).descriptor) && index.equals(hookFrames.get(i).bci), "delta2 retained descriptor and BCI match independent hook");
        }
        System.out.println("{\"traceWitness\":true,\"syntheticOnly\":true,\"sameLine\":"+a.line+",\"firstBCI\":"+a.bci+",\"secondBCI\":"+b.bci+",\"descriptor\":\""+a.descriptor+"\",\"probeRetainsStrongSite\":"+strongProbe+"}");
        done("same-line-strong-site-discrimination-synthetic-only");
    }

    public static void main(String[] args) throws Exception {
        ConcreteHostProbe.reset();
        probeCallbacks();probeBounds();handlerShape();registrationShape();earlyVirtualsAndHierarchy();assetBytes();
        textWatcherOrder();compositionAndCodePoints();forwardingSurface();nativeBridgeShape();motionAndGraphics();strongSiteWitness();
        check(controls == 12,"all leaf-only controls executed");
        System.out.println("{\"scope\":\"leaf-only sanity; zero product classes\",\"controls\":"+controls+",\"assertions\":"+assertions+",\"probeRetainsStrongSite\":"+strongProbe+",\"productTests\":0}");
    }
}

/** Synthetic marker ONLY for the probe's name filter. This is not NativeRenderer,
 * a product copy, a renderer double, or evidence for any actual product body. */
final class NativeRenderer$IndependentLeafTraceWitness {
    private NativeRenderer$IndependentLeafTraceWitness() {}
    static void sameLine(Paint paint) { paint.setColor(11); paint.setColor(22); }
}
