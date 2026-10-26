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

/** Selected private fixed-membership controls. Fixture and existing assertion helpers
 * are copied from the unchanged frozen PC-C16 witness; new cases are authored here.
 * Host invariants only. Reflective hostile states are explicitly distinguished
 * from ordinary synchronous coordinator paths. No production instrumentation.
 */
public final class PreservationMembershipControls {
    private PreservationMembershipControls() {}
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
    private static final String[] MUTATIONS = {"duplicate", "swap", "missing", "foreign", "short-array", "long-array", "short-count", "long-count", "scope-omission", "scope-substitution"};
    private static boolean inside(String name) {
        for (StackTraceElement selected : Thread.currentThread().getStackTrace()) if (selected.getMethodName().equals(name)) return true;
        return false;
    }
    private static Object nativeState(Object journal, NativeAppearanceViewsV2.Record record) {
        for (Object selected : (Object[]) get(journal, "states")) if (get(selected, "record") == record) return selected;
        throw new AssertionError("exact constructor state missing");
    }
    private static final class Roster {
        final Object journal;
        final Object[] array, members;
        final int count, aIndex, cIndex;
        final Object aState, cState, cPreservation;
        Roster(Object journal, Fixture fixture) {
            this.journal = journal; array = (Object[]) get(journal, "states"); members = array.clone(); count = (Integer) get(journal, "stateCount");
            int ai = -1, ci = -1;
            for (int index = 0; index < members.length; index++) {
                if (get(members[index], "record") == fixture.a.record) ai = index;
                if (get(members[index], "record") == fixture.c.record) ci = index;
                check(get(members[index], "journal") == journal && get(members[index], "position").equals(index), "actual constructor journal and fixed position");
            }
            check(ai >= 0 && ci >= 0 && ai != ci && count == array.length, "exact ordered state bounds include A/C");
            aIndex = ai; cIndex = ci; aState = members[ai]; cState = members[ci]; cPreservation = get(cState, "preservation");
        }
        void mutate(String mode, Object foreign, NativeAppearanceViewsV2.FieldPreservation substitute) {
            switch (mode) {
                case "duplicate" -> array[cIndex] = aState;
                case "swap" -> { array[aIndex] = cState; array[cIndex] = aState; }
                case "missing" -> array[cIndex] = null;
                case "foreign" -> array[cIndex] = foreign;
                case "short-array" -> put(journal, "states", Arrays.copyOf(array, array.length - 1));
                case "long-array" -> put(journal, "states", Arrays.copyOf(array, array.length + 1));
                case "short-count" -> put(journal, "stateCount", count - 1);
                case "long-count" -> put(journal, "stateCount", count + 1);
                case "scope-omission" -> put(cState, "preservation", null);
                case "scope-substitution" -> { check(substitute != null && substitute != cPreservation, "equal-authority substitute is a distinct unacquired scope"); put(cState, "preservation", substitute); }
                default -> throw new AssertionError(mode);
            }
            note("HOSTILE_PRIVATE_MEMBERSHIP " + mode);
        }
        void restoreFixtureOnly() {
            System.arraycopy(members, 0, array, 0, array.length); put(journal, "states", array); put(journal, "stateCount", count); put(cState, "preservation", cPreservation);
            note("SYNTHETIC_FIXTURE_RESTORE roster references only; no hold, ledger, phase or authority repair");
        }
    }
    private static NativeAppearanceViewsV2.FieldPreservation substitute(Cohort cohort) {
        var original = cohort.scopes[1];
        var result = new NativeAppearanceViewsV2.FieldPreservation(original.field, original.original, original.selected, original.editable, original.renderer, original.candidate, original.journal);
        result.entered = true; result.counted = true; result.phase = NativeAppearanceViewsV2.FieldPreservation.PRECOMMIT_READY;
        return result;
    }
    private static void retained(Fixture fixture, Cohort cohort) {
        check(count(fixture.renderer) == 2 && get(fixture.renderer, "outstandingFieldPreservations").equals(2) && get(cohort.candidate, "heldPreservations").equals(2), "only original B unwinds; both actual A/C holds remain in all three tallies");
        check(cohort.scopes[0].counted && !cohort.scopes[0].released && cohort.scopes[1].counted && !cohort.scopes[1].released, "unproven roster never double releases or erases omitted actual C custody");
        check(fixture.renderer.editorDisposalBusyV2() && NativeBridge.destroyCalls == 0, "actual retained preservation custody keeps disposal busy");
        check((Boolean) get(cohort.journal, "failedInvoked") && get(cohort.journal, "completion").equals(4), "own malformed roster consumes one failed endpoint with no release");
    }
    private static void failedReplay(Fixture fixture, Cohort cohort, Roster roster, Fixture foreign, Object foreignCandidate) {
        refusedWithoutEffects(() -> call(fixture.renderer, "completeFailedV2", cohort.candidate, null, null), fixture.renderer, fixture.fence, cohort.candidate, cohort.journal, cohort.scopes[0], cohort.scopes[1], fixture.a.record, fixture.c.record);
        refusedWithoutEffects(() -> call(foreign.renderer, "completeFailedV2", cohort.candidate, null, null), foreign.renderer, foreign.fence, foreignCandidate, fixture.renderer, cohort.candidate, cohort.journal, cohort.scopes[0], cohort.scopes[1], fixture.a.record, fixture.c.record);
        roster.restoreFixtureOnly();
        refusedWithoutEffects(() -> call(fixture.renderer, "completeFailedV2", cohort.candidate, null, null), fixture.renderer, fixture.fence, cohort.candidate, cohort.journal, cohort.scopes[0], cohort.scopes[1], fixture.a.record, fixture.c.record);
        check(cohort.scopes[1].counted && fixture.renderer.editorDisposalBusyV2(), "restoring a hostile test roster does not authorize endpoint retry or recover C");
    }
    private static void membership(String boundary) {
        try (Fixture foreign = new Fixture(true, true)) {
            Cohort completed = new Cohort(foreign); ConcreteHostProbe.hook = completed::observe; check(foreign.edit(), "real distinct foreign completed source"); ConcreteHostProbe.hook = null;
            Object foreignState = nativeState(completed.journal, foreign.c.record);
            ObjectState foreignStateBefore = new ObjectState(foreign.renderer, completed.candidate, completed.journal, completed.scopes[0], completed.scopes[1], foreign.a.record, foreign.c.record);
            for (String mutation : MUTATIONS) try (Fixture fixture = new Fixture(true, true)) {
                Cohort cohort = new Cohort(fixture); Roster[] roster = {null}; NativeAppearanceViewsV2.FieldPreservation[] fake = {null}; boolean[] injected = {false}, observed = {false}; Fatal first = new Fatal("original engine fatal before malformed failure " + mutation);
                Object observer = get(fixture.renderer, "v2Environment"); NativeEnvironmentV2.Sink sink = (NativeEnvironmentV2.Sink) get(observer, "sink");
                put(observer, "sink", (NativeEnvironmentV2.Sink) (source, change, cause, primary, fatal) -> {
                    if (injected[0] && !observed[0] && boundary.equals("finish")) {
                        observed[0] = true;
                        check(count(fixture.renderer) == 3 && cohort.scopes[0].counted && cohort.scopes[1].counted && !cohort.scopes[0].ended && !cohort.scopes[1].ended, "whole roster refusal precedes every end/decrement under original count3");
                        check(fixture.a.record.fieldPreservation == cohort.scopes[0] && fixture.c.record.fieldPreservation == cohort.scopes[1], "no callback revocation before whole roster refusal");
                        check(!(Boolean) get(cohort.candidate, "used") && !(Boolean) get(cohort.journal, "complete") && get(cohort.journal, "completion").equals(0), "no candidate consumption or success claim before refusal");
                        check(get(fixture.renderer, "packet") == get(cohort.candidate, "base") && get(fixture.renderer, "v2Records") == get(cohort.candidate, "baseRecords"), "no presentation swap before whole roster refusal");
                    }
                    sink.changed(source, change, cause, primary, fatal);
                });
                ConcreteHostProbe.hook = (method, phase) -> {
                    cohort.observe(method, phase);
                    if (cohort.forward && roster[0] == null) { roster[0] = new Roster(cohort.journal, fixture); fake[0] = substitute(cohort); }
                    boolean selected = boundary.equals("precommit") ? method.equals("TextView.getEditableText") && phase.equals("beforeReturn") && ConcreteHostProbe.lastEvent().receiver == fixture.a && frame("validateAttachedV2") : cohort.commit && method.equals("NativeBridge.commitV2") && phase.equals("beforeReturn");
                    if (!injected[0] && roster[0] != null && selected) {
                        injected[0] = true; cohort.afterFinish = true; roster[0].mutate(mutation, foreignState, fake[0]);
                        if (boundary.equals("failed")) throw first;
                    }
                };
                boolean returned = false; Throwable escaped = null; int commitsBefore = NativeBridge.commitCalls;
                try { returned = fixture.edit(); } catch (RuntimeException | Error failure) { escaped = failure; } ConcreteHostProbe.hook = null;
                check(injected[0] && !returned && fixture.fence.terminal && !get(cohort.journal, "completion").equals(2), "selected " + boundary + " roster mutation refuses success: " + mutation);
                if (boundary.equals("finish")) check(observed[0], "actual reporter observed refusal with intact original cohort");
                if (boundary.equals("failed")) check(escaped == first, "earlier engine fatal retains object identity through malformed roster failure");
                if (boundary.equals("precommit")) check(!cohort.commit && NativeBridge.commitCalls == commitsBefore, "malformed final validation cannot reach engine commit");
                retained(fixture, cohort); failedReplay(fixture, cohort, roster[0], foreign, completed.candidate); foreignStateBefore.unchanged();
                System.out.println("MEMBERSHIP_" + boundary + " " + mutation + " originalCCounted=" + cohort.scopes[1].counted + " shared=" + count(fixture.renderer) + " preservation=" + get(fixture.renderer, "outstandingFieldPreservations") + " held=" + get(cohort.candidate, "heldPreservations") + " busy=" + fixture.renderer.editorDisposalBusyV2() + " escaped=" + escaped);
                put(observer, "sink", sink);
            }
        }
    }
    private static void endpoints() {
        try (Fixture foreign = new Fixture(true, true)) {
            Cohort completed = new Cohort(foreign); ConcreteHostProbe.hook = completed::observe; check(foreign.edit(), "foreign membership fixture succeeds"); ConcreteHostProbe.hook = null;
            for (String mutation : MUTATIONS) try (Fixture fixture = new Fixture(true, true)) {
                Cohort cohort = new Cohort(fixture); boolean[] tested = {false};
                ConcreteHostProbe.hook = (method, phase) -> {
                    cohort.observe(method, phase);
                    if (!tested[0] && cohort.forward) {
                        tested[0] = true; Roster roster = new Roster(cohort.journal, fixture);
                        check(call(fixture.renderer, "preservationMembershipV2", cohort.journal).equals(true), "real entered roster passes exact membership");
                        refusedWithoutEffects(() -> call(fixture.renderer, "beginFieldPreservationsV2", cohort.candidate, cohort.scopes[0].original), fixture.renderer, cohort.candidate, cohort.journal, cohort.scopes[0], cohort.scopes[1], fixture.a.record, fixture.c.record, roster.aState, roster.cState);
                        Object beforeMember = get(roster.cState, "membership");
                        roster.mutate(mutation, nativeState(completed.journal, foreign.c.record), substitute(cohort));
                        check(call(fixture.renderer, "preservationMembershipV2", cohort.journal).equals(false), "selected roster mutation fails scalar membership");
                        refusedWithoutEffects(() -> fixture.a.record.input.fieldPreservationBegin(fixture.a.record, cohort.scopes[0]), fixture.renderer, cohort.candidate, cohort.journal, cohort.scopes[0], cohort.scopes[1], fixture.a.record, fixture.c.record);
                        refusedWithoutEffects(() -> fixture.c.record.input.fieldPreservationEnd(fixture.c.record, cohort.scopes[1]), fixture.renderer, cohort.candidate, cohort.journal, cohort.scopes[0], cohort.scopes[1], fixture.a.record, fixture.c.record);
                        check(get(roster.cState, "membership") == beforeMember, "refusal never replaces capture-once expected scope");
                        roster.restoreFixtureOnly();
                    }
                };
                check(fixture.edit() && tested[0] && !fixture.fence.terminal, "restored endpoint-only fixture completes original healthy transaction"); ConcreteHostProbe.hook = null; cohort.balanced(false);
            }
        }
    }
    private static void reportReentry() {
        for (String mutation : new String[] {"duplicate", "missing", "long-count", "scope-omission"}) try (Fixture fixture = new Fixture(true, true)) {
            Cohort cohort = new Cohort(fixture); Roster[] roster = {null}; boolean[] injected = {false}; Fatal first = new Fatal("original reporting chronology " + mutation); Fatal later = new Fatal("later reporter " + mutation);
            Object observer = get(fixture.renderer, "v2Environment"); NativeEnvironmentV2.Sink sink = (NativeEnvironmentV2.Sink) get(observer, "sink");
            put(observer, "sink", (NativeEnvironmentV2.Sink) (source, change, cause, primary, fatal) -> {
                if (!injected[0] && roster[0] != null && inside("completeFailedV2")) {
                    injected[0] = true; check(count(fixture.renderer) == 3 && cohort.scopes[0].counted && cohort.scopes[1].counted, "reporter reentry occurs while every applicable count remains held");
                    roster[0].mutate(mutation, null, null); throw later;
                }
                sink.changed(source, change, cause, primary, fatal);
            });
            ConcreteHostProbe.hook = (method, phase) -> {
                cohort.observe(method, phase);
                if (cohort.forward && roster[0] == null) roster[0] = new Roster(cohort.journal, fixture);
                if (cohort.commit && method.equals("NativeBridge.commitV2") && phase.equals("beforeReturn")) { cohort.afterFinish = true; throw first; }
            };
            Throwable escaped = null; try { fixture.edit(); } catch (RuntimeException | Error failure) { escaped = failure; } ConcreteHostProbe.hook = null;
            check(injected[0] && escaped == first, "report-time malformed membership preserves first fatal by identity"); retained(fixture, cohort);
            refusedWithoutEffects(() -> call(fixture.renderer, "completeFailedV2", cohort.candidate, null, null), fixture.renderer, cohort.candidate, cohort.journal, cohort.scopes[0], cohort.scopes[1], fixture.a.record, fixture.c.record);
            check(get(cohort.candidate, "heldPreservations").equals(2), "report-time omission never erases actual C custody"); put(observer, "sink", sink);
            System.out.println("MEMBERSHIP_REPORT " + mutation + " firstFatalPreserved=true shared=" + count(fixture.renderer) + " Ccounted=" + cohort.scopes[1].counted);
        }
    }
    private static void healthy() {
        try (Fixture fixture = new Fixture(true, true)) {
            Cohort cohort = new Cohort(fixture); ConcreteHostProbe.hook = cohort::observe; check(fixture.edit(), "healthy exact count3 to B1 to0 succeeds"); ConcreteHostProbe.hook = null; cohort.balanced(false);
            check(cohort.commit && cohort.afterFinish && !fixture.fence.terminal, "actual original commit interval and exact count-last tail remain healthy");
            refusedWithoutEffects(() -> call(fixture.renderer, "finishV2", cohort.candidate, cohort.journal), fixture.renderer, cohort.candidate, cohort.journal, cohort.scopes[0], cohort.scopes[1], fixture.a.record, fixture.c.record);
        }
        for (String boundary : new String[] {"finish", "failed"}) try (Fixture fixture = new Fixture(false, true)) {
            Object[] candidate = {null}; boolean[] injected = {false}; Fatal first = new Fatal("no-scope unknown outcome");
            ConcreteHostProbe.hook = (method, phase) -> {
                if (!injected[0] && method.equals("NativeBridge.commitV2") && phase.equals("beforeReturn")) {
                    injected[0] = true; candidate[0] = pending(fixture.renderer); var selected = journal(candidate[0]); new Roster(selected, fixture).mutate("duplicate", null, null);
                    if (boundary.equals("failed")) throw first;
                }
            };
            boolean returned = false; try { returned = fixture.edit(); } catch (RuntimeException | Error expected) { note("no-scope malformed roster refused"); } ConcreteHostProbe.hook = null;
            check(injected[0] && !returned && fixture.fence.terminal && get(journal(candidate[0]), "completion").equals(4), "exact constructor roster is mandatory even with no captured scopes: " + boundary);
            check(count(fixture.renderer) == 0 && get(fixture.renderer, "outstandingFieldPreservations").equals(0) && get(candidate[0], "heldPreservations").equals(0), "no-scope refusal invents no hold or release");
            check(get(fixture.renderer, "packet") == get(candidate[0], "base"), "no-scope malformed roster cannot publish prepared presentation");
            refusedWithoutEffects(() -> call(fixture.renderer, "completeFailedV2", candidate[0], null, null), fixture.renderer, fixture.fence, candidate[0], journal(candidate[0]));
        }
    }
    public static void main(String[] arguments) throws Exception {
        descriptor = Files.readAllBytes(Path.of(arguments[1]));
        switch (arguments[0]) {
            case "finish-membership" -> membership("finish");
            case "failed-membership" -> membership("failed");
            case "precommit-membership" -> membership("precommit");
            case "endpoint-membership" -> endpoints();
            case "report-reentry-membership" -> reportReentry();
            case "healthy" -> healthy();
            default -> throw new IllegalArgumentException(arguments[0]);
        }
        System.out.println("PASS selected private fixed membership control " + arguments[0] + " / " + checks + " assertions; trace=" + trace);
    }
}
