package dev.mixer.android;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.os.Build;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.View;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.EditText;
import android.widget.Switch;
import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

/** Real SDK/JNI/Swift/native integration only. No host leaves or engine status substitutions. */
@SuppressWarnings("deprecation")
public final class CoordinatorJoinInstrumentation extends Instrumentation {
    private int checks;
    private int operations;
    private int maximumChecks;
    private CoordinatorJoinActivity window;
    private final List<Object> observations = new ArrayList<>();
    private final Map<String, Object> packets = new LinkedHashMap<>();
    private String expectedDescriptor;

    @Override public void onCreate(Bundle arguments) {
        super.onCreate(arguments);
        expectedDescriptor = arguments == null ? null : arguments.getString("descriptorSHA256");
        start();
    }

    private void check(boolean condition, String name) {
        if (++checks > maximumChecks) throw new AssertionError("bounded check budget exceeded");
        observations.add(Json.map("check", name, "passed", condition));
        if (!condition) throw new AssertionError(name);
    }

    private void status(String name, int actual, int expected) {
        observations.add(Json.map("nativeStatus", name, "actual", actual, "expected", expected));
        check(actual == expected, name);
    }

    private void onMain(Runnable operation) {
        AtomicReference<Throwable> failure = new AtomicReference<>();
        runOnMainSync(() -> {
            try { operation.run(); }
            catch (RuntimeException | Error rejected) { failure.set(rejected); }
        });
        if (failure.get() instanceof RuntimeException rejected) throw rejected;
        if (failure.get() instanceof Error rejected) throw rejected;
    }

    private static Object field(Object object, String name) {
        try {
            Field value = object.getClass().getDeclaredField(name);
            value.setAccessible(true);
            return value.get(object);
        } catch (ReflectiveOperationException failure) { throw new AssertionError(name, failure); }
    }

    private static byte[] retained(NativeCoordinatorV2 coordinator) {
        return (byte[]) field(coordinator, "committedPacket");
    }

    private NativeRenderer renderer() { return (NativeRenderer) field(window.coordinator, "renderer"); }
    private long session() { return (Long) field(window.coordinator, "session"); }

    private static String sha(byte[] bytes) {
        try {
            StringBuilder result = new StringBuilder();
            for (byte value : MessageDigest.getInstance("SHA-256").digest(bytes))
                result.append(String.format(java.util.Locale.ROOT, "%02x", value & 255));
            return result.toString();
        } catch (NoSuchAlgorithmException failure) { throw new AssertionError(failure); }
    }

    private void write(String name, byte[] bytes) {
        try { Files.write(getTargetContext().getFilesDir().toPath().resolve(name), bytes); }
        catch (IOException failure) { throw new AssertionError(name, failure); }
    }

    private void packet(String name, byte[] bytes, String provenance) {
        UiPacket packet = UiPacket.decode(bytes);
        write(name + ".bin", bytes);
        packets.put(name, Json.map("file", name + ".bin", "sha256", sha(bytes),
            "revision", packet.revision, "nodeCount", packet.nodes.size(), "provenance", provenance));
    }

    private byte[] asset(String path) {
        try (InputStream stream = getTargetContext().getAssets().open(path)) {
            return stream.readNBytes(65537);
        } catch (IOException failure) { throw new AssertionError(path, failure); }
    }

    private void exceptionStatus(String name, Runnable call, int expected) {
        RuntimeException failure = null;
        try { call.run(); }
        catch (RuntimeException rejected) { failure = rejected; }
        String text = failure == null ? "" : failure.toString();
        observations.add(Json.map("nativeException", name, "actual", text, "expectedStatus", expected));
        check(failure != null && text.contains("(status " + expected + ")"), name);
    }

    private void jni() {
        long handle = NativeBridge.create();
        long foreign = 0;
        try {
            foreign = NativeBridge.create();
            check(handle != 0 && foreign != 0 && handle != foreign, "actual Swift session registry owners");
            NativeBridge.Candidate initial = NativeBridge.prepareV2(handle, 0, null);
            byte[] original = initial.packet();
            UiPacket first = UiPacket.decode(original);
            check(initial.token() != 0 && first.revision.equals("1") && first.nodes.containsKey("task.1")
                && first.nodes.containsKey("task.2"), "ordinary compiled ChecklistEngine initial packet");
            packet("jni-initial", original, "actual NativeBridge.prepareV2 -> C JNI -> Swift ordinary registry/ChecklistEngine");
            byte[] copy = initial.packet();
            copy[0] ^= 1;
            check(Arrays.equals(original, initial.packet()), "JNI candidate packet copies are defensive");
            exceptionStatus("second candidate busy", () -> NativeBridge.prepareV2(handle, 0, null), 5);
            status("foreign token rejected", NativeBridge.commitV2(foreign, initial.token()), 6);
            status("zero token rejected", NativeBridge.abortV2(handle, 0), 6);
            status("initial abort", NativeBridge.abortV2(handle, initial.token()), 0);
            status("idempotent abort", NativeBridge.abortV2(handle, initial.token()), 0);
            status("aborted token cannot commit", NativeBridge.commitV2(handle, initial.token()), 6);
            UiPacket.Node task = first.nodes.get("task.1");
            NativeBridge.Candidate input = NativeBridge.prepareV2(handle, 1,
                first.event(task.id, task.generation, "valueChange", true));
            check(UiPacket.decode(input.packet()).nodes.get("task.1").flag("value", false),
                "actual ordinary reducer prepared input");
            status("actual engine candidate commit", NativeBridge.commitV2(handle, input.token()), 0);
            status("one-use commit token", NativeBridge.commitV2(handle, input.token()), 6);
            NativeBridge.Candidate committed = NativeBridge.prepareV2(handle, 0, null);
            UiPacket next = UiPacket.decode(committed.packet());
            check(next.revision.equals("2") && next.nodes.get("task.1").flag("value", false),
                "actual Swift engine stores committed reducer state");
            packet("jni-committed", committed.packet(), "actual prepare render after scalar commit");
            status("render candidate abort", NativeBridge.abortV2(handle, committed.token()), 0);
            exceptionStatus("malformed ordinary input rejected", () -> NativeBridge.prepareV2(handle, 1, new byte[] {'!'}), 4);
            NativeBridge.Candidate live = NativeBridge.prepareV2(handle, 0, null);
            status("rejected input leaves actual registry live", NativeBridge.abortV2(handle, live.token()), 0);
        } finally {
            NativeBridge.destroy(handle);
            if (foreign != 0) NativeBridge.destroy(foreign);
        }
        status("destroyed session closed", NativeBridge.commitV2(handle, 1), 2);
    }

    private CoordinatorJoinActivity launch() {
        Intent intent = new Intent(getTargetContext(), CoordinatorJoinActivity.class)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        CoordinatorJoinActivity launched = (CoordinatorJoinActivity) startActivitySync(intent);
        waitWindow(launched);
        return launched;
    }

    private void waitWindow(CoordinatorJoinActivity activity) {
        long deadline = SystemClock.uptimeMillis() + 8000;
        AtomicReference<Boolean> ready = new AtomicReference<>(false);
        do {
            waitForIdleSync();
            onMain(() -> ready.set(activity.root.isAttachedToWindow() && activity.root.getWidth() > 0
                && activity.root.getHeight() > 0 && activity.root.hasWindowFocus()));
            if (ready.get()) return;
            SystemClock.sleep(20);
        } while (SystemClock.uptimeMillis() < deadline);
        throw new AssertionError("bounded attached/focused native window wait");
    }

    private void initial() {
        window = launch();
        onMain(() -> {
            NativeRenderer captureOwner = new NativeRenderer(window, ignored -> { throw new AssertionError("capture-only owner input"); });
            try {
                InstalledAppearanceV2 installed = captureOwner.captureInstalledV2();
                check(expectedDescriptor != null && installed.sha256.equals(expectedDescriptor),
                    "actual installed AssetManager descriptor exact build hash");
                NativeEnvironmentV2 environment = captureOwner.captureEnvironmentV2(window, window.root);
                var value = environment.value;
                check(Build.VERSION.SDK_INT == 37 && value.density1024() == 3072
                    && value.profile() == AppearanceDescriptorV2.Profile.l
                    && Float.compare(window.getResources().getConfiguration().fontScale, 1.0f) == 0,
                    "agreed API37/density3/default-font environment only");
                observations.add(Json.map("environment", value.toString(), "widthPixels", environment.width,
                    "heightPixels", environment.height, "descriptorSHA256", installed.sha256));
            } finally { captureOwner.disposeV2(); }
            window.coordinator = new NativeCoordinatorV2(window, window.root);
            window.coordinator.renderInitial();
            check(window.coordinator.hasCommittedPresentation() && !window.coordinator.isRetired(),
                "same APK ordinary Swift/JNI/coordinator/renderer initial commit");
            UiPacket initial = UiPacket.decode(retained(window.coordinator));
            check(initial.revision.equals("1") && initial.nodes.get("task.1").text("label", "").equals("Verify native input"),
                "coordinator packet comes from compiled ordinary engine");
            packet("joined-initial", retained(window.coordinator), "production coordinator committed packet observed by reflection only");
        });
        refresh();
    }

    private void refresh() {
        waitForIdleSync();
        onMain(() -> {
            window.coordinator.refreshEnvironment();
            check(renderer().presentationCurrentV2(), "actual renderer capture current and input/draw gate open");
        });
    }

    private void toggle() {
        refresh();
        onMain(() -> {
            byte[] before = retained(window.coordinator);
            UiPacket previous = UiPacket.decode(before);
            Switch toggle = window.root.findViewWithTag("mixer.task.1");
            check(toggle != null && toggle.isAttachedToWindow() && toggle.isShown()
                && toggle.isEnabled() && toggle.hasWindowFocus(), "actual native toggle input eligibility");
            check(toggle.performClick(), "actual Switch.performClick");
            UiPacket next = UiPacket.decode(retained(window.coordinator));
            check(new BigInteger(next.revision).equals(new BigInteger(previous.revision).add(BigInteger.ONE)),
                "one native toggle advances ordinary reducer revision once");
            check(next.nodes.get("task.1").flag("value", false) && toggle.isChecked()
                && renderer().view("task.1") == toggle, "same surviving native toggle agrees with Swift committed state");
            check(window.coordinator.lastNativeInputFailure() == null, "successful native toggle has no contained failure");
            packet("joined-toggle", retained(window.coordinator), "actual native Switch callback through production coordinator/JNI/reducer");
        });
    }

    private void text() {
        refresh();
        onMain(() -> {
            EditText draft = window.root.findViewWithTag("mixer.draft");
            check(draft != null && draft.requestFocus(), "actual native editor takes focus");
            draft.setSelection(draft.getText().length());
            InputConnection connection = draft.onCreateInputConnection(new EditorInfo());
            check(connection != null && connection.commitText("joined", 1), "actual native InputConnection commitText");
            check(!window.coordinator.isRetired() && window.coordinator.lastNativeInputFailure() == null,
                "ordinary text callback commits without coordinator retirement");
            UiPacket next = UiPacket.decode(retained(window.coordinator));
            check(next.nodes.get("draft").text("value", "").equals("joined")
                && draft.getText().toString().equals("joined") && renderer().view("draft") == draft,
                "actual native editor buffer acknowledged by ordinary Swift reducer");
            check(BaseInputConnection.getComposingSpanStart(draft.getText()) < 0,
                "committed text receipt has no invented composing span");
            packet("joined-text", retained(window.coordinator), "actual native InputConnection; no system keyboard or composition workflow claim");
            draft.clearFocus();
        });
    }

    private void environmentOnly() {
        refresh();
        onMain(() -> {
            byte[] retained = retained(window.coordinator);
            long handle = session();
            NativeBridge.Candidate pending = NativeBridge.prepareV2(handle, 0, null);
            long token = pending.token();
            try {
                window.coordinator.refreshEnvironment();
                check(retained(window.coordinator) == retained, "environment-only exact retained packet identity");
                check(Arrays.equals(retained(window.coordinator), retained), "environment-only exact retained packet bytes");
                check(renderer().presentationCurrentV2(), "environment-only real native finish reopens current capture");
                status("environment refresh leaves actual pending registry candidate intact", NativeBridge.abortV2(handle, token), 0);
                NativeBridge.Candidate after = NativeBridge.prepareV2(handle, 0, null);
                check(after.token() == token + 1, "environment-only allocates no ordinary engine prepare token");
                check(Arrays.equals(after.packet(), pending.packet()), "environment-only preserves actual Swift packet/state");
                status("post-refresh actual candidate disposal", NativeBridge.abortV2(handle, after.token()), 0);
            } finally { NativeBridge.abortV2(handle, token); }
            renderer().environmentInvalidatedV2();
            check(!renderer().presentationCurrentV2(), "invalidated concrete capture closes forwarding");
            window.coordinator.refreshEnvironment();
            check(renderer().presentationCurrentV2() && retained(window.coordinator) == retained,
                "fresh real capture restores exact retained presentation");
            packet("joined-environment", retained(window.coordinator), "exact retained packet after no-engine native refresh and concrete capture invalidation");
            // This is an actual software View.draw probe, not hardware/compositor screenshot acceptance.
            Bitmap bitmap = Bitmap.createBitmap(window.root.getWidth(), window.root.getHeight(), Bitmap.Config.ARGB_8888);
            try {
                window.root.draw(new Canvas(bitmap));
                check(bitmap.getPixel(0, 0) != 0, "actual current native root draws its canvas");
            } finally { bitmap.recycle(); }
        });
    }

    private void attachmentFault() {
        refresh();
        onMain(() -> {
            long handle = session();
            renderer().testFaultV2(0, false);
            UiPacket before = UiPacket.decode(retained(window.coordinator));
            UiPacket.Node task = before.nodes.get("task.2");
            boolean rejected = false;
            try { window.coordinator.dispatchInput(before.event(task.id, task.generation, "valueChange", true)); }
            catch (RuntimeException expected) { rejected = true; observations.add(Json.map("actualAttachmentFault", expected.toString())); }
            check(rejected && window.coordinator.isRetired() && !window.coordinator.hasCommittedPresentation(),
                "real native attachment exception retires joined owners");
            check(renderer().testRetiredV2() && !renderer().presentationCurrentV2(), "actual retired native gate remains closed");
            status("attachment-fault actual Swift session destroyed", NativeBridge.commitV2(handle, 1), 2);
        });
    }

    private void lifecycle() {
        // This is actual Activity destruction/relaunch with harness-owned disposal, not persistence restoration.
        CoordinatorJoinActivity old = window;
        onMain(old::finish);
        long deadline = SystemClock.uptimeMillis() + 8000;
        AtomicReference<Boolean> destroyed = new AtomicReference<>(false);
        do {
            waitForIdleSync();
            onMain(() -> destroyed.set(old.destroyed));
            if (destroyed.get()) break;
            SystemClock.sleep(20);
        } while (SystemClock.uptimeMillis() < deadline);
        check(destroyed.get(), "actual Activity onDestroy completed");
        window = launch();
        onMain(() -> {
            check(window != old && window.root != old.root, "real new Activity/window owner");
            window.coordinator = new NativeCoordinatorV2(window, window.root);
            window.coordinator.renderInitial();
            UiPacket initial = UiPacket.decode(retained(window.coordinator));
            check(initial.revision.equals("1") && !initial.nodes.get("task.1").flag("value", true),
                "new actual registry session starts fresh; no persistence claim");
            packet("joined-relaunched", retained(window.coordinator), "new real Activity and ordinary Swift session after previous Activity destruction");
            long oldHandle = session();
            window.coordinator.close();
            status("explicit lifecycle disposal destroys actual Swift session", NativeBridge.commitV2(oldHandle, 1), 2);
            check(renderer().testRetiredV2(), "explicit lifecycle disposal retires actual renderer");
            window.root.removeAllViews();
            window.coordinator = new NativeCoordinatorV2(window, window.root);
            window.coordinator.renderInitial();
        });
    }

    private void rejection() {
        refresh();
        onMain(() -> {
            long handle = session();
            boolean rejected = false;
            try { window.coordinator.dispatchInput(new byte[] {'!'}); }
            catch (RuntimeException expected) {
                rejected = expected.toString().contains("(status 4)");
                observations.add(Json.map("actualEngineRejection", expected.toString()));
            }
            check(rejected && window.coordinator.isRetired() && !window.coordinator.hasCommittedPresentation(),
                "actual ordinary engine rejection retires coordinator/presentation");
            status("rejected-input actual Swift session destroyed", NativeBridge.commitV2(handle, 1), 2);
            check(renderer().testRetiredV2() && !renderer().presentationCurrentV2(), "rejected-input actual native gate retired");
            boolean closed = false;
            try { window.coordinator.refreshEnvironment(); }
            catch (IllegalStateException expected) { closed = true; }
            check(closed, "retired coordinator rejects future operations");
        });
    }

    @Override public void onStart() {
        Bundle result = new Bundle();
        int resultCode = Activity.RESULT_CANCELED;
        String outcome = "failed";
        try {
            Map<String, Object> fixture = Json.object(Json.parse(asset("CoordinatorJoin/operations.json")));
            Json.keys(fixture, "format", "maximumChecks", "maximumOperations", "operations");
            maximumChecks = Integer.parseInt(Json.uint(fixture.get("maximumChecks")));
            if (maximumChecks < 1 || maximumChecks > 256) throw new AssertionError("fixture check budget");
            List<Object> steps = Json.array(fixture.get("operations"));
            check(Json.string(fixture.get("format")).equals("mixer-private-ordinary-coordinator-join-1")
                && Json.uint(fixture.get("maximumOperations")).equals("8")
                && steps.equals(List.of("jni", "initial", "toggle", "text", "environmentOnly", "attachmentFault", "lifecycle", "rejection")),
                "bounded exact native operations fixture");
            check(Build.VERSION.SDK_INT == 37 && Build.SUPPORTED_ABIS[0].equals("arm64-v8a"), "exact agreed API37 arm64 runtime");
            for (Object step : steps) {
                if (++operations > 8) throw new AssertionError("operation budget");
                switch (Json.string(step)) {
                    case "jni": jni(); break;
                    case "initial": initial(); break;
                    case "toggle": toggle(); break;
                    case "text": text(); break;
                    case "environmentOnly": environmentOnly(); break;
                    case "attachmentFault": attachmentFault(); break;
                    case "lifecycle": lifecycle(); break;
                    case "rejection": rejection(); break;
                    default: throw new AssertionError("unsupported operation");
                }
            }
            outcome = "passed";
            resultCode = Activity.RESULT_OK;
        } catch (RuntimeException | Error failure) {
            result.putString("failure", failure.toString());
            observations.add(Json.map("failure", failure.toString()));
        } finally {
            if (window != null) {
                try {
                    onMain(() -> {
                        try {
                            if (window.coordinator != null && !window.coordinator.isRetired()) window.coordinator.close();
                        } finally { window.finish(); }
                    });
                } catch (RuntimeException | Error failure) {
                    result.putString("cleanupFailure", failure.toString());
                    outcome = "failed";
                    resultCode = Activity.RESULT_CANCELED;
                }
            }
            result.putString("status", outcome);
            result.putInt("checks", checks);
            result.putInt("operations", operations);
            result.putString("scope", "actual private ordinary JNI/Swift/coordinator/native join; bounded subset only; no full native fault/IME/lifecycle/physical/public/signed/GA acceptance");
            write("native-results.json", new org.json.JSONObject(Json.map("status", outcome, "checks", checks, "operations", operations,
                "observations", observations, "packets", packets, "scope", result.getString("scope"))).toString().getBytes(StandardCharsets.UTF_8));
            finish(resultCode, result);
        }
    }
}
