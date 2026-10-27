package dev.mixer.android;

import android.app.Activity;
import android.text.InputFilter;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.TextAttribute;
import android.widget.EditText;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

/** Independent ordinary-Java controls for exactly the two added return wrappers. */
public final class IndependentAttributeControls {
    private IndependentAttributeControls() {}
    private static int assertions;
    private static final String DESC = "(Ljava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z";
    private static final class Fatal extends Error {
        private static final long serialVersionUID = 1L;
    }
    private static void check(boolean condition, String explanation) {
        assertions++;
        if (!condition) throw new AssertionError(explanation);
    }
    private static EditText editor() {
        EditText result = new EditText(new Activity());
        result.setText("old");
        result.setSelection(3, 3);
        return result;
    }
    private static String name(String family) {
        return "BaseInputConnection." + family + "WithAttributes";
    }
    private static boolean call(BaseInputConnection target, String family) {
        return family.equals("commitText")
            ? target.commitText("z", 1, new TextAttribute())
            : target.setComposingText("z", 1, new TextAttribute());
    }
    private static void returnAndCaptureFailure(String family, boolean initiallyClosed,
                                               boolean fatalObserver) {
        EditText edit = editor();
        int[] filters = {0};
        edit.setFilters(new InputFilter[]{(s, start, end, dest, dstart, dend) -> {
            filters[0]++;
            return null;
        }});
        BaseInputConnection target = new BaseInputConnection(edit, true);
        target.closed = initiallyClosed;
        Throwable secondary = fatalObserver ? new Fatal() : new IllegalArgumentException("observer");
        List<String> order = new ArrayList<>();
        List<NativeOutcomeProbe.Outcome> rows = new ArrayList<>();
        ConcreteHostProbe.reset();
        NativeOutcomeProbe.begin(value -> {
            if (!value.method().equals(name(family))) return;
            rows.add(value);
            order.add("capture");
            ConcreteHostProbe.fail(secondary);
        });
        ConcreteHostProbe.hook = (method, phase) -> {
            if (!method.equals(name(family))) return;
            order.add("ordinary-" + phase);
            if (phase.equals("beforeReturn")) target.closed = !initiallyClosed;
        };
        Consumer<ConcreteHostProbe.Event> qualification = event -> {
            if (event.method.equals(name(family))) order.add("qualification-" + event.phase);
        };
        ConcreteHostProbe.installQualificationHook(qualification);
        boolean actual;
        try {
            actual = call(target, family);
        } finally {
            ConcreteHostProbe.clearQualificationHook(qualification);
            ConcreteHostProbe.hook = null;
            NativeOutcomeProbe.end();
        }
        check(actual == !initiallyClosed, "observer failure preserves computed native boolean");
        check(rows.size() == 1 && rows.get(0).value().equals(actual)
            && rows.get(0).receiver() == target && rows.get(0).descriptor().equals(DESC)
            && rows.get(0).completion().equals("return")
            && rows.get(0).originalException() == null, "one exact typed completion before sink failure");
        check(order.equals(List.of("ordinary-entry", "qualification-entry",
            "ordinary-beforeReturn", "qualification-beforeReturn", "capture")),
            "original ordinary and qualification callback order precedes measured return");
        check(filters[0] == (initiallyClosed ? 0 : 1), "insert expression evaluates once");
        check(edit.getText().toString().equals(initiallyClosed ? "old" : "oldz"), "original text effect");
        check(target.mutations == 1 && ConcreteHostProbe.count(name(family), "entry") == 1
            && ConcreteHostProbe.count(name(family), "beforeReturn") == 1, "original counts preserved");
        check(!NativeOutcomeProbe.clean() && NativeOutcomeProbe.captureFailure() == secondary,
            "observer failure is retained as refusal after end");
        ConcreteHostProbe.reset();
    }
    private static void originalAndCaptureFailure(String family, String phase,
                                                  boolean qualified, boolean originalFatal) {
        EditText edit = editor();
        BaseInputConnection target = new BaseInputConnection(edit, true);
        Throwable original = originalFatal ? new Fatal() : new IllegalStateException("original");
        Throwable secondary = originalFatal ? new IllegalArgumentException("observer") : new Fatal();
        List<NativeOutcomeProbe.Outcome> rows = new ArrayList<>();
        ConcreteHostProbe.reset();
        NativeOutcomeProbe.begin(value -> {
            if (!value.method().equals(name(family))) return;
            rows.add(value);
            ConcreteHostProbe.fail(secondary);
        });
        Consumer<ConcreteHostProbe.Event> qualification = event -> {
            if (event.method.equals(name(family)) && event.phase.equals(phase)) {
                ConcreteHostProbe.fail(original);
            }
        };
        if (qualified) ConcreteHostProbe.installQualificationHook(qualification);
        else ConcreteHostProbe.hook = (method, at) -> {
            if (method.equals(name(family)) && at.equals(phase)) ConcreteHostProbe.fail(original);
        };
        Throwable escaped = null;
        try {
            call(target, family);
        } catch (RuntimeException | Error failure) {
            escaped = failure;
        } finally {
            if (qualified) ConcreteHostProbe.clearQualificationHook(qualification);
            ConcreteHostProbe.hook = null;
            NativeOutcomeProbe.end();
        }
        check(escaped == original, "original unchecked throwable identity survives observer failure");
        check(rows.size() == 1 && rows.get(0).completion().equals("exception")
            && rows.get(0).descriptor().equals("hook-exception")
            && rows.get(0).originalException() == original && rows.get(0).value() == null,
            "hook exception is honest and no native return is invented");
        check(ConcreteHostProbe.count(name(family), "entry") == 1
            && ConcreteHostProbe.count(name(family), "beforeReturn") == (phase.equals("entry") ? 0 : 1)
            && target.mutations == (phase.equals("entry") ? 0 : 1), "original exception cut preserves counts");
        check(edit.getText().toString().equals(phase.equals("entry") ? "old" : "oldz"),
            "original effect precedes beforeReturn exception");
        check(!NativeOutcomeProbe.clean() && NativeOutcomeProbe.captureFailure() == secondary,
            "failed exception observation refuses evidence without replacing original");
        ConcreteHostProbe.reset();
    }
    private static void bodyExceptionRemainsUnobserved(String family, boolean fatal) {
        EditText edit = editor();
        Throwable original = fatal ? new Fatal() : new IllegalStateException("filter body");
        int[] filters = {0};
        edit.setFilters(new InputFilter[]{(s, start, end, dest, dstart, dend) -> {
            filters[0]++;
            ConcreteHostProbe.fail(original);
            return null;
        }});
        BaseInputConnection target = new BaseInputConnection(edit, true);
        List<NativeOutcomeProbe.Outcome> rows = new ArrayList<>();
        ConcreteHostProbe.reset();
        NativeOutcomeProbe.begin(rows::add);
        Throwable escaped = null;
        try {
            call(target, family);
        } catch (RuntimeException | Error failure) {
            escaped = failure;
        } finally {
            NativeOutcomeProbe.end();
        }
        check(escaped == original && filters[0] == 1, "original body exception escapes exactly once");
        check(rows.stream().noneMatch(row -> row.method().equals(name(family))),
            "body exception creates neither native return nor hook exception observation");
        check(ConcreteHostProbe.count(name(family), "entry") == 1
            && ConcreteHostProbe.count(name(family), "beforeReturn") == 0 && target.mutations == 1,
            "body exception retains original incomplete callback sequence");
        check(NativeOutcomeProbe.clean(), "clean observer alone does not assert full body-exception coverage");
        ConcreteHostProbe.reset();
    }
    private static void boundedOverflow(String family) {
        EditText edit = editor();
        BaseInputConnection target = new BaseInputConnection(edit, true);
        int[] captured = {0};
        ConcreteHostProbe.reset();
        NativeOutcomeProbe.begin(value -> captured[0]++);
        for (int i = 0; i < NativeOutcomeProbe.LIMIT; i++) {
            check(NativeOutcomeProbe.returned("limit-fill", "()Z", target, true), "fill return preserved");
        }
        check(call(target, family), "capture overflow preserves native true");
        target.closed = true;
        check(!call(target, family), "capture overflow preserves native false");
        NativeOutcomeProbe.end();
        check(captured[0] == NativeOutcomeProbe.LIMIT && !NativeOutcomeProbe.clean()
            && NativeOutcomeProbe.failed(), "bounded observer overrun refuses capture");
        check(ConcreteHostProbe.count(name(family), "entry") == 2
            && ConcreteHostProbe.count(name(family), "beforeReturn") == 2,
            "capture overflow leaves original callback counts intact");
        ConcreteHostProbe.reset();
    }
    public static void main(String[] arguments) {
        for (String family : List.of("commitText", "setComposingText")) {
            for (boolean closed : new boolean[]{false, true})
                for (boolean fatal : new boolean[]{false, true}) returnAndCaptureFailure(family, closed, fatal);
            for (String phase : List.of("entry", "beforeReturn"))
                for (boolean qualified : new boolean[]{false, true})
                    for (boolean fatal : new boolean[]{false, true})
                        originalAndCaptureFailure(family, phase, qualified, fatal);
            for (boolean fatal : new boolean[]{false, true}) bodyExceptionRemainsUnobserved(family, fatal);
            boundedOverflow(family);
        }
        System.out.println("PASS independent exact attribute wrappers assertions=" + assertions);
    }
}
