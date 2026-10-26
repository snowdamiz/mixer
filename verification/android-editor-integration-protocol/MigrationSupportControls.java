package dev.mixer.android;

import android.app.Activity;
import android.os.Handler;
import android.text.Editable;
import android.view.KeyEvent;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.EditText;
import java.lang.reflect.InvocationTargetException;
import java.nio.file.Files;
import java.nio.file.Path;

/** Bounded historical-class controls. No corrected-candidate or native equivalence claim. */
public final class MigrationSupportControls {
    private MigrationSupportControls() {}
    private static int assertions;
    private static final Class<?> SUITE = NativeOwnerV2ConcreteHostTests.class;
    private static Object field(Object owner, String name) {
        try {
            var value = owner.getClass().getDeclaredField(name);
            value.setAccessible(true);
            return value.get(owner);
        } catch (ReflectiveOperationException failure) { throw new AssertionError(failure); }
    }
    private static Object call(Object owner, String name) {
        try {
            var method = owner.getClass().getDeclaredMethod(name);
            method.setAccessible(true);
            return method.invoke(owner);
        } catch (InvocationTargetException failure) { throw unchecked(failure.getCause()); }
        catch (ReflectiveOperationException failure) { throw new AssertionError(failure); }
    }
    private static RuntimeException unchecked(Throwable failure) {
        if (failure instanceof Error error) throw error;
        if (failure instanceof RuntimeException ordinary) return ordinary;
        throw new AssertionError(failure);
    }
    private static byte[] packet(String value) {
        try {
            var method = SUITE.getDeclaredMethod("packet", long.class, String.class, String.class);
            method.setAccessible(true);
            return (byte[]) method.invoke(null, 2L, "field", value);
        } catch (InvocationTargetException failure) { throw unchecked(failure.getCause()); }
        catch (ReflectiveOperationException failure) { throw new AssertionError(failure); }
    }
    private static void check(boolean value, String message) {
        assertions++;
        if (!value) throw new AssertionError(message);
    }
    private static final class Fixture implements AutoCloseable {
        private final Object reused;
        final NativeOwnerV2 owner;
        final NativeRenderer renderer;
        final NativeOwnerV2.Fence fence;
        final EditText editor;
        final NativeAppearanceViewsV2.Record record;
        final InputConnection connection;
        final Activity activity;
        final Handler queue;
        Throwable expectedCleanupFailure;
        Fixture() {
            ConcreteHostProbe.reset();
            try {
                var constructor = Class.forName(SUITE.getName() + "$Fixture").getDeclaredConstructor(String.class);
                constructor.setAccessible(true);
                reused = constructor.newInstance("field");
            } catch (InvocationTargetException failure) { throw unchecked(failure.getCause()); }
            catch (ReflectiveOperationException failure) { throw new AssertionError(failure); }
            call(reused, "ready");
            owner = (NativeOwnerV2) field(reused, "owner");
            renderer = (NativeRenderer) call(reused, "renderer");
            fence = (NativeOwnerV2.Fence) call(reused, "fence");
            activity = (Activity) field(reused, "activity");
            queue = (Handler) field(reused, "queue");
            editor = (EditText) renderer.view("field");
            record = renderer.inspectV2().get("field");
            check(!record.changing, "healthy fixture started changing");
            check(editor.getSelectionStart() == 0 && editor.getSelectionEnd() == 0, "initial cursor must be zero");
            editor.requestFocus();
            connection = editor.onCreateInputConnection(new EditorInfo());
            check(connection != null, "healthy connection unavailable");
        }
        @Override public void close() {
            ConcreteHostProbe.hook = null;
            record.changing = false;
            try { call(reused, "close"); }
            catch (RuntimeException | Error failure) {
                check(failure == expectedCleanupFailure, "unexpected fixture cleanup failure");
                try { queue.drainAll(4); }
                catch (RuntimeException | Error cleanup) {
                    check(cleanup == expectedCleanupFailure, "cleanup changed retained fatal identity");
                }
            }
            check(queue.queued() == 0, "fixture owned queue retained");
        }
    }
    private static void batchCurrent() {
        try (Fixture f = new Fixture()) {
            var before = f.fence.presentation;
            int entries = ConcreteHostProbe.count("BaseInputConnection.beginBatchEdit", "entry");
            check(f.connection.beginBatchEdit(), "healthy beginBatchEdit refused");
            check(ConcreteHostProbe.count("BaseInputConnection.beginBatchEdit", "entry") == entries + 1, "target not called exactly once");
            check(f.fence.presentation == before && !f.fence.terminal, "non-text ordinary case changed presentation");
        }
        System.out.println("PASS current-batch-normal-leaf");
    }
    private static void changingRefusal() {
        try (Fixture f = new Fixture()) {
            int entries = ConcreteHostProbe.count("BaseInputConnection.beginBatchEdit", "entry");
            f.record.changing = true;
            check(!f.connection.beginBatchEdit(), "changing entry unexpectedly forwarded");
            check(ConcreteHostProbe.count("BaseInputConnection.beginBatchEdit", "entry") == entries, "changing entry reached native target");
            check(!f.fence.terminal, "clean changing refusal became terminal");
        }
        System.out.println("PASS changing-is-separate-invalid-entry");
    }
    private static void appendCallback() {
        try (Fixture f = new Fixture()) {
            int length = f.editor.getText().length();
            f.editor.setSelection(length, length);
            check(f.editor.getSelectionStart() == length && f.editor.getSelectionEnd() == length, "append cursor not explicit");
            Editable buffer = f.editor.getText();
            var before = f.fence.presentation;
            int prepared = NativeBridge.prepareCalls, committed = NativeBridge.commitCalls;
            NativeBridge.preparedPacket = packet("helloz");
            check(f.connection.commitText("z", 1), "ordinary real callback append refused");
            check(f.editor.getText() == buffer && buffer.toString().equals("helloz"), "text callback replaced buffer or append value");
            check(NativeBridge.prepareCalls == prepared + 1 && NativeBridge.commitCalls == committed + 1, "watcher did not deliver real feature transaction");
            check(f.fence.presentation != before && !f.fence.terminal, "ordinary text callback did not publish successor");
        }
        System.out.println("PASS ordinary-append-keeps-watchers-and-publishes-successor");
    }
    private static void injectedSuccessor() {
        try (Fixture f = new Fixture()) {
            var before = f.fence.presentation;
            var old = NativeAppearanceViewsV2.Mutation.live(f.fence);
            int prepared = NativeBridge.prepareCalls;
            boolean[] reached = {false};
            ConcreteHostProbe.hook = (method, phase) -> {
                if (!reached[0] && method.equals("BaseInputConnection.beginBatchEdit") && phase.equals("beforeReturn")) {
                    reached[0] = true;
                    ConcreteHostProbe.hook = null;
                    NativeBridge.preparedPacket = packet(f.editor.getText().toString());
                    f.editor.hostReplace(0, f.editor.getText().length(), f.editor.getText().toString());
                }
            };
            check(f.connection.beginBatchEdit(), "injected-successor batch result refused");
            check(reached[0] && f.fence.presentation != before && NativeBridge.prepareCalls == prepared + 1, "injected same-buffer feature event did not publish");
            check(!old.current() && !f.fence.terminal, "old mutation survived or healthy injected successor retired");
        }
        System.out.println("PASS batch-with-separately-injected-real-same-buffer-feature-event");
    }
    private static final class Fatal extends Error {
        private static final long serialVersionUID = 1L;
    }
    private static void fatalControl() {
        try (Fixture f = new Fixture()) {
            Fatal fatal = new Fatal();
            ConcreteHostProbe.hook = (method, phase) -> {
                if (method.equals("BaseInputConnection.beginBatchEdit") && phase.equals("beforeReturn")) {
                    ConcreteHostProbe.hook = null;
                    throw fatal;
                }
            };
            Throwable escaped = null;
            try { f.connection.beginBatchEdit(); } catch (RuntimeException | Error failure) { escaped = failure; }
            check(escaped == fatal, "fatal target identity lost");
            check(f.fence.terminal && f.owner.cleanupLedger().firstFatal() == fatal, "fatal did not retain ledger/retirement");
            f.expectedCleanupFailure = fatal;
        }
        System.out.println("PASS fatal-batch-normal-leaf");
    }
    private static void closedControl(String state) {
        try (Fixture f = new Fixture()) {
            if (state.equals("terminal")) f.owner.close();
            else if (state.equals("dirty")) f.owner.onPause();
            else f.activity.getResources().configuration.uiMode = android.content.res.Configuration.UI_MODE_NIGHT_YES;
            int entries = ConcreteHostProbe.count("BaseInputConnection.beginBatchEdit", "entry");
            check(!f.connection.beginBatchEdit(), state + " forwarded batch");
            check(ConcreteHostProbe.count("BaseInputConnection.beginBatchEdit", "entry") == entries, state + " target entered");
        }
        System.out.println("PASS " + state + "-batch-no-target-entry");
    }
    private static void sendKeyRefusal() {
        try (Fixture f = new Fixture()) {
            int before = ConcreteHostProbe.events().size();
            check(!f.connection.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_SPACE)), "sendKeyEvent accepted");
            check(ConcreteHostProbe.events().size() == before, "sendKeyEvent performed leaf work");
        }
        System.out.println("PASS sendKeyEvent-clean-direct-refusal");
    }
    public static void main(String[] args) throws Exception {
        var descriptor = SUITE.getDeclaredField("descriptor");
        descriptor.setAccessible(true);
        descriptor.set(null, Files.readAllBytes(Path.of(args[0])));
        batchCurrent();
        changingRefusal();
        appendCallback();
        injectedSuccessor();
        fatalControl();
        for (String state : new String[]{"terminal", "dirty", "stale"}) closedControl(state);
        sendKeyRefusal();
        System.out.println("PASS historical migration support: 9 controls / " + assertions + " assertions; no corrected-source acceptance or native equivalence");
    }
}
