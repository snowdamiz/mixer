package dev.mixer.android;

import android.text.Spanned;
import android.view.KeyEvent;
import android.view.inputmethod.InputConnection;
import java.lang.reflect.Proxy;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.function.Supplier;

public final class TitleInputControl {
    private static final String HISTORICAL = "Inspect pump P-17";
    private static final String TITLE = F06TitleInput.TITLE;
    private static final String ADD = F06TitleInput.ADD;
    private static final AndroidUIProfile V4 = AndroidUIProfile.MEASURED_MULTILINE_LONG_NOTES_V4;

    private final List<String> reports = new ArrayList<>();
    private final F06TitleInput input = new F06TitleInput(reports::add);
    private final NativeAppearanceViewsV2.NativeField field = new NativeAppearanceViewsV2.NativeField(input, this::capture);
    private UiPacket frame = packet(1, 2, "", true);
    private final List<byte[]> envelopes = new ArrayList<>();
    private int consumed;

    private TitleInputControl() { input.witnessed(frame, field); }

    private void capture(String value) {
        byte[] envelope = frame.event(TITLE, "2", "textChange", value);
        check(input.captureTitle(frame, envelope), "capture exact title envelope");
        envelopes.add(envelope);
    }

    private static UiPacket packet(int revision, int generation, String value, boolean vertical) {
        String wire = """
            {"schemaVersion":1,"document":{"schemaVersion":1,"revision":%d,"root":{
              "id":"task.screen","kind":"navigation","properties":{},"actions":[],"children":[
                {"id":"stack","kind":"vStack","properties":{},"actions":[],"children":[
                  {"id":"task.title","kind":"textField","properties":{"axis":"%s","label":"Title","value":%s},
                   "children":[],"actions":[{"id":"task.title","event":"textChange"}]},
                  {"id":"task.save","kind":"button","properties":{"label":"Add"},"children":[],
                   "actions":[{"id":"task.save","event":"activate"}]}
                ]}
              ]}},"identities":[{"id":"task.screen","generation":1},{"id":"task.title","generation":%d},
                               {"id":"task.save","generation":3},{"id":"stack","generation":4}]}
            """.formatted(revision, vertical ? "vertical" : "horizontal",
                new String(Json.encode(value), java.nio.charset.StandardCharsets.UTF_8), generation);
        return UiPacket.decode(wire.getBytes(java.nio.charset.StandardCharsets.UTF_8), V4);
    }

    private void key(char value) { check(input.key(field, new KeyEvent(value)), "accept key " + value); }

    private void echo(String value) {
        String prefix = frame.nodes.get(TITLE).text("value", "");
        check(value.startsWith(prefix), "append-only control");
        check(envelopes.size() == consumed + 1 && input.awaiting(frame), "single in-flight turn");
        check(Arrays.equals(envelopes.get(consumed++), frame.event(TITLE, "2", "textChange", value)),
            "exact emitted revision, identity and value");
        input.suspend();
        frame = packet(Integer.parseInt(frame.revision) + 1, 2, value, true);
        check(!input.addAllowed(frame, field), "Add before real witness");
        input.witnessed(frame, field);
    }

    private void burst() {
        check(input.addAllowed(frame, field), "initial Add authority remains guest-owned");
        UiPacket initial = frame;
        for (char value : HISTORICAL.toCharArray()) key(value);
        check(field.buffer.toString().equals("I") && envelopes.size() == 1, "burst buffered before mutation");
        input.witnessed(initial, field);
        check(field.buffer.toString().equals("I"), "same frame witness cannot release next key");
        for (int count = 1; count <= HISTORICAL.length(); count++) {
            check(!input.addAllowed(frame, field), "Add while historical keys remain");
            echo(HISTORICAL.substring(0, count));
        }
        check(field.buffer.toString().equals(HISTORICAL) && input.addAllowed(frame, field), "exact final title gates Add");
        check(!input.addAllowed(initial, field), "queued Add from old frame refused");
        check(reports.isEmpty(), "healthy burst without refusals");
        System.out.println("PASS historical burst: 17 exact revision-bound envelopes through revision " + frame.revision);
    }

    private void ime() {
        var connection = new NativeEditorConnectionV2.Api33(field, field.attempt);
        check(connection.commitText("Inspect ", 1), "plain two-argument commit");
        check(connection.commitText("pump ", 1, null), "plain three-argument commit without attributes");
        check(connection.commitText("P-17", 1), "second queued plain commit");
        check(field.buffer.toString().equals("Inspect "), "later commits did not mutate before echo");
        check(!connection.setComposingText("x", 1) && !connection.setComposingText("x", 1, null) &&
            !connection.setComposingRegion(0, 1) && !connection.finishComposingText() &&
            !connection.deleteSurroundingText(1, 0) && !connection.setSelection(0, 0) &&
            !connection.performEditorAction(0) && !connection.performEditorAction(6) &&
            !connection.beginBatchEdit() && !connection.endBatchEdit(), "unsupported IME operations refused");
        Spanned styled = (Spanned) Proxy.newProxyInstance(getClass().getClassLoader(), new Class<?>[]{Spanned.class},
            (ignored, method, args) -> { throw new AssertionError("Spanned value was read"); });
        check(!connection.commitText(styled, 1) && !connection.commitText(null, 1) &&
            !connection.commitText("x", 0) && !connection.commitText("a".repeat(1025), 1) &&
            !connection.commitText(new String(new char[]{(char) 0xd800}), 1), "invalid commit shapes refused");
        echo("Inspect ");
        echo("Inspect pump ");
        echo(HISTORICAL);
        check(input.addAllowed(frame, field), "Add follows final IME echo");
        check(connection.commitText("\n\u03a9\ud83d\ude00", 1), "plain multiline Unicode draft admitted");
        echo(HISTORICAL + "\n\u03a9\ud83d\ude00");
        System.out.println("PASS plain IME commits, multiline Unicode draft, and refusals at controlled connection");
    }

    private void negative(String kind) {
        key('I');
        key('n');
        input.suspend();
        switch (kind) {
            case "echo" -> frame = packet(2, 2, "X", true);
            case "generation" -> frame = packet(2, 5, "I", true);
            case "revision" -> frame = packet(1, 2, "I", true);
            case "editable" -> {
                field.buffer = new StringBuilder("I");
                frame = packet(2, 2, "I", true);
            }
            case "loss" -> {
                input.lost();
                frame = packet(2, 2, "I", true);
            }
            default -> throw new AssertionError(kind);
        }
        input.witnessed(frame, field);
        check(!input.addAllowed(frame, field) && envelopes.size() == 1 &&
            reports.stream().anyMatch(report -> report.startsWith("Title input incomplete")),
            "queued edit and Add fenced after " + kind);
    }

    private void cancel() {
        key('I');
        key('n');
        input.abandon();
        input.close();
        check(envelopes.size() == 1 && !input.awaiting(frame) && !input.addAllowed(frame, field),
            "Cancel discards queued title and closes Add");
    }

    private static void check(boolean state, String message) {
        if (!state) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        check(F06TitleInput.isTitle(TITLE, true) && !F06TitleInput.isTitle(TITLE, false) &&
            !F06TitleInput.isTitle("task.notes", true), "exact private selector");
        new TitleInputControl().burst();
        new TitleInputControl().ime();
        for (String kind : List.of("echo", "generation", "revision", "editable", "loss")) {
            new TitleInputControl().negative(kind);
        }
        new TitleInputControl().cancel();
        System.out.println("PASS exact axis selector, wrong echo/generation/revision, replacement and loss, and Cancel");
    }
}

// Controlled native leaves shared by the actual title policy and the actual connection adapter.
final class NativeEnvironmentV2 { static void requireMain() {} }

final class NativeAppearanceViewsV2 {
    static final class NativeField {
        static final class Attempt {
            final InputConnection target;
            final CharSequence editable;
            Attempt(InputConnection target, CharSequence editable) { this.target = target; this.editable = editable; }
        }

        static final class Record { final String generation = "2"; }
        final Record record = new Record();
        final F06TitleInput input;
        final java.util.function.Consumer<String> changed;
        StringBuilder buffer = new StringBuilder();
        final Attempt attempt;

        NativeField(F06TitleInput input, java.util.function.Consumer<String> changed) {
            this.input = input;
            this.changed = changed;
            var target = (InputConnection) Proxy.newProxyInstance(getClass().getClassLoader(),
                new Class<?>[]{InputConnection.class}, (ignored, method, args) -> {
                    if (!method.getName().equals("commitText") || args.length != 2)
                        throw new AssertionError("Unsupported operation reached native leaf: " + method);
                    return append(args[0].toString());
                });
            attempt = new Attempt(target, buffer);
        }

        private boolean append(String value) {
            if (!input.admitsNativeMutation()) throw new AssertionError("Mutation outside exact edit turn");
            buffer.append(value);
            if (!value.isEmpty()) changed.accept(buffer.toString());
            return true;
        }
        F06TitleInput f06TitleInput() { return input; }
        boolean f06SameInput(Attempt expected) { return attempt == expected; }
        CharSequence nativeEditable() { return buffer; }
        boolean nativeKeyDown(int code, KeyEvent event) { return append(new String(Character.toChars(code))); }
        boolean proposal(CharSequence text, boolean composing) { return text != null; }
        <T> T dispatch(Attempt expected, String hook, T refused, Supplier<T> action) {
            return expected == attempt ? action.get() : refused;
        }
        <T> T nativeValue(Attempt expected, T refused, Supplier<T> action) {
            return expected == attempt ? action.get() : refused;
        }
        void close(Attempt expected) { input.lost(); }
    }
}
