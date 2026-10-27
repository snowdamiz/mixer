package dev.mixer.android;

import android.app.Activity;
import android.os.Handler;
import android.text.Editable;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.lang.reflect.Proxy;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;

/** Independently authored before access to the selected completion derivative.
 * Host invariants only. Reflective hostile states are explicitly distinguished
 * from ordinary synchronous coordinator paths. No production instrumentation.
 */
public final class SelectedIdentityMembershipReviewControls {
    private SelectedIdentityMembershipReviewControls() {}
    private static byte[] descriptor;
    private static int checks;
    private static final List<String> trace = new ArrayList<>();
    private static final class Fatal extends Error {
        private static final long serialVersionUID = 1L;
        Fatal(String message) { super(message); }
    }
    private static void check(boolean value, String message) {
        checks++;
        if (!value) throw new AssertionError(message + " trace=" + trace);
    }
    private static void note(String message) { if (trace.size() < 192) trace.add(message); }
    private static Field field(Object object, String name) {
        try { Field result = object.getClass().getDeclaredField(name); result.setAccessible(true); return result; }
        catch (ReflectiveOperationException failure) { throw new AssertionError("frozen-source binding required: " + name, failure); }
    }
    private static Object get(Object object, String name) {
        try { return field(object, name).get(object); }
        catch (IllegalAccessException failure) { throw new AssertionError(failure); }
    }
    private static void put(Object object, String name, Object value) {
        try { field(object, name).set(object, value); }
        catch (IllegalAccessException failure) { throw new AssertionError(failure); }
    }
    private static Object call(Object object, String name, Object... arguments) {
        for (Method method : object.getClass().getDeclaredMethods()) {
            if (!method.getName().equals(name) || method.getParameterCount() != arguments.length) continue;
            try { method.setAccessible(true); return method.invoke(object, arguments); }
            catch (InvocationTargetException failure) {
                if (failure.getCause() instanceof Error fatal) throw fatal;
                if (failure.getCause() instanceof RuntimeException ordinary) throw ordinary;
                throw new AssertionError(failure.getCause());
            } catch (ReflectiveOperationException failure) { throw new AssertionError(failure); }
        }
        throw new AssertionError("selected endpoint missing: " + name);
    }
    private static int count(NativeRenderer renderer) { return (Integer) get(renderer, "outstandingEditorNativeCalls"); }
    private static Object journal(Object candidate) { return get(candidate, "journal"); }
    private static Object pending(NativeRenderer renderer) { return get(renderer, "v2Pending"); }
    private static boolean frame(String name) {
        return ConcreteHostProbe.lastEvent().productionFrames.stream().anyMatch(site -> site.methodName().equals(name));
    }
    private static void write(StringBuilder output, Object value) {
        if (value instanceof List<?> values) {
            output.append('[');
            for (int index = 0; index < values.size(); index++) { if (index > 0) output.append(','); write(output, values.get(index)); }
            output.append(']');
        } else if (value instanceof Map<?, ?> values) {
            output.append('{'); boolean comma = false;
            for (var item : values.entrySet()) { if (comma) output.append(','); comma = true; Json.write(output, item.getKey()); output.append(':'); write(output, item.getValue()); }
            output.append('}');
        } else Json.write(output, value);
    }
    private static Object node(String id, String value) {
        return Json.map("id", id, "kind", "textField", "properties", Json.map("label", id, "value", value),
                "children", List.of(), "actions", List.of(Json.map("id", id + "Changed", "event", "textChange")));
    }
    private static byte[] packet(long revision, String b) {
        Object root = Json.map("id", "root", "kind", "vStack", "properties", Json.map(),
                "children", List.of(node("a", "hello"), node("b", b), node("c", "third")), "actions", List.of());
        StringBuilder result = new StringBuilder();
        write(result, Json.map("schemaVersion", new Json.Num("1"), "document", Json.map("schemaVersion", new Json.Num("1"),
                "revision", new Json.Num(Long.toString(revision)), "root", root), "identities", List.of(
                Json.map("id", "root", "generation", new Json.Num("1")), Json.map("id", "a", "generation", new Json.Num("2")),
                Json.map("id", "b", "generation", new Json.Num("3")), Json.map("id", "c", "generation", new Json.Num("4")))));
        return result.toString().getBytes(StandardCharsets.UTF_8);
    }
    private static final class Snapshot {
        final NativeAppearanceViewsV2.NativeField field;
        final Editable editable;
        final NativeAppearanceViewsV2.EditorSnapshot nativeSnapshot;
        final Object binding, geometry, predecessor, disposition;
        Snapshot(NativeAppearanceViewsV2.NativeField selected) {
            field = selected; editable = selected.getText(); nativeSnapshot = new NativeAppearanceViewsV2.EditorSnapshot(selected, editable);
            binding = selected.record.binding; geometry = selected.record.geometry; predecessor = get(selected, "attempt");
            disposition = predecessor == null ? null : get(predecessor, "close");
        }
        void unchanged(boolean oldPresentation) {
            check(field.getText() == editable && nativeSnapshot.same(field, editable), "exact post-close Editable/value/selection/composition snapshot");
            check(get(field, "attempt") == predecessor && (predecessor == null || get(predecessor, "close") == disposition), "settled predecessor disposition unchanged");
            if (oldPresentation) check(field.record.binding == binding && field.record.geometry == geometry, "old Binding and geometry restored by reference");
        }
    }
    private static final class Fixture implements AutoCloseable {
        final Activity activity;
        final FrameLayout root;
        final NativeOwnerV2 owner;
        final NativeCoordinatorV2 coordinator;
        final NativeRenderer renderer;
        final Handler queue;
        final NativeAppearanceViewsV2.NativeField a, b, c;
        final NativeOwnerV2.Fence fence;
        InputConnection oldA, oldC, liveB;
        BaseInputConnection targetA, targetC, targetB;
        Snapshot beforeA, beforeC;
        Fixture(boolean history, boolean connectB) {
            ConcreteHostProbe.reset(); NativeBridge.reset(); activity = new Activity(); root = new FrameLayout(activity);
            activity.assets.put(InstalledAppearanceV2.DESCRIPTOR, descriptor); root.layout(0, 0, 1000, 1500);
            activity.window.getDecorView().layout(0, 0, 1000, 1500); root.hostAttach(new Object()); NativeBridge.preparedPacket = packet(1, "other");
            owner = new NativeOwnerV2(activity, root); queue = (Handler) get(owner, "handler"); owner.onResume(); owner.start(); queue.drainAll(6);
            check(owner.hasCommittedPresentation(), "real owner/coordinator initial publication"); coordinator = (NativeCoordinatorV2) get(owner, "coordinator");
            renderer = (NativeRenderer) get(coordinator, "renderer"); fence = (NativeOwnerV2.Fence) get(owner, "fence");
            a = (NativeAppearanceViewsV2.NativeField) renderer.view("a"); b = (NativeAppearanceViewsV2.NativeField) renderer.view("b"); c = (NativeAppearanceViewsV2.NativeField) renderer.view("c");
            if (history) {
                a.requestFocus(); oldA = a.onCreateInputConnection(new EditorInfo()); check(oldA != null && oldA.setSelection(1, 3) && oldA.setComposingRegion(0, 2), "A native selection and composition before legitimate blur");
                targetA = (BaseInputConnection) a.lastConnection; a.clearFocus();
                c.requestFocus(); oldC = c.onCreateInputConnection(new EditorInfo()); check(oldC != null && oldC.setSelection(2, 4) && oldC.setComposingRegion(1, 3), "C distinct native selection and composition before legitimate blur");
                targetC = (BaseInputConnection) c.lastConnection; c.clearFocus();
                check(targetA.closeCalls == 1 && targetC.closeCalls == 1, "each original target settled once");
                // Snapshot the real post-close state; do not fabricate retained composition.
                beforeA = new Snapshot(a); beforeC = new Snapshot(c);
            }
            b.requestFocus();
            if (connectB) { liveB = b.onCreateInputConnection(new EditorInfo()); check(liveB != null, "B original focused adapter"); targetB = (BaseInputConnection) b.lastConnection; check(liveB.setSelection(5, 5), "B explicit end cursor"); }
            check(count(renderer) == 0, "fixture has no entered native custody outside calls"); ConcreteHostProbe.reset();
        }
        boolean edit() { NativeBridge.preparedPacket = packet(2, "otherz"); return liveB.commitText("z", 1); }
        void refresh() { root.layout(0, 0, 1001, 1501); queue.drainAll(8); }
        @Override public void close() {
            ConcreteHostProbe.hook = null;
            try { owner.close(); queue.drainAll(8); } catch (RuntimeException | Error expected) { /* asserted before disposal */ }
            ConcreteHostProbe.reset();
        }
    }
    /** Captures all declared scalar/reference fields, plus exact hook membership.
     * Used for foreign/replay refusal assertions; no semantic field-name filter.
     */
    private static final class ObjectState {
        final IdentityHashMap<Object, Map<Field, Object>> objects = new IdentityHashMap<>();
        final IdentityHashMap<Object, Object[]> hooks = new IdentityHashMap<>();
        ObjectState(Object... selected) { for (Object object : selected) add(object); }
        void add(Object object) {
            if (object == null || objects.containsKey(object)) return;
            Map<Field, Object> values = new java.util.LinkedHashMap<>();
            for (Field selected : object.getClass().getDeclaredFields()) if (!Modifier.isStatic(selected.getModifiers())) {
                try { selected.setAccessible(true); values.put(selected, selected.get(object)); }
                catch (IllegalAccessException failure) { throw new AssertionError(failure); }
            }
            objects.put(object, values);
            if (object instanceof NativeAppearanceViewsV2.FieldPreservation scope) hooks.put(scope, scope.hooks.toArray());
        }
        void unchanged() {
            for (var object : objects.entrySet()) for (var value : object.getValue().entrySet()) {
                Object actual;
                try { actual = value.getKey().get(object.getKey()); } catch (IllegalAccessException failure) { throw new AssertionError(failure); }
                check(value.getKey().getType().isPrimitive() ? value.getValue().equals(actual) : value.getValue() == actual,
                        "refusal preserves exact field " + object.getKey().getClass().getSimpleName() + "." + value.getKey().getName());
            }
            for (var item : hooks.entrySet()) check(Arrays.equals(((NativeAppearanceViewsV2.FieldPreservation) item.getKey()).hooks.toArray(), item.getValue()), "refusal preserves exact hook stack");
        }
    }
    private static void refusedWithoutEffects(Runnable action, Object... objects) {
        ObjectState state = new ObjectState(objects); int effects = ConcreteHostProbe.events().size(); boolean refused = false;
        try { action.run(); } catch (IllegalArgumentException | IllegalStateException expected) { refused = true; }
        check(refused, "foreign or consumed endpoint refuses"); state.unchanged();
        check(ConcreteHostProbe.events().size() == effects, "refusal precedes native/platform effects");
    }
    private static final class Cohort {
        final Fixture fixture;
        final NativeAppearanceViewsV2.FieldPreservation[] scopes = new NativeAppearanceViewsV2.FieldPreservation[2];
        Object candidate, journal, lease;
        boolean forward, commit, afterFinish;
        int commitReturns, intervalPlatformCalls, restores;
        Cohort(Fixture fixture) { this.fixture = fixture; }
        void observe(String method, String phase) {
            var event = ConcreteHostProbe.lastEvent();
            if (!forward && event.receiver == fixture.a && method.equals("View.invalidate") && phase.equals("entry") && fixture.a.record.fieldPreservation != null) {
                forward = true; scopes[0] = fixture.a.record.fieldPreservation; scopes[1] = fixture.c.record.fieldPreservation;
                check(scopes[1] != null && scopes[0] != scopes[1], "two distinct exact inactive preservation scopes");
                candidate = scopes[0].candidate; journal = journal(candidate); lease = fixture.b.record.editorCallbackLease;
                check(scopes[1].candidate == candidate && scopes[0].original == scopes[1].original && get(candidate, "originalMutation") == scopes[0].original,
                        "same immutable candidate/journal and identical original transaction object");
                check(scopes[0].original.token == fixture.fence.operation && scopes[0].original.fence == fixture.fence, "captured original token/fence");
                int expected = lease == null ? 2 : 3; check(count(fixture.renderer) == expected, "actual two holds plus distinct existing B lease");
                check(scopes[0].entered && scopes[0].counted && !scopes[0].ended && scopes[1].entered && scopes[1].counted && !scopes[1].ended, "both scopes entered atomically before forward work");
                refusedWithoutEffects(() -> fixture.a.record.input.fieldPreservationBegin(fixture.a.record, scopes[0]), fixture.renderer, candidate, journal, scopes[0], scopes[1], fixture.a.record, fixture.c.record);
                refusedWithoutEffects(() -> fixture.a.record.input.fieldPreservationEnd(fixture.c.record, scopes[0]), fixture.renderer, candidate, journal, scopes[0], scopes[1], fixture.a.record, fixture.c.record);
                note("forward count=" + count(fixture.renderer));
            }
            if (forward && frame("restoreV2")) {
                restores++; check(fixture.a.record.fieldPreservation == scopes[0] && fixture.c.record.fieldPreservation == scopes[1], "restoration uses original two unended scope registrations");
                check(scopes[0].original == get(candidate, "originalMutation") && count(fixture.renderer) >= 2, "restoration uses identical original while holds retained");
            }
            if (method.equals("NativeBridge.commitV2") && phase.equals("entry")) {
                commit = true; check(forward && count(fixture.renderer) == 3 && fixture.b.record.editorCallbackLease == lease, "count3 through real engine commit");
                check(!scopes[0].ended && !scopes[1].ended && scopes[0].counted && scopes[1].counted, "attach return does not consume restoration authority");
                note("commit count3");
            }
            if (commitReturns > 0 && fixture.fence.commitFinish && !method.equals("NativeBridge.commitV2")) intervalPlatformCalls++;
            if (method.equals("NativeBridge.commitV2") && phase.equals("beforeReturn")) commitReturns++;
            if (forward && !afterFinish && !fixture.fence.commitFinish && (Boolean) get(candidate, "used") && (Boolean) get(journal, "complete") && NativeBridge.commitStatus == 0 && NativeBridge.commitFailure == null) {
                afterFinish = true;
                int expected = lease == null ? 0 : 1;
                check(count(fixture.renderer) == expected && (lease == null || fixture.b.record.editorCallbackLease == lease), "scalar finish leaves only exact existing B lease");
                check(scopes[0].ended && scopes[1].ended && !scopes[0].counted && !scopes[1].counted && fixture.a.record.fieldPreservation == null && fixture.c.record.fieldPreservation == null,
                        "success releases each exact preservation count and callback registration");
                note("after finish count=" + expected);
            }
        }
        void balanced(boolean oldPresentation) {
            check(forward && count(fixture.renderer) == 0, "existing B unwind reaches count0");
            check(scopes[0].ended && scopes[1].ended && !scopes[0].counted && !scopes[1].counted, "both exact held claims released once");
            check(fixture.a.record.fieldPreservation == null && fixture.c.record.fieldPreservation == null, "no surviving callback authority");
            check(intervalPlatformCalls == 0, "no host platform/native probe between commit return and scalar finish");
            fixture.beforeA.unchanged(oldPresentation); fixture.beforeC.unchanged(oldPresentation);
            check(fixture.targetA.closeCalls == 1 && fixture.targetC.closeCalls == 1, "no repeated predecessor close");
            int effects = ConcreteHostProbe.events().size();
            check(!fixture.oldA.beginBatchEdit() && !fixture.oldC.beginBatchEdit() && fixture.a.onCreateInputConnection(new EditorInfo()) == null && fixture.c.onCreateInputConnection(new EditorInfo()) == null,
                    "inactive field preservation does not revive old adapters or unfocused creators");
            check(ConcreteHostProbe.events().size() == effects, "old adapters refuse before native calls");
            note("outer unwind count0");
        }
    }
    private static void success() {
        try (Fixture fixture = new Fixture(true, true)) {
            Cohort cohort = new Cohort(fixture); ConcreteHostProbe.hook = cohort::observe;
            check(fixture.edit(), "B ordinary compatible edit succeeds"); ConcreteHostProbe.hook = null;
            check(cohort.commit && cohort.afterFinish && !fixture.fence.terminal, "real healthy commit/finish observed"); cohort.balanced(false);
            refusedWithoutEffects(() -> call(fixture.renderer, "finishV2", cohort.candidate, cohort.journal), fixture.renderer, cohort.candidate, cohort.journal, cohort.scopes[0], cohort.scopes[1], fixture.a.record, fixture.c.record);
            refusedWithoutEffects(() -> call(fixture.renderer, "completeFailedV2", cohort.candidate, null, null), fixture.renderer, cohort.candidate, cohort.journal, cohort.scopes[0], cohort.scopes[1], fixture.a.record, fixture.c.record);
        }
    }
    private static void knownRejections() {
        for (int status : new int[] {1, 3, 4, 5, 6, 7}) try (Fixture fixture = new Fixture(true, true)) {
            Cohort cohort = new Cohort(fixture); NativeBridge.commitStatus = status; ConcreteHostProbe.hook = cohort::observe;
            boolean result = false; try { result = fixture.edit(); } catch (RuntimeException expected) { note("known status" + status + " " + expected.getClass().getSimpleName()); }
            ConcreteHostProbe.hook = null;
            check(!result && cohort.commit && fixture.coordinator.cleanupLedger().abort() == NativeCoordinatorV2.Outcome.RETURNED && fixture.coordinator.cleanupLedger().rollback() == NativeCoordinatorV2.Outcome.RETURNED,
                    "known rejection/abort0 real coordinator restoration returns for status" + status);
            check(cohort.restores > 0, "real native restoration path visited under original scopes"); cohort.balanced(true);
            refusedWithoutEffects(() -> call(fixture.renderer, "completeFailedV2", cohort.candidate, null, null), fixture.renderer, cohort.candidate, cohort.journal, cohort.scopes[0], cohort.scopes[1], fixture.a.record, fixture.c.record);
        }
    }
    private static void outcomeFailures() {
        for (String mode : new String[] {"terminal2", "unknown8", "commit-ordinary", "commit-fatal", "abort-nonzero", "abort-ordinary", "abort-fatal"}) try (Fixture fixture = new Fixture(true, true)) {
            Cohort cohort = new Cohort(fixture); Fatal fatal = new Fatal(mode);
            switch (mode) {
                case "terminal2" -> NativeBridge.commitStatus = 2;
                case "unknown8" -> NativeBridge.commitStatus = 8;
                case "commit-ordinary" -> NativeBridge.commitFailure = new IllegalStateException(mode);
                case "commit-fatal" -> NativeBridge.commitFailure = fatal;
                case "abort-nonzero" -> { NativeBridge.commitStatus = 1; NativeBridge.abortStatus = 1; }
                case "abort-ordinary" -> { NativeBridge.commitStatus = 1; NativeBridge.abortFailure = new IllegalStateException(mode); }
                default -> { NativeBridge.commitStatus = 1; NativeBridge.abortFailure = fatal; }
            }
            ConcreteHostProbe.hook = cohort::observe; Throwable escaped = null; boolean result = false;
            try { result = fixture.edit(); } catch (RuntimeException | Error expected) { escaped = expected; } ConcreteHostProbe.hook = null;
            check(!result && cohort.commit && fixture.fence.terminal && cohort.restores == 0, "terminal/unknown/abort uncertainty never obtains restoration: " + mode);
            if (mode.endsWith("fatal")) check(escaped == fatal, "actual original fatal is surfaced by identity");
            cohort.balanced(false);
        }
    }
    private static void refresh() {
        try (Fixture fixture = new Fixture(true, false)) {
            Cohort cohort = new Cohort(fixture); int commits = NativeBridge.commitCalls; ConcreteHostProbe.hook = cohort::observe;
            fixture.refresh(); ConcreteHostProbe.hook = null;
            // Refresh can return without another instrumented native call after finish.
            // Observe its scalar result directly outside the transaction interval.
            if (cohort.forward && !cohort.afterFinish && get(cohort.journal, "completion").equals(2)) {
                cohort.afterFinish = true;
                check(count(fixture.renderer) == 0 && cohort.scopes[0].ended && cohort.scopes[1].ended &&
                        cohort.scopes[0].released && cohort.scopes[1].released && !cohort.scopes[0].counted && !cohort.scopes[1].counted &&
                        fixture.a.record.fieldPreservation == null && fixture.c.record.fieldPreservation == null,
                        "refresh scalar completion releases both exact holds without needing a native observation callback");
                note("outer refresh scalar finish count0");
            }
            check(cohort.forward && !cohort.commit && cohort.afterFinish && NativeBridge.commitCalls == commits && !fixture.fence.terminal, "real owner refresh uses zero-count Begin and count2 scalar completion without engine commit");
            cohort.balanced(false);
        }
    }
    private static void noScope() {
        for (String mode : new String[] {"success", "refresh", "known-rejection", "unknown"}) try (Fixture fixture = new Fixture(false, true)) {
            Object[] candidate = {null}; ConcreteHostProbe.hook = (method, phase) -> { Object current = pending(fixture.renderer); if (current != null) candidate[0] = current; };
            if (mode.equals("refresh")) fixture.refresh();
            else { if (mode.equals("known-rejection")) NativeBridge.commitStatus = 1; if (mode.equals("unknown")) NativeBridge.commitStatus = 8; try { fixture.edit(); } catch (RuntimeException expected) { note("no-scope " + mode); } }
            ConcreteHostProbe.hook = null; check(candidate[0] != null && count(fixture.renderer) == 0, "actual candidate with native states and no preservation holds: " + mode);
            for (Object state : (List<?>) get(journal(candidate[0]), "previous")) check(get(state, "preservation") == null, "no field scope is fabricated");
            check(fixture.a.record.fieldPreservation == null && fixture.c.record.fieldPreservation == null && get(fixture.a, "primary") == null && get(fixture.c, "primary") == null, "no invented inactive native-prefix failure");
            refusedWithoutEffects(() -> call(fixture.renderer, "completeFailedV2", candidate[0], null, null), fixture.renderer, candidate[0], journal(candidate[0]), fixture.a.record, fixture.c.record);
        }
    }
    private static void preAttachNoOriginal() {
        try (Fixture fixture = new Fixture(true, true)) {
            Object[] candidate = {null}; boolean[] injected = {false}; Fatal original = new Fatal("before attach original capture");
            ConcreteHostProbe.hook = (method, phase) -> {
                Object current = pending(fixture.renderer);
                if (!injected[0] && current != null && get(current, "originalMutation") == null && frame("current") && frame("transact")) {
                    injected[0] = true; candidate[0] = current; check(count(fixture.renderer) == 1, "pre-attach only existing B count"); throw original;
                }
            };
            Throwable escaped = null; try { fixture.edit(); } catch (RuntimeException | Error expected) { escaped = expected; } ConcreteHostProbe.hook = null;
            check(injected[0] && escaped == original && count(fixture.renderer) == 0, "pre-attach failure preserves actual fatal and fabricates no held count");
            check(get(candidate[0], "originalMutation") == null && get(fixture.a, "primary") == null && get(fixture.c, "primary") == null, "no original Mutation/scope/native error fabricated");
            for (Object state : (List<?>) get(journal(candidate[0]), "previous")) check(get(state, "preservation") == null, "pre-attach journal has no preservation");
            refusedWithoutEffects(() -> call(fixture.renderer, "completeFailedV2", candidate[0], original, original), fixture.renderer, candidate[0], journal(candidate[0]), fixture.a.record, fixture.c.record);
        }
    }
    /** A test-only Input interceptor is installed at an existing pre-Begin native
     * snapshot boundary. It restores the exact original Input before invoking
     * real Begin; no product endpoint receives proxy ownership.
     */
    private static void entryRefusal(String selected, boolean constructorFailure) {
        try (Fixture fixture = new Fixture(true, true)) {
            NativeAppearanceViewsV2.NativeField selectedField = selected.equals("a") ? fixture.a : fixture.c;
            NativeAppearanceViewsV2.Input exactInput = selectedField.record.input;
            Object[] candidate = {null}; NativeAppearanceViewsV2.FieldPreservation[] scope = {null}; boolean[] installed = {false}, refused = {false};
            IllegalStateException original = new IllegalStateException(constructorFailure ? "constructor before registration" : "actual Begin refusal before entered/count publication");
            ConcreteHostProbe.hook = (method, phase) -> {
                var event = ConcreteHostProbe.lastEvent();
                if (installed[0] || event.receiver != selectedField || !frame("beginFieldPreservationsV2") || !frame("sameNativeBaseV2")) return;
                installed[0] = true; candidate[0] = pending(fixture.renderer);
                Object proxy = Proxy.newProxyInstance(NativeAppearanceViewsV2.Input.class.getClassLoader(), new Class<?>[] {NativeAppearanceViewsV2.Input.class}, (receiver, invoked, arguments) -> {
                    if (constructorFailure && invoked.getName().equals("editorLossObservation")) { put(selectedField.record, "input", exactInput); refused[0] = true; throw original; }
                    if (invoked.getName().equals("fieldPreservationBegin")) {
                        put(selectedField.record, "input", exactInput); scope[0] = (NativeAppearanceViewsV2.FieldPreservation) arguments[1];
                        OwnerLifecycleV2.Token operation = fixture.fence.operation; fixture.fence.operation = null;
                        try { exactInput.fieldPreservationBegin(selectedField.record, scope[0]); throw new AssertionError("Begin ignored actual current-token refusal"); }
                        catch (IllegalArgumentException | IllegalStateException expected) { refused[0] = true; check(!scope[0].entered && !scope[0].counted, "refused Begin acquired no scope count"); }
                        finally { fixture.fence.operation = operation; }
                        throw original;
                    }
                    try { return invoked.invoke(exactInput, arguments); }
                    catch (InvocationTargetException failure) { throw failure.getCause(); }
                });
                put(selectedField.record, "input", proxy);
            };
            try { fixture.edit(); } catch (RuntimeException | Error expected) { note("entry rejection " + selected + " " + expected.getClass().getSimpleName()); }
            finally { ConcreteHostProbe.hook = null; put(selectedField.record, "input", exactInput); }
            check(installed[0] && refused[0] && candidate[0] != null && count(fixture.renderer) == 0, "actual partial attach uses candidate journal despite no returned journal");
            if (constructorFailure) check(scope[0] == null && selectedField.record.fieldPreservation == null, "failed constructor published no field registration");
            else check(scope[0] != null && scope[0].ended && !scope[0].entered && !scope[0].counted && selectedField.record.fieldPreservation == null, "CAPTURED registration cleanup ends unentered scope without decrement");
            check(get(selectedField, "primary") == null && get(selectedField, "firstFatal") == null, "unentered field has no invented native-prefix failure");
            if (selected.equals("c")) {
                NativeAppearanceViewsV2.FieldPreservation entered = null;
                for (Object state : (List<?>) get(journal(candidate[0]), "previous")) if (get(state, "record") == fixture.a.record) entered = (NativeAppearanceViewsV2.FieldPreservation) get(state, "preservation");
                check(entered != null && entered.entered && entered.ended && !entered.counted, "earlier exact A count releases when later C Begin refuses");
            }
        }
    }
    private static void malformedCustody() {
        for (String mode : new String[] {"callback", "hook", "checking", "counted-not-entered", "entered-not-counted", "underfunded"}) try (Fixture fixture = new Fixture(true, true)) {
            Cohort cohort = new Cohort(fixture); boolean[] changed = {false};
            ConcreteHostProbe.hook = (method, phase) -> {
                cohort.observe(method, phase);
                if (!changed[0] && cohort.commit && method.equals("NativeBridge.commitV2") && phase.equals("beforeReturn")) {
                    changed[0] = true; var scope = cohort.scopes[0];
                    switch (mode) {
                        case "callback" -> scope.callbacks++;
                        case "hook" -> scope.hooks.push("hostile-unbalanced");
                        case "checking" -> scope.checking = true;
                        case "counted-not-entered" -> scope.entered = false;
                        case "entered-not-counted" -> scope.counted = false;
                        default -> put(fixture.renderer, "outstandingEditorNativeCalls", 1);
                    }
                    note("synthetic invariant " + mode);
                }
            };
            boolean result = false; try { result = fixture.edit(); } catch (RuntimeException | Error expected) { note("malformed escaped " + expected.getClass().getSimpleName()); } ConcreteHostProbe.hook = null;
            check(changed[0] && !result && fixture.fence.terminal && fixture.renderer.editorDisposalBusyV2() && NativeBridge.destroyCalls == 0, "malformed exact custody remains terminally busy: " + mode);
            check(fixture.a.record.fieldPreservation == null && fixture.c.record.fieldPreservation == null, "failed completion removes exact callback registrations");
            if (!mode.equals("underfunded")) check(!cohort.scopes[1].counted, "other exact balanced C scope releases despite A imbalance");
            else check(cohort.scopes[0].counted && cohort.scopes[1].counted, "underfunded aggregate cannot fund either represented preservation hold");
            refusedWithoutEffects(() -> call(fixture.renderer, "completeFailedV2", cohort.candidate, null, null), fixture.renderer, cohort.candidate, cohort.journal, cohort.scopes[0], cohort.scopes[1], fixture.a.record, fixture.c.record);
            // No synthetic repair: deliberately retained custody lives until this bounded host JVM exits.
        }
    }
    private static void fatalChronology() {
        try (Fixture fixture = new Fixture(true, true)) {
            Cohort cohort = new Cohort(fixture); Fatal first = new Fatal("F first native"), laterRestore = new Fatal("G later restore"), laterAbort = new Fatal("H later abort");
            boolean[] f = {false}, g = {false}, h = {false}; NativeBridge.abortFailure = laterAbort;
            ConcreteHostProbe.hook = (method, phase) -> {
                cohort.observe(method, phase); var event = ConcreteHostProbe.lastEvent();
                if (!f[0] && cohort.forward && event.receiver == fixture.a && method.equals("View.invalidate") && phase.equals("entry") && !frame("restoreV2")) {
                    f[0] = true; check(count(fixture.renderer) == 3, "F observed with all real custody held"); note("F"); throw first;
                }
                if (f[0] && !g[0] && event.receiver == fixture.c && frame("restoreV2")) { g[0] = true; check(count(fixture.renderer) == 3, "G restoration/reporting still holds all custody"); note("G"); throw laterRestore; }
                if (method.equals("NativeBridge.abortV2") && phase.equals("entry")) { h[0] = true; check(f[0] && g[0] && count(fixture.renderer) == 3, "H occurs after F then G while held"); note("H"); }
            };
            Throwable escaped = null; try { fixture.edit(); } catch (RuntimeException | Error expected) { escaped = expected; } ConcreteHostProbe.hook = null;
            check(f[0] && g[0] && h[0] && escaped == first, "actual chronological F survives G then H by identity");
            check(!cohort.scopes[0].counted && !cohort.scopes[1].counted && count(fixture.renderer) == 0, "every eligible balanced hold releases before first fatal surfaces");
            check(fixture.coordinator.cleanupLedger().firstFatal() == first && fixture.coordinator.cleanupLedger().abortFailure() == laterAbort, "coordinator keeps F while observing H abort failure");
        }
    }
    private static void foreignReplay() {
        try (Fixture foreign = new Fixture(true, true)) {
            Cohort foreignCohort = new Cohort(foreign); boolean[] corrupt = {false};
            ConcreteHostProbe.hook = (method, phase) -> {
                foreignCohort.observe(method, phase);
                if (!corrupt[0] && foreignCohort.commit && method.equals("NativeBridge.commitV2") && phase.equals("beforeReturn")) {
                    corrupt[0] = true; foreignCohort.scopes[0].callbacks++;
                }
            };
            try { foreign.edit(); } catch (RuntimeException | Error expected) { note("real foreign retained hold " + expected.getClass().getSimpleName()); }
            ConcreteHostProbe.hook = null;
            var retained = foreignCohort.scopes[0];
            check(corrupt[0] && retained.ended && retained.counted && count(foreign.renderer) == 1, "real foreign ended-but-countHeld native scope");
            // Match FH-C02's internal invariant setup. Clearing the deliberately
            // injected callback imbalance grants no new target/native authority.
            retained.callbacks = 0;
            try (Fixture local = new Fixture(true, true)) {
                Cohort localCohort = new Cohort(local); boolean[] attempted = {false};
                ConcreteHostProbe.hook = (method, phase) -> {
                    localCohort.observe(method, phase);
                    if (attempted[0] || !localCohort.forward) return;
                    attempted[0] = true;
                    Object[] states = {foreign.renderer, foreignCohort.candidate, foreignCohort.journal, retained, foreign.a.record, foreign.c.record,
                            local.renderer, localCohort.candidate, localCohort.journal, localCohort.scopes[0], localCohort.scopes[1], local.a.record, local.c.record};
                    refusedWithoutEffects(() -> local.a.record.input.fieldPreservationEnd(foreign.a.record, retained), states);
                    refusedWithoutEffects(() -> local.a.record.input.fieldPreservationBegin(foreign.a.record, retained), states);
                    refusedWithoutEffects(() -> foreign.a.record.input.fieldPreservationEnd(local.a.record, localCohort.scopes[0]), states);
                    refusedWithoutEffects(() -> call(local.renderer, "finishV2", foreignCohort.candidate, foreignCohort.journal), states);
                    refusedWithoutEffects(() -> call(local.renderer, "finishV2", localCohort.candidate, foreignCohort.journal), states);
                    refusedWithoutEffects(() -> call(local.renderer, "completeFailedV2", foreignCohort.candidate, null, null), states);
                    check(count(foreign.renderer) == 1 && retained.counted && count(local.renderer) == 3, "neither owner lends its actual held count");
                };
                check(local.edit(), "local real compatible edit survives foreign endpoint refusals"); ConcreteHostProbe.hook = null;
                check(attempted[0], "real local cohort exercised every foreign endpoint"); localCohort.balanced(false);
                check(foreign.renderer.editorDisposalBusyV2() && count(foreign.renderer) == 1 && retained.counted, "foreign retained custody remains independent after local unwind");
            }
        }
    }
    private static void fixtureSmoke() {
        try (Fixture fixture = new Fixture(true, true)) {
            fixture.beforeA.unchanged(true); fixture.beforeC.unchanged(true);
            check(fixture.targetA.closeCalls == 1 && fixture.targetC.closeCalls == 1 && fixture.targetB.closeCalls == 0 && !fixture.fence.terminal, "old-source-only real three-field fixture is healthy");
        }
    }
    private static void progressStates() {
        for (boolean partialRelease : new boolean[] {false, true}) try (Fixture fixture = new Fixture(true, true)) {
            Cohort cohort = new Cohort(fixture); boolean[] constructed = {false}; ObjectState[] alreadyReleased = {null};
            ConcreteHostProbe.hook = (method, phase) -> {
                cohort.observe(method, phase);
                if (!constructed[0] && cohort.commit && method.equals("NativeBridge.commitV2") && phase.equals("beforeReturn")) {
                    constructed[0] = true; cohort.afterFinish = true; // Disable success-only test observer for this hostile state.
                    check(!(Boolean) get(cohort.journal, "failedInvoked"), "success preclaim has not consumed failed-endpoint invocation");
                    put(cohort.journal, "completion", 1); // actual SUCCESS_IN_PROGRESS
                    put(cohort.journal, "complete", true); put(cohort.candidate, "used", true); put(fixture.renderer, "v2Pending", null);
                    if (partialRelease) {
                        var released = cohort.scopes[0]; released.record.fieldPreservation = null; released.ended = true;
                        released.counted = false; released.released = true; released.phase = NativeAppearanceViewsV2.FieldPreservation.COMMITTED;
                        put(cohort.candidate, "heldPreservations", 1); put(fixture.renderer, "outstandingFieldPreservations", 1);
                        put(fixture.renderer, "outstandingEditorNativeCalls", 2); alreadyReleased[0] = new ObjectState(released);
                    }
                    note("hostile success-progress partialRelease=" + partialRelease);
                    throw new IllegalStateException("test-only partial scalar progress state; no asynchronous recovery claim");
                }
            };
            try { fixture.edit(); } catch (RuntimeException expected) { note("hostile progress transported through ordinary outer catch"); } ConcreteHostProbe.hook = null;
            check(constructed[0] && (Boolean) get(cohort.journal, "failedInvoked") && get(cohort.journal, "completion").equals(4), "first failed invocation completes despite success progress and used/complete flags");
            check(!cohort.scopes[0].counted && !cohort.scopes[1].counted && cohort.scopes[0].released && cohort.scopes[1].released &&
                    count(fixture.renderer) == 0 && get(fixture.renderer, "outstandingFieldPreservations").equals(0) && get(cohort.candidate, "heldPreservations").equals(0), "release remaining exact holds once across all three counts");
            if (alreadyReleased[0] != null) alreadyReleased[0].unchanged();
            refusedWithoutEffects(() -> call(fixture.renderer, "completeFailedV2", cohort.candidate, null, null), fixture.renderer, fixture.fence, cohort.candidate, cohort.journal, cohort.scopes[0], cohort.scopes[1], fixture.a.record, fixture.c.record);
        }
    }
    private static void cohortPreflight() {
        for (boolean imbalance : new boolean[] {false, true}) try (Fixture fixture = new Fixture(true, true)) {
            Cohort cohort = new Cohort(fixture); boolean[] injected = {false}, report = {false};
            Object observer = get(fixture.renderer, "v2Environment");
            NativeEnvironmentV2.Sink original = (NativeEnvironmentV2.Sink) get(observer, "sink");
            NativeEnvironmentV2.Sink checked = (source, change, cause, primary, firstFatal) -> {
                if (injected[0] && !report[0]) {
                    report[0] = true;
                    check(count(fixture.renderer) == 3 && !cohort.scopes[0].ended && !cohort.scopes[1].ended && cohort.scopes[0].counted && cohort.scopes[1].counted,
                            "whole-cohort refusal precedes ending or releasing either A or C");
                    check(fixture.a.record.fieldPreservation == cohort.scopes[0] && fixture.c.record.fieldPreservation == cohort.scopes[1] &&
                            !(Boolean) get(cohort.candidate, "used") && !(Boolean) get(cohort.journal, "complete") &&
                            get(cohort.journal, "completion").equals(0) && !(Boolean) get(cohort.journal, "failedInvoked"), "whole preflight leaves callback and candidate/journal success state untouched");
                    check(get(fixture.renderer, "packet") == get(cohort.candidate, "base") && get(fixture.renderer, "v2Records") == get(cohort.candidate, "baseRecords"), "no prepared presentation/reference swap precedes cohort refusal");
                    note("preflight refusal observed before cleanup reporter under count3");
                }
                original.changed(source, change, cause, primary, firstFatal);
            };
            put(observer, "sink", checked);
            ConcreteHostProbe.hook = (method, phase) -> {
                cohort.observe(method, phase);
                if (!injected[0] && cohort.commit && method.equals("NativeBridge.commitV2") && phase.equals("beforeReturn")) {
                    injected[0] = true;
                    if (imbalance) cohort.scopes[1].callbacks = 1;
                    else cohort.scopes[1].phase = NativeAppearanceViewsV2.FieldPreservation.ATTACHED;
                }
            };
            boolean returned = false; try { returned = fixture.edit(); } catch (RuntimeException expected) { note("scalar preflight ordinary failure"); } ConcreteHostProbe.hook = null;
            check(injected[0] && report[0] && !returned && fixture.fence.terminal, "whole-cohort supported refusal reaches actual deferred report");
            check((Boolean) get(cohort.journal, "failedInvoked") && !cohort.scopes[0].counted && cohort.scopes[0].released, "failure endpoint remained available and released exact balanced A");
            check(count(fixture.renderer) == (imbalance ? 1 : 0) && cohort.scopes[1].counted == imbalance, "C custody follows its independent balance; original B unwinds once");
            if (imbalance) check(fixture.renderer.editorDisposalBusyV2() && NativeBridge.destroyCalls == 0, "retained C imbalance prevents disposal");
            put(observer, "sink", original);
        }
    }
    private static Object nativeState(Object journal, NativeAppearanceViewsV2.Record record) {
        for (Object state : (Object[]) get(journal, "states")) if (get(state, "record") == record) return state;
        throw new AssertionError("exact native state absent");
    }
    private static void identityMatrix() {
        try (Fixture other = new Fixture(true, true); Fixture fixture = new Fixture(true, true)) {
            Cohort foreign = new Cohort(other); ConcreteHostProbe.hook = foreign::observe; check(other.edit(), "foreign actual completed cohort"); ConcreteHostProbe.hook = null;
            Cohort cohort = new Cohort(fixture); boolean[] nativePhase = {false}, finishPhase = {false};
            ConcreteHostProbe.hook = (method, phase) -> {
                cohort.observe(method, phase);
                boolean finishing = cohort.commit && method.equals("NativeBridge.commitV2") && phase.equals("entry");
                if (!cohort.forward || (finishing ? finishPhase[0] : nativePhase[0]) || (!finishing && !method.equals("View.invalidate"))) return;
                if (finishing) finishPhase[0] = true; else nativePhase[0] = true;
                var scope = cohort.scopes[0]; NativeAppearanceViewsV2.Input exactInput = fixture.a.record.input;
                Object state = nativeState(cohort.journal, fixture.a.record);
                var equalOriginal = NativeAppearanceViewsV2.Mutation.transaction(fixture.fence, fixture.fence.operation);
                for (String identity : new String[] {"renderer", "candidate", "journal", "record", "view", "input", "original-equal-token", "scope-original", "fence", "token", "membership"}) {
                    Object target, wrong; String member;
                    switch (identity) {
                        case "renderer" -> { target = scope; member = "renderer"; wrong = other.renderer; }
                        case "candidate" -> { target = scope; member = "candidate"; wrong = foreign.candidate; }
                        case "journal" -> { target = scope; member = "journal"; wrong = foreign.journal; }
                        case "record" -> { target = scope; member = "record"; wrong = fixture.c.record; }
                        case "view" -> { target = fixture.a.record; member = "view"; wrong = fixture.c; }
                        case "input" -> { target = fixture.a.record; member = "input"; wrong = other.a.record.input; }
                        case "original-equal-token" -> { target = cohort.candidate; member = "originalMutation"; wrong = equalOriginal; }
                        case "scope-original" -> { target = scope; member = "original"; wrong = equalOriginal; }
                        case "fence" -> { target = scope.original; member = "fence"; wrong = other.fence; }
                        case "token" -> { target = scope.original; member = "token"; wrong = foreign.scopes[0].original.token; }
                        case "membership" -> { target = state; member = "preservation"; wrong = cohort.scopes[1]; }
                        default -> { target = state; member = "forwardPreserved"; wrong = false; }
                    }
                    Object previous = get(target, member); put(target, member, wrong);
                    Object[] snapshot = {fixture.renderer, fixture.fence, cohort.candidate, cohort.journal, cohort.scopes[0], cohort.scopes[1], fixture.a.record, fixture.c.record,
                            state, scope.original, fixture.renderer.cleanupLedger(), other.renderer, other.fence, foreign.candidate, foreign.journal, foreign.scopes[0], foreign.scopes[1], other.a.record, other.c.record};
                    try {
                        if (finishing) refusedWithoutEffects(() -> call(fixture.renderer, "finishV2", cohort.candidate, cohort.journal), snapshot);
                        else {
                            refusedWithoutEffects(() -> exactInput.fieldPreservationBegin(fixture.a.record, scope), snapshot);
                            refusedWithoutEffects(() -> exactInput.fieldPreservationEnd(fixture.a.record, scope), snapshot);
                            refusedWithoutEffects(() -> call(fixture.renderer, "completeFailedV2", cohort.candidate, null, null), snapshot);
                        }
                    } finally { put(target, member, previous); }
                    note((finishing ? "finish " : "native ") + identity);
                }
            };
            check(fixture.edit(), "valid own success remains after complete identity matrix"); ConcreteHostProbe.hook = null;
            check(nativePhase[0] && finishPhase[0] && count(other.renderer) == 0 && count(fixture.renderer) == 0, "both real owners preserved across all endpoint substitutions");
        }
    }
    private static void getterSuffixMatrix() {
        for (String hook : new String[] {"focus", "windowFocus", "windowVisibility", "aggregate", "visibility", "detach"}) for (boolean foreign : new boolean[] {false, true}) for (boolean repeated : new boolean[] {false, true}) try (Fixture fixture = new Fixture(true, true)) {
            Cohort cohort = new Cohort(fixture); boolean[] fired = {false}; int[] supers = {0};
            var selected = foreign ? fixture.c : fixture.a; long before = (Long) get(fixture.renderer, "editorLossSerial");
            String nativeName = switch (hook) { case "focus" -> "View.onFocusChanged"; case "windowFocus" -> "View.onWindowFocusChanged"; case "windowVisibility" -> "View.onWindowVisibilityChanged"; case "aggregate" -> "View.onVisibilityAggregated"; case "visibility" -> "View.onVisibilityChanged"; default -> "View.onDetachedFromWindow"; };
            Runnable loss = () -> {
                switch (hook) {
                    case "focus" -> call(selected, "onFocusChanged", false, 0, null);
                    case "windowFocus" -> selected.onWindowFocusChanged(false);
                    case "windowVisibility" -> call(selected, "onWindowVisibilityChanged", android.view.View.INVISIBLE);
                    case "aggregate" -> selected.onVisibilityAggregated(false);
                    case "visibility" -> call(selected, "onVisibilityChanged", selected, android.view.View.INVISIBLE);
                    default -> call(selected, "onDetachedFromWindow");
                }
            };
            ConcreteHostProbe.hook = (method, phase) -> {
                cohort.observe(method, phase); var event = ConcreteHostProbe.lastEvent();
                if (!fired[0] && cohort.forward && event.receiver == fixture.a && method.equals("TextView.getEditableText") && phase.equals("beforeReturn") && frame("validateAttachedV2")) {
                    fired[0] = true; check(cohort.scopes[0].checking, "actual final snapshot getter remains checking at lifecycle reentry");
                    for (int index = 0; index < (repeated ? 2 : 1); index++) try { loss.run(); } catch (RuntimeException | Error expected) { note("loss retained " + hook); }
                }
                if (fired[0] && event.receiver == selected && method.equals(nativeName) && phase.equals("entry")) { supers[0]++; check(count(fixture.renderer) == 3, "exact captured superclass suffix uses original A/C/B custody"); }
            };
            boolean returned = false; try { returned = fixture.edit(); } catch (RuntimeException | Error expected) { note("getter loss refused success"); } ConcreteHostProbe.hook = null;
            check(fired[0] && supers[0] == (repeated ? 2 : 1) && (Long) get(fixture.renderer, "editorLossSerial") == before + (repeated ? 2 : 1), "each own/foreign actual getter loss observes denial and exactly matching native superclass: " + hook);
            check(!returned && !cohort.commit && fixture.fence.terminal && count(fixture.renderer) == 0 && !cohort.scopes[0].counted && !cohort.scopes[1].counted, "new or repeated lifecycle loss cannot commit or retain balanced native counts");
        }
    }
    private static void journalMembership() {
        try (Fixture fixture = new Fixture(true, true)) {
            Cohort cohort = new Cohort(fixture); boolean[] constructed = {false};
            ConcreteHostProbe.hook = (method, phase) -> {
                cohort.observe(method, phase);
                if (!constructed[0] && cohort.commit && method.equals("NativeBridge.commitV2") && phase.equals("beforeReturn")) {
                    constructed[0] = true; cohort.afterFinish = true; // Independent post-return accounting below.
                    Object[] states = (Object[]) get(cohort.journal, "states");
                    Object a = nativeState(cohort.journal, fixture.a.record);
                    for (int index = 0; index < states.length; index++) if (get(states[index], "record") == fixture.c.record) states[index] = a;
                    note("hostile fixed journal array substitutes duplicate exact owned A state for C");
                }
            };
            boolean returned = false; Throwable escaped = null;
            try { returned = fixture.edit(); } catch (RuntimeException | Error failure) { escaped = failure; }
            ConcreteHostProbe.hook = null;
            System.out.println("JOURNAL_MEMBERSHIP_OBSERVATION injected=" + constructed[0] + " returned=" + returned + " escaped=" + escaped +
                    " terminal=" + fixture.fence.terminal + " completion=" + get(cohort.journal, "completion") +
                    " shared=" + count(fixture.renderer) + " preservation=" + get(fixture.renderer, "outstandingFieldPreservations") +
                    " held=" + get(cohort.candidate, "heldPreservations") + " Acounted=" + cohort.scopes[0].counted + " Areleased=" + cohort.scopes[0].released +
                    " Ccounted=" + cohort.scopes[1].counted + " Creleased=" + cohort.scopes[1].released + " Cregistered=" + (fixture.c.record.fieldPreservation == cohort.scopes[1]) +
                    " busy=" + fixture.renderer.editorDisposalBusyV2());
            check(constructed[0] && !returned && fixture.fence.terminal && !get(cohort.journal, "completion").equals(2), "duplicated owned journal membership must not complete success or double-decrement one exact count");
        }
    }
    public static void main(String[] arguments) throws Exception {
        descriptor = Files.readAllBytes(Path.of(arguments[1]));
        switch (arguments[0]) {
            case "fixture-smoke" -> fixtureSmoke();
            case "three-success" -> success();
            case "three-known-rejections" -> knownRejections();
            case "outcome-failures" -> outcomeFailures();
            case "refresh-zero-count" -> refresh();
            case "no-scope" -> noScope();
            case "pre-attach-no-original" -> preAttachNoOriginal();
            case "captured-A-refusal" -> entryRefusal("a", false);
            case "partial-A-entered-C-refusal" -> entryRefusal("c", false);
            case "constructor-before-registration" -> entryRefusal("a", true);
            case "malformed-custody" -> malformedCustody();
            case "fatal-chronology" -> fatalChronology();
            case "foreign-replay" -> foreignReplay();
            case "progress-states" -> progressStates();
            case "cohort-preflight" -> cohortPreflight();
            case "identity-matrix" -> identityMatrix();
            case "getter-suffix-matrix" -> getterSuffixMatrix();
            case "journal-membership" -> journalMembership();
            default -> throw new IllegalArgumentException(arguments[0]);
        }
        System.out.println("PASS independent prospective preservation control " + arguments[0] + " / " + checks + " assertions; trace=" + trace);
    }
}
