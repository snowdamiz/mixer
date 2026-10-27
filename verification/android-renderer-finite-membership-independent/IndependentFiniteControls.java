package dev.mixer.android;

import java.lang.invoke.MethodType;
import java.lang.reflect.Array;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Independent finite host observations; no enclosing completion authority. */
public final class IndependentFiniteControls {
    private IndependentFiniteControls() {}
    private static Object fixture, candidate, journal, stateA, stateC, membershipA;
    private static NativeRenderer renderer;
    private static NativeAppearanceViewsV2.NativeField a, c;
    private static NativeAppearanceViewsV2.FieldPreservation sa, sc;
    private static Object[] states;
    private static boolean observed;
    private static final Map<String, Method> methods = new LinkedHashMap<>();
    private static final List<String> rows = new ArrayList<>();
    private static final List<String> frames = new ArrayList<>();
    private static void require(boolean value, String reason) {
        if (!value) throw new AssertionError(reason);
    }
    private static Field field(Object target, String name) {
        Class<?> type = target instanceof Class<?> selected ? selected : target.getClass();
        for (; type != null; type = type.getSuperclass()) {
            try { Field result = type.getDeclaredField(name); result.setAccessible(true); return result; }
            catch (NoSuchFieldException ignored) { /* superclass lookup */ }
        }
        throw new AssertionError("field absent: " + name);
    }
    private static Object get(Object target, String name) {
        try { return field(target, name).get(target instanceof Class<?> ? null : target); }
        catch (IllegalAccessException error) { throw new AssertionError(error); }
    }
    private static void set(Object target, String name, Object value) {
        try { field(target, name).set(target instanceof Class<?> ? null : target, value); }
        catch (IllegalAccessException error) { throw new AssertionError(error); }
    }
    private static Object call(Object target, String name) throws ReflectiveOperationException {
        Method method = target.getClass().getDeclaredMethod(name); method.setAccessible(true);
        try { return method.invoke(target); }
        catch (InvocationTargetException error) {
            if (error.getCause() instanceof RuntimeException ordinary) throw ordinary;
            if (error.getCause() instanceof Error fatal) throw fatal;
            throw error;
        }
    }
    private record Change(Object target, String name, Object value) {}
    private static Change change(Object target, String name, Object value) { return new Change(target, name, value); }
    private static void changed(Runnable test, Change... changes) {
        Object[] saved = new Object[changes.length]; int applied = 0;
        try {
            for (Change item : changes) { saved[applied] = get(item.target, item.name); set(item.target, item.name, item.value); applied++; }
            test.run();
        } finally {
            while (applied > 0) { int index = --applied; set(changes[index].target, changes[index].name, saved[index]); }
        }
    }
    private static int[] counts() {
        return new int[] {(Integer)get(candidate, "heldPreservations"), (Integer)get(renderer, "outstandingFieldPreservations"), (Integer)get(renderer, "outstandingEditorNativeCalls")};
    }
    private record Slot(Object owner, Field field, Object value) {}
    /** Bounded direct relevant-object snapshot. This intentionally claims no recursive graph coverage. */
    private static final class Snapshot {
        final List<Slot> slots = new ArrayList<>();
        final Map<Object, List<Object>> containers = new java.util.IdentityHashMap<>();
        final List<ConcreteHostProbe.Event> events = ConcreteHostProbe.events();
        Snapshot() {
            for (Object object : new Object[] {fixture, renderer, candidate, journal, sa, sc, a, c, a.record, c.record, sa.original, get(renderer, "v2Cleanup")}) capture(object);
            for (Object state : states) { if (state != null) { capture(state); Object membership = get(state, "membership"); if (membership != null) capture(membership); } }
            container(states); container(sa.hooks); container(sc.hooks);
            for (Field selected : NativeBridge.class.getDeclaredFields()) if (Modifier.isStatic(selected.getModifiers())) {
                selected.setAccessible(true);
                try { Object value = selected.get(null); slots.add(new Slot(null, selected, value)); if (value != null && value.getClass().isArray()) container(value); }
                catch (IllegalAccessException error) { throw new AssertionError(error); }
            }
        }
        void capture(Object object) {
            for (Class<?> type = object.getClass(); type != Object.class; type = type.getSuperclass()) {
                for (Field selected : type.getDeclaredFields()) if (!Modifier.isStatic(selected.getModifiers())) {
                    selected.setAccessible(true);
                    try { slots.add(new Slot(object, selected, selected.get(object))); }
                    catch (IllegalAccessException error) { throw new AssertionError(error); }
                }
            }
        }
        void container(Object value) {
            List<Object> copy = new ArrayList<>();
            if (value.getClass().isArray()) for (int i=0; i<Array.getLength(value); i++) copy.add(Array.get(value, i));
            else copy.addAll((Collection<?>)value);
            containers.put(value, copy);
        }
        void verify() {
            for (Slot slot : slots) {
                try {
                    Object actual = slot.field.get(slot.owner);
                    require(slot.field.getType().isPrimitive() ? slot.value.equals(actual) : slot.value == actual, "direct relevant field changed: " + slot.field);
                } catch (IllegalAccessException error) { throw new AssertionError(error); }
            }
            for (var item : containers.entrySet()) {
                Object container = item.getKey(); List<Object> actual = new ArrayList<>();
                boolean primitive = container.getClass().isArray() && container.getClass().getComponentType().isPrimitive();
                if (container.getClass().isArray()) for (int i=0; i<Array.getLength(container); i++) actual.add(Array.get(container, i));
                else actual.addAll((Collection<?>)container);
                require(actual.size() == item.getValue().size(), "container size changed");
                for (int i=0; i<actual.size(); i++) require(primitive ? item.getValue().get(i).equals(actual.get(i)) : item.getValue().get(i) == actual.get(i), "container item changed");
            }
            List<ConcreteHostProbe.Event> after = ConcreteHostProbe.events();
            require(after.size() == events.size(), "native host event added");
            for (int i=0; i<after.size(); i++) require(after.get(i) == events.get(i), "native host event prefix changed");
        }
    }
    private static void observe(String method, String label, String expected, Object... args) {
        Snapshot snapshot = new Snapshot(); int[] before = counts(); Object value = null; Throwable failure = null;
        Method selected = methods.get(method);
        try { value = selected.invoke(renderer, args); }
        catch (InvocationTargetException error) { failure = error.getCause(); }
        catch (IllegalAccessException error) { throw new AssertionError(error); }
        snapshot.verify(); require(Arrays.equals(before, counts()), "counts changed");
        String actual = failure == null ? String.valueOf(value) : failure.getClass().getName();
        require(actual.equals(expected), method + "/" + label + " expected=" + expected + " actual=" + actual);
        String descriptor = MethodType.methodType(selected.getReturnType(), selected.getParameterTypes()).toMethodDescriptorString();
        rows.add(method + descriptor + "\t" + label + "\t" + expected + "\t" + actual + "\t" + Arrays.toString(before) + "\t" + Arrays.toString(counts()) + "\t0");
    }
    private static Object[] tuple() { return new Object[] {candidate, journal, a.record, sa}; }
    private static void suite() {
        require(Arrays.equals(counts(), new int[] {2, 2, 3}), "original first A boundary counts");
        require(states.length == 4 && sa != sc && sa.counted && sc.counted, "ordinary full roster and two counted scopes");
        Snapshot original = new Snapshot();
        RuntimeException primary = new IllegalStateException("independent seed primary"); Error fatal = new AssertionError("independent seed first fatal");
        changed(() -> {
            observe("preservationMembershipV2", "baseline", "true", journal);
            observe("fieldPreservationCapturedV2", "baseline", "true", tuple());
            observe("preservationProvenanceV2", "baseline", "true", candidate, journal);
            observe("fieldPreservationIdentityV2", "baseline", "true", tuple());
            observe("preservationCohortV2", "baseline", "true", candidate);
            observe("preservationFailureFundedV2", "baseline", "true", candidate);
            changed(() -> {
                observe("preservationProvenanceV2", "null-states-classification", "true", candidate, journal);
                observe("preservationMembershipV2", "null-states-membership", "false", journal);
                observe("preservationCohortV2", "null-states-cohort", "false", candidate);
                observe("preservationFailureFundedV2", "null-states-funding", "false", candidate);
            }, change(journal, "states", null));
            changed(() -> {
                String npe = "java.lang.NullPointerException";
                observe("preservationMembershipV2", "null-scope-dereference", npe, journal);
                observe("fieldPreservationIdentityV2", "null-scope-dereference", npe, tuple());
                observe("preservationCohortV2", "null-scope-dereference", npe, candidate);
                observe("preservationFailureFundedV2", "null-scope-dereference", npe, candidate);
                observe("preservationProvenanceV2", "null-scope-classification", "false", candidate, journal);
            }, change(membershipA, "scope", null), change(stateA, "preservation", null));
            changed(() -> {
                observe("preservationMembershipV2", "matching-null-records", "true", journal);
                observe("fieldPreservationCapturedV2", "matching-null-records", "false", tuple());
                observe("preservationProvenanceV2", "matching-null-records", "false", candidate, journal);
            }, change(stateA, "record", null), change(sa, "record", null));
            var twin = NativeAppearanceViewsV2.Mutation.transaction(sa.original.fence, sa.original.token);
            require(twin != sa.original && twin.token == sa.original.token, "ordinary distinct equal-token mutation");
            changed(() -> {
                observe("fieldPreservationCapturedV2", "distinct-equal-token-original", "false", tuple());
                observe("fieldPreservationIdentityV2", "distinct-equal-token-original", "false", tuple());
                observe("preservationProvenanceV2", "distinct-equal-token-original", "false", candidate, journal);
            }, change(candidate, "originalMutation", twin));
            changed(() -> {
                observe("preservationCohortV2", "extra-held-within-bound", "false", candidate);
                observe("preservationFailureFundedV2", "extra-held-within-bound", "true", candidate);
            }, change(candidate, "heldPreservations", 3), change(renderer, "outstandingFieldPreservations", 3));
            changed(() -> {
                observe("preservationCohortV2", "unrelated-shared-work", "true", candidate);
                observe("preservationFailureFundedV2", "unrelated-shared-work", "true", candidate);
            }, change(renderer, "outstandingEditorNativeCalls", Integer.MAX_VALUE));
            changed(() -> {
                observe("preservationCohortV2", "insufficient-shared", "false", candidate);
                observe("preservationFailureFundedV2", "insufficient-shared", "false", candidate);
            }, change(renderer, "outstandingEditorNativeCalls", 1));
            changed(() -> {
                observe("preservationCohortV2", "represented-zero", "true", candidate);
                observe("preservationFailureFundedV2", "represented-zero", "true", candidate);
            }, change(sa, "counted", false), change(sc, "counted", false), change(candidate, "heldPreservations", 0), change(renderer, "outstandingFieldPreservations", 0), change(renderer, "outstandingEditorNativeCalls", 0));
            changed(() -> {
                observe("preservationCohortV2", "ended-not-release-authority", "true", candidate);
                observe("preservationFailureFundedV2", "ended-not-release-authority", "true", candidate);
                observe("fieldPreservationIdentityV2", "ended-not-release-authority", "true", tuple());
            }, change(sa, "ended", true), change(sa, "released", true), change(sa, "entered", false), change(candidate, "used", true));
            require(states[0] != stateA && get(states[0], "preservation") == null, "earlier nonpreserved state");
            changed(() -> {
                observe("fieldPreservationIdentityV2", "earlier-duplicate-record", "false", tuple());
                observe("preservationMembershipV2", "earlier-duplicate-record", "true", journal);
                observe("preservationProvenanceV2", "earlier-duplicate-record", "true", candidate, journal);
            }, change(states[0], "record", a.record));
            changed(() -> {
                observe("preservationProvenanceV2", "non-own-state-skipped", "true", candidate, journal);
                observe("preservationMembershipV2", "non-own-state-invalid-roster", "false", journal);
            }, change(stateA, "journal", null));
        }, change(get(renderer, "v2Cleanup"), "primary", primary), change(get(renderer, "v2Cleanup"), "firstFatal", fatal));
        original.verify(); require(Arrays.equals(counts(), new int[] {2, 2, 3}), "all test mutations restored");
    }
    public static void main(String[] args) throws Exception {
        Class<?> ordinary = Class.forName("dev.mixer.android.SelectedIdentityMembershipReviewControls");
        set(ordinary, "descriptor", Files.readAllBytes(Path.of(args[0])));
        Class<?> ct = NativeRenderer.Candidate.class, jt = NativeRenderer.AttachmentJournal.class;
        for (String name : new String[] {"preservationMembershipV2", "fieldPreservationCapturedV2", "preservationProvenanceV2", "fieldPreservationIdentityV2", "preservationCohortV2", "preservationFailureFundedV2"}) {
            Class<?>[] parameters = name.equals("preservationMembershipV2") ? new Class<?>[] {jt} : name.equals("preservationProvenanceV2") ? new Class<?>[] {ct, jt} : name.startsWith("fieldPreservation") ? new Class<?>[] {ct, jt, NativeAppearanceViewsV2.Record.class, NativeAppearanceViewsV2.FieldPreservation.class} : new Class<?>[] {ct};
            Method selected = NativeRenderer.class.getDeclaredMethod(name, parameters); selected.setAccessible(true); require(selected.getReturnType() == boolean.class, "exact descriptor"); methods.put(name, selected);
        }
        try (var bytes = NativeRenderer.class.getResourceAsStream("NativeRenderer.class")) {
            require(bytes != null, "class resource exists");
            require(java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes.readAllBytes())).equals("c7ad938bb6a6cc5403927006171a344750966bef2d1fa8e8b6b6ae7ef8551d2f"), "exact original renderer class");
        }
        try {
            Class<?> ft = Class.forName("dev.mixer.android.SelectedIdentityMembershipReviewControls$Fixture");
            Constructor<?> constructor = ft.getDeclaredConstructor(boolean.class, boolean.class); constructor.setAccessible(true); fixture = constructor.newInstance(true, true);
            renderer = (NativeRenderer)get(fixture, "renderer"); a = (NativeAppearanceViewsV2.NativeField)get(fixture, "a"); c = (NativeAppearanceViewsV2.NativeField)get(fixture, "c");
            ConcreteHostProbe.hook = (method, phase) -> {
                var event = ConcreteHostProbe.lastEvent();
                if (!observed && method.equals("View.invalidate") && phase.equals("entry") && event.receiver == a && a.record.fieldPreservation != null) {
                    observed = true; sa = a.record.fieldPreservation; sc = c.record.fieldPreservation; candidate = get(renderer, "v2Pending"); journal = get(candidate, "journal"); states = (Object[])get(journal, "states");
                    for (Object state : states) { if (get(state, "record") == a.record) stateA = state; if (get(state, "record") == c.record) stateC = state; }
                    require(stateA != null && stateC != null, "actual A/C states"); membershipA = get(stateA, "membership");
                    for (var site : event.productionFrames) frames.add(site.className() + "#" + site.methodName() + site.descriptor() + "@bci=" + site.bytecodeIndex());
                    suite();
                }
            };
            require((Boolean)call(fixture, "edit"), "ordinary edit succeeds after restores"); ConcreteHostProbe.hook = null;
            require(observed && Arrays.equals(counts(), new int[] {0, 0, 0}), "original edit ends counts zero");
            require(a.record.fieldPreservation == null && c.record.fieldPreservation == null && !sa.counted && !sc.counted && sa.released && sc.released, "original releases actual A/C registrations");
            require(rows.size() == 37, "exact finite independent invocation count");
            Files.write(Path.of(args[1]), rows); Files.write(Path.of(args[2]), frames);
            System.out.println("PASS independent finite host controls: 37 direct calls; original counts 2/2/3 -> 0/0/0; no native host events during calls.");
        } finally {
            ConcreteHostProbe.hook = null; if (fixture != null) call(fixture, "close");
        }
    }
}
