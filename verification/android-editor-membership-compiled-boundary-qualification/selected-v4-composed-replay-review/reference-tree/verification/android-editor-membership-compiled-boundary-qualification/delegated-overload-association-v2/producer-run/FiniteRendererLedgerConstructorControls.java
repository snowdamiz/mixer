package dev.mixer.android;

import java.lang.invoke.MethodType;
import java.lang.reflect.Array;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Comparator;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Two finite original Java bodies. No enclosing lifecycle or release authority. */
public final class FiniteRendererLedgerConstructorControls {
    private FiniteRendererLedgerConstructorControls() {}
    private static final String CONTEXT = "1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd";
    private static final String RENDERER_HASH = "c7ad938bb6a6cc5403927006171a344750966bef2d1fa8e8b6b6ae7ef8551d2f";
    private static final String MEMBERSHIP_HASH = "08b7d65bcdc16a21365d00997605541a2b784d9028d1b71e975c32e27aa87d8f";
    private static final String LEDGER_ID = "dev/mixer/android/NativeRenderer#rememberV2(Ljava/lang/Throwable;)V";
    private static final String CONSTRUCTOR_ID = "dev/mixer/android/NativeRenderer$PreservationMembership#<init>(Ldev/mixer/android/NativeRenderer$NativeState;Ldev/mixer/android/NativeAppearanceViewsV2$FieldPreservation;)V";
    private static final IdentityHashMap<Object, String> identities = new IdentityHashMap<>();
    private static final List<Map<String, Object>> rows = new ArrayList<>();
    private static final List<Map<String, Object>> snapshots = new ArrayList<>();
    private static final List<Map<String, Object>> boundaryFrames = new ArrayList<>();
    private static final List<Object> relevant = new ArrayList<>();
    private static final List<Object> constructed = new ArrayList<>();
    private static List<Throwable> markerFailures = List.of();
    private static Object fixture, candidate, journal, stateA, stateC, ledger;
    private static NativeRenderer renderer;
    private static NativeAppearanceViewsV2.NativeField a, c;
    private static NativeAppearanceViewsV2.FieldPreservation scopeA, scopeC;
    private static Object[] states;
    private static Method remember;
    private static Constructor<?> membershipConstructor;
    private static Class<?> membershipClass;
    private static boolean observed, editCompleted, fixtureClosed;
    private static int checks, anonymous;

    private static final class EqualOrdinary extends RuntimeException {
        private static final long serialVersionUID = 1L;
        EqualOrdinary(String name) { super(name); }
        @Override public boolean equals(Object value) { return value instanceof EqualOrdinary; }
        @Override public int hashCode() { return 7; }
    }
    private static final class EqualFatal extends Error {
        private static final long serialVersionUID = 1L;
        EqualFatal(String name) { super(name); }
        @Override public boolean equals(Object value) { return value instanceof EqualFatal; }
        @Override public int hashCode() { return 11; }
    }
    private static void require(boolean value, String reason) {
        checks++;
        if (!value) throw new AssertionError(reason);
    }
    private static Map<String, Object> map(Object... entries) {
        Map<String, Object> value = new LinkedHashMap<>();
        for (int index = 0; index < entries.length; index += 2) value.put((String)entries[index], entries[index + 1]);
        return value;
    }
    private static String reference(Object value) {
        if (value == null) return null;
        return identities.computeIfAbsent(value, ignored -> "object." + (++anonymous) + ":" + value.getClass().getName());
    }
    private static void anchor(Object value, String name) {
        if (value != null) {
            String old = identities.putIfAbsent(value, name);
            require(old == null || old.equals(name), "duplicate named identity: " + name);
        }
    }
    private static void include(Object value, String name) {
        if (value != null) {
            anchor(value, name);
            boolean present = false;
            for (Object old : relevant) if (old == value) present = true;
            if (!present) relevant.add(value);
        }
    }
    private static Field field(Object target, String name) {
        Class<?> type = target instanceof Class<?> selected ? selected : target.getClass();
        for (; type != null; type = type.getSuperclass()) {
            try { Field selected = type.getDeclaredField(name); selected.setAccessible(true); return selected; }
            catch (NoSuchFieldException ignored) { /* inherited host fields are relevant */ }
        }
        throw new AssertionError("exact field missing: " + name);
    }
    private static Object get(Object target, String name) {
        try { return field(target, name).get(target instanceof Class<?> ? null : target); }
        catch (IllegalAccessException failure) { throw new AssertionError(failure); }
    }
    private static void set(Object target, String name, Object value) {
        try { field(target, name).set(target instanceof Class<?> ? null : target, value); }
        catch (IllegalAccessException failure) { throw new AssertionError(failure); }
    }
    private static Object fixtureCall(String name) throws ReflectiveOperationException {
        Method selected = fixture.getClass().getDeclaredMethod(name); selected.setAccessible(true);
        try { return selected.invoke(fixture); }
        catch (InvocationTargetException failure) {
            if (failure.getCause() instanceof RuntimeException ordinary) throw ordinary;
            if (failure.getCause() instanceof Error fatal) throw fatal;
            throw failure;
        }
    }
    private static String hash(byte[] value) {
        try { return java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value)); }
        catch (java.security.NoSuchAlgorithmException failure) { throw new AssertionError(failure); }
    }
    private static String digest(Object value) { return hash(json(value).getBytes(StandardCharsets.UTF_8)); }
    private static String json(Object value) {
        StringBuilder result = new StringBuilder(); write(result, value); return result.toString();
    }
    private static void write(StringBuilder result, Object value) {
        if (value == null) result.append("null");
        else if (value instanceof Boolean || value instanceof Number) result.append(value);
        else if (value instanceof String text) {
            result.append('"');
            for (int index = 0; index < text.length(); index++) {
                char ch = text.charAt(index);
                switch (ch) {
                    case '"' -> result.append("\\\"");
                    case '\\' -> result.append("\\\\");
                    case '\n' -> result.append("\\n");
                    case '\r' -> result.append("\\r");
                    case '\t' -> result.append("\\t");
                    default -> { if (ch < 32) result.append(String.format("\\u%04x", (int)ch)); else result.append(ch); }
                }
            }
            result.append('"');
        } else if (value instanceof Map<?, ?> values) {
            result.append('{'); boolean comma = false;
            for (var entry : values.entrySet()) { if (comma) result.append(','); comma = true; write(result, entry.getKey()); result.append(':'); write(result, entry.getValue()); }
            result.append('}');
        } else if (value instanceof Collection<?> values) {
            result.append('['); boolean comma = false;
            for (Object item : values) { if (comma) result.append(','); comma = true; write(result, item); }
            result.append(']');
        } else throw new AssertionError("receipt value type unsupported: " + value.getClass());
    }
    private static List<Integer> counts() {
        return List.of((Integer)get(candidate, "heldPreservations"), (Integer)get(renderer, "outstandingFieldPreservations"), (Integer)get(renderer, "outstandingEditorNativeCalls"));
    }
    private static String fieldKey(Object owner, Field selected) {
        return reference(owner) + "/" + selected.getDeclaringClass().getName() + "#" + selected.getName();
    }
    /** Complete direct fields on a bounded relevant roster. Containers are identity/value digests.
     * No traversal into JDK object internals, arbitrary globals or recursive product graphs. */
    private static final class Snapshot {
        final Map<String, Object> fields = new LinkedHashMap<>();
        final Map<String, Object> containers = new LinkedHashMap<>();
        final Map<String, Object> throwableDiagnostics = failureStates(markerFailures);
        final List<ConcreteHostProbe.Event> events = ConcreteHostProbe.events();
        Snapshot() {
            for (Object owner : relevant) capture(owner);
            for (Field selected : sortedFields(NativeBridge.class)) if (Modifier.isStatic(selected.getModifiers())) captureField(null, selected);
            for (Object state : states) container(get(state, "drawableState"));
            container(states);
        }
        void capture(Object owner) {
            for (Class<?> type = owner.getClass(); type != Object.class; type = type.getSuperclass()) {
                for (Field selected : sortedFields(type)) if (!Modifier.isStatic(selected.getModifiers())) captureField(owner, selected);
            }
        }
        void captureField(Object owner, Field selected) {
            selected.setAccessible(true);
            try {
                Object value = selected.get(owner);
                String key = owner == null ? "static/" + selected.getDeclaringClass().getName() + "#" + selected.getName() : fieldKey(owner, selected);
                fields.put(key, selected.getType().isPrimitive() ? value : reference(value));
                container(value);
            } catch (IllegalAccessException failure) { throw new AssertionError(failure); }
        }
        void container(Object value) {
            if (value == null || containers.containsKey(reference(value))) return;
            List<Object> items = new ArrayList<>();
            if (value.getClass().isArray()) {
                boolean primitive = value.getClass().getComponentType().isPrimitive();
                for (int index = 0; index < Array.getLength(value); index++) {
                    Object item = Array.get(value, index); items.add(primitive ? item : reference(item));
                }
            } else if (value instanceof Collection<?> collection) {
                for (Object item : collection) items.add(reference(item));
            } else if (value instanceof Map<?, ?> values) {
                for (var item : values.entrySet()) items.add(Arrays.asList(reference(item.getKey()), reference(item.getValue())));
            } else return;
            containers.put(reference(value), map("type", value.getClass().getName(), "size", items.size(), "identity_or_primitive_items_sha256", digest(items)));
        }
        Map<String, Object> document() {
            List<String> eventIds = new ArrayList<>(); for (Object event : events) eventIds.add(reference(event));
            return map("fields", fields, "containers", containers, "throwable_diagnostics", throwableDiagnostics, "native_event_prefix", eventIds,
                       "counts", counts(), "snapshot_scope", "bounded relevant direct fields, inherited fields, direct containers and JNI static fields");
        }
        void unchangedExcept(Snapshot after, boolean remembering) {
            Map<String, Object> beforeFields = new LinkedHashMap<>(fields), afterFields = new LinkedHashMap<>(after.fields);
            if (remembering) for (String name : new String[] {"primary", "firstFatal"}) {
                String key = fieldKey(ledger, field(ledger, name)); beforeFields.remove(key); afterFields.remove(key);
            }
            require(beforeFields.equals(afterFields), "non-target direct field changed");
            require(containers.equals(after.containers), "array/collection/map membership or primitive values changed");
            require(throwableDiagnostics.equals(after.throwableDiagnostics), "exception suppression/cause/stack diagnostics changed");
            require(events.size() == after.events.size(), "native host event emitted by selected body");
            for (int index = 0; index < events.size(); index++) require(events.get(index) == after.events.get(index), "native event identity prefix changed");
        }
    }
    private static List<Field> sortedFields(Class<?> type) {
        List<Field> fields = new ArrayList<>(Arrays.asList(type.getDeclaredFields()));
        fields.sort(Comparator.comparing(Field::getName)); return fields;
    }
    private static void retainSnapshots(Map<String, Object> row, Snapshot before, Snapshot after) {
        int beforeIndex = snapshots.size(); Map<String, Object> b = before.document(); snapshots.add(b);
        int afterIndex = snapshots.size(); Map<String, Object> f = after.document(); snapshots.add(f);
        row.put("snapshot_before_index", beforeIndex); row.put("snapshot_after_index", afterIndex);
        row.put("snapshot_before_sha256", digest(b)); row.put("snapshot_after_sha256", digest(f));
        row.put("unchanged_non_target_fields_and_containers", true);
        row.put("native_effects", 0); row.put("native_events_before", before.events.size()); row.put("native_events_after", after.events.size());
    }
    private record Sequence(String name, Throwable primarySeed, Error fatalSeed, Throwable[] inputs, Throwable[] primary, Error[] fatal) {}
    private static void rememberSequence(Sequence sequence) {
        Object savedPrimary = get(ledger, "primary"), savedFatal = get(ledger, "firstFatal");
        try {
            set(ledger, "primary", sequence.primarySeed); set(ledger, "firstFatal", sequence.fatalSeed);
            require(sequence.inputs.length == sequence.primary.length && sequence.inputs.length == sequence.fatal.length, "literal oracle dimensions");
            for (int index = 0; index < sequence.inputs.length; index++) {
                Snapshot before = new Snapshot(); List<Integer> countBefore = counts();
                Object pBefore = get(ledger, "primary"), fBefore = get(ledger, "firstFatal");
                Throwable input = sequence.inputs[index]; Object result = null; Throwable failure = null;
                try { result = remember.invoke(renderer, new Object[] {input}); }
                catch (InvocationTargetException wrapped) { failure = wrapped.getCause(); }
                catch (IllegalAccessException wrapped) { throw new AssertionError(wrapped); }
                Snapshot after = new Snapshot(); before.unchangedExcept(after, true);
                require(failure == null && result == null && remember.getReturnType() == void.class, "exact typed void outcome");
                require(get(ledger, "primary") == sequence.primary[index], "literal first primary identity");
                require(get(ledger, "firstFatal") == sequence.fatal[index], "literal first fatal identity");
                require(countBefore.equals(counts()), "selected remember altered held/global/shared counts");
                Map<String, Object> row = map("subject_id", LEDGER_ID, "case_id", "renderer-finite-source-invariants", "control_case", sequence.name + "/" + index,
                    "class_sha256", RENDERER_HASH, "source_context", CONTEXT, "input", reference(input),
                    "ledger_before", map("primary", reference(pBefore), "firstFatal", reference(fBefore)),
                    "literal_expected_after", map("primary", reference(sequence.primary[index]), "firstFatal", reference(sequence.fatal[index])),
                    "actual_after", map("primary", reference(get(ledger, "primary")), "firstFatal", reference(get(ledger, "firstFatal"))),
                    "actual_typed_outcome", map("kind", "void", "jvm_return_descriptor", "V", "reflection_return", result, "exception", reference(failure)),
                    "counts_before", countBefore, "counts_after", counts(), "seed_scope", "private component primary/fatal seeds only; no enclosing lifecycle reachability inferred");
                retainSnapshots(row, before, after); rows.add(row);
            }
        } finally { set(ledger, "primary", savedPrimary); set(ledger, "firstFatal", savedFatal); }
    }
    private static void construct(String label, Object state, NativeAppearanceViewsV2.FieldPreservation scope) {
        Snapshot before = new Snapshot(); List<Integer> countBefore = counts(); Object value = null; Throwable failure = null;
        try { value = membershipConstructor.newInstance(state, scope); }
        catch (InvocationTargetException wrapped) { failure = wrapped.getCause(); }
        catch (ReflectiveOperationException wrapped) { throw new AssertionError(wrapped); }
        Snapshot after = new Snapshot(); before.unchangedExcept(after, false);
        require(failure == null && value != null && value.getClass() == membershipClass, "exact constructed reference outcome");
        require(get(value, "state") == state && get(value, "scope") == scope, "constructor retains literal argument references");
        for (Object previous : constructed) require(value != previous, "ordinary repeated construction must be fresh");
        for (Object stateEntry : states) require(value != get(stateEntry, "membership"), "new construction is not an original registration");
        require(countBefore.equals(counts()), "constructor altered held/global/shared counts");
        anchor(value, "constructed." + constructed.size()); constructed.add(value);
        Map<String, Object> row = map("subject_id", CONSTRUCTOR_ID, "case_id", "renderer-finite-source-invariants", "control_case", label,
            "class_sha256", MEMBERSHIP_HASH, "source_context", CONTEXT,
            "literal_arguments", map("state", reference(state), "scope", reference(scope)),
            "literal_expected_after", map("state", reference(state), "scope", reference(scope), "fresh_identity", true),
            "actual_after", map("state", reference(get(value, "state")), "scope", reference(get(value, "scope")), "fresh_identity", true),
            "actual_typed_outcome", map("kind", "constructed-reference", "jvm_return_descriptor", "V", "reflection_return_class", value.getClass().getName(), "constructed_reference", reference(value), "exception", reference(failure)),
            "counts_before", countBefore, "counts_after", counts(), "additional_instance_default_fields", List.of(),
            "membership_or_release_authority_inferred", false, "allocation_failure_qualified", false);
        retainSnapshots(row, before, after); rows.add(row);
    }
    private static void suite() {
        require(counts().equals(List.of(2, 2, 3)), "exact original ordinary A boundary counts");
        require(states.length == 4 && scopeA != scopeC && scopeA.counted && scopeC.counted, "actual original full roster and A/C custody");
        EqualOrdinary oa = new EqualOrdinary("ordinary A"), ob = new EqualOrdinary("ordinary B");
        EqualFatal fa = new EqualFatal("fatal A"), fb = new EqualFatal("fatal B");
        Throwable checked = new Throwable("checked Throwable"); Exception exception = new Exception("checked Exception");
        anchor(oa, "ordinary.A"); anchor(ob, "ordinary.B"); anchor(fa, "fatal.A"); anchor(fb, "fatal.B"); anchor(checked, "checked.Throwable"); anchor(exception, "checked.Exception");
        require(oa != ob && oa.equals(ob) && fa != fb && fa.equals(fb), "identity markers intentionally value-equal");
        List<Throwable> failures = List.of(oa, ob, fa, fb, checked, exception);
        markerFailures = failures;
        Map<String, Object> failureStates = failureStates(failures);
        Snapshot original = new Snapshot();
        // Every expected identity below is independently literal; no product condition is copied.
        rememberSequence(new Sequence("ordinary-then-error", null, null,
            new Throwable[] {null, oa, null, ob, fa, fb, oa, null},
            new Throwable[] {null, oa, oa, oa, oa, oa, oa, oa},
            new Error[] {null, null, null, null, fa, fa, fa, fa}));
        rememberSequence(new Sequence("error-then-ordinary", null, null,
            new Throwable[] {fa, null, oa, fb, fa, ob, null},
            new Throwable[] {fa, fa, fa, fa, fa, fa, fa},
            new Error[] {fa, fa, fa, fa, fa, fa, fa}));
        rememberSequence(new Sequence("checked-failures", null, null,
            new Throwable[] {checked, exception, null, fb, checked},
            new Throwable[] {checked, checked, checked, checked, checked},
            new Error[] {null, null, null, fb, fb}));
        rememberSequence(new Sequence("already-retained-pair", oa, fa,
            new Throwable[] {null, ob, fb, fa},
            new Throwable[] {oa, oa, oa, oa},
            new Error[] {fa, fa, fa, fa}));
        rememberSequence(new Sequence("independent-fatal-before-primary-seed", null, fa,
            new Throwable[] {null, oa, fb, null},
            new Throwable[] {null, oa, oa, oa},
            new Error[] {fa, fa, fa, fa}));
        rememberSequence(new Sequence("primary-error-with-separately-empty-fatal-seed", fa, null,
            new Throwable[] {null, ob, fb, null},
            new Throwable[] {fa, fa, fa, fa},
            new Error[] {null, null, fb, fb}));
        require(failureStates.equals(failureStates(failures)), "failure cause/suppression/stack/identity unchanged");
        original.unchangedExcept(new Snapshot(), false);
        Object savedPrimary = get(ledger, "primary"), savedFatal = get(ledger, "firstFatal");
        try {
            set(ledger, "primary", oa); set(ledger, "firstFatal", fa);
            construct("both-null", null, null);
            construct("both-null-repeat-fresh", null, null);
            construct("state-only", stateA, null);
            construct("scope-only", null, scopeA);
            construct("actual-A-pair", stateA, scopeA);
            construct("actual-C-pair", stateC, scopeC);
            construct("crossed-A-state-C-scope", stateA, scopeC);
            construct("crossed-C-state-A-scope", stateC, scopeA);
            construct("actual-A-pair-repeat-fresh", stateA, scopeA);
        } finally { set(ledger, "primary", savedPrimary); set(ledger, "firstFatal", savedFatal); }
        original.unchangedExcept(new Snapshot(), false);
        require(failureStates.equals(failureStates(failures)), "constructor does not alter held failure identities or diagnostics");
    }
    private static Map<String, Object> failureStates(List<Throwable> failures) {
        Map<String, Object> result = new LinkedHashMap<>();
        for (Throwable failure : failures) {
            List<String> suppressed = new ArrayList<>(); for (Throwable entry : failure.getSuppressed()) suppressed.add(reference(entry));
            List<String> stack = new ArrayList<>(); for (StackTraceElement entry : failure.getStackTrace()) stack.add(entry.toString());
            result.put(reference(failure), map("cause", reference(failure.getCause()), "suppressed", suppressed, "stack", stack));
        }
        return result;
    }
    private static void bindBoundary() {
        scopeA = a.record.fieldPreservation; scopeC = c.record.fieldPreservation;
        candidate = get(renderer, "v2Pending"); journal = get(candidate, "journal"); states = (Object[])get(journal, "states"); ledger = get(renderer, "v2Cleanup");
        include(fixture, "fixture"); include(renderer, "renderer"); include(candidate, "candidate"); include(journal, "journal"); include(ledger, "renderer.ledger");
        include(scopeA, "scope.A"); include(scopeC, "scope.C"); include(a, "field.A"); include(c, "field.C"); include(a.record, "record.A"); include(c.record, "record.C");
        include(scopeA.original, "original.mutation");
        Object owner = get(fixture, "owner"), coordinator = get(fixture, "coordinator"), observer = get(owner, "observer");
        include(owner, "owner"); include(coordinator, "coordinator"); include(observer, "observer"); include(get(fixture, "fence"), "fence");
        include(get(owner, "ledger"), "owner.ledger"); include(get(coordinator, "ledger"), "coordinator.ledger"); include(get(observer, "ledger"), "observer.ledger");
        include(get(fixture, "b"), "field.B"); include(get(get(fixture, "b"), "record"), "record.B");
        for (int index = 0; index < states.length; index++) {
            Object state = states[index]; include(state, "state." + index); Object membership = get(state, "membership");
            if (membership != null) include(membership, "original.membership." + index);
            if (get(state, "record") == a.record) stateA = state;
            if (get(state, "record") == c.record) stateC = state;
        }
        require(stateA != null && stateC != null && get(stateA, "preservation") == scopeA && get(stateC, "preservation") == scopeC, "actual state/scope registration capture");
    }
    private static void verifyClass(Class<?> selected, String expected) throws Exception {
        try (var source = selected.getResourceAsStream(selected.getSimpleName() + ".class")) {
            // Nested getSimpleName is not its emitted binary basename.
            if (source != null && !selected.isMemberClass()) { require(hash(source.readAllBytes()).equals(expected), "exact class bytes"); return; }
        }
        String resource = "/" + selected.getName().replace('.', '/') + ".class";
        try (var source = selected.getResourceAsStream(resource)) { require(source != null && hash(source.readAllBytes()).equals(expected), "exact original emitted class " + selected.getName()); }
    }
    public static void main(String[] args) throws Exception {
        require(args.length == 4, "descriptor, results, snapshots, boundary output paths");
        set(SelectedIdentityMembershipReviewControls.class, "descriptor", Files.readAllBytes(Path.of(args[0])));
        remember = NativeRenderer.class.getDeclaredMethod("rememberV2", Throwable.class); remember.setAccessible(true);
        require(MethodType.methodType(remember.getReturnType(), remember.getParameterTypes()).toMethodDescriptorString().equals("(Ljava/lang/Throwable;)V"), "exact remember descriptor");
        membershipClass = Class.forName("dev.mixer.android.NativeRenderer$PreservationMembership");
        Class<?> nativeState = Class.forName("dev.mixer.android.NativeRenderer$NativeState");
        membershipConstructor = membershipClass.getDeclaredConstructor(nativeState, NativeAppearanceViewsV2.FieldPreservation.class); membershipConstructor.setAccessible(true);
        require(MethodType.methodType(void.class, membershipConstructor.getParameterTypes()).toMethodDescriptorString().equals("(Ldev/mixer/android/NativeRenderer$NativeState;Ldev/mixer/android/NativeAppearanceViewsV2$FieldPreservation;)V"), "exact constructor descriptor");
        List<Field> ownFields = sortedFields(membershipClass);
        require(ownFields.size() == 2 && ownFields.get(0).getName().equals("scope") && ownFields.get(1).getName().equals("state"), "complete exact constructor field inventory; no extra defaults");
        for (Field selected : ownFields) require(!selected.isSynthetic() && !Modifier.isStatic(selected.getModifiers()) && Modifier.isFinal(selected.getModifiers()), "only two final non-synthetic reference fields");
        require(field(membershipClass, "state").getType() == nativeState && field(membershipClass, "scope").getType() == NativeAppearanceViewsV2.FieldPreservation.class, "exact constructor field types");
        verifyClass(NativeRenderer.class, RENDERER_HASH); verifyClass(membershipClass, MEMBERSHIP_HASH);
        try {
            Class<?> type = Class.forName("dev.mixer.android.SelectedIdentityMembershipReviewControls$Fixture"); Constructor<?> constructor = type.getDeclaredConstructor(boolean.class, boolean.class); constructor.setAccessible(true);
            fixture = constructor.newInstance(true, true); renderer = (NativeRenderer)get(fixture, "renderer"); a = (NativeAppearanceViewsV2.NativeField)get(fixture, "a"); c = (NativeAppearanceViewsV2.NativeField)get(fixture, "c");
            ConcreteHostProbe.hook = (method, phase) -> {
                ConcreteHostProbe.Event event = ConcreteHostProbe.lastEvent();
                if (!observed && method.equals("View.invalidate") && phase.equals("entry") && event.receiver == a && a.record.fieldPreservation != null) {
                    observed = true; bindBoundary();
                    for (var frame : event.productionFrames) boundaryFrames.add(map("class", frame.className(), "method", frame.methodName(), "descriptor", frame.descriptor(), "bci", frame.bytecodeIndex(), "line", frame.line()));
                    suite();
                }
            };
            require(Boolean.TRUE.equals(fixtureCall("edit")), "original edit succeeds after finally-restored fields"); editCompleted = true; ConcreteHostProbe.hook = null;
            require(observed && counts().equals(List.of(0, 0, 0)), "all original held/global/shared counts return to zero");
            require(a.record.fieldPreservation == null && c.record.fieldPreservation == null && scopeA.released && scopeC.released && !scopeA.counted && !scopeC.counted, "original A/C registrations released after real edit");
            require(rows.size() == 41 && constructed.size() == 9, "exact finite selected invocation count");
        } finally {
            ConcreteHostProbe.hook = null;
            if (fixture != null) { fixtureCall("close"); fixtureClosed = true; }
        }
        Files.writeString(Path.of(args[1]), json(map("source_context", CONTEXT, "invocations", rows.size(), "remember_invocations", 32, "constructor_invocations", constructed.size(), "checks", checks,
            "snapshot_scope", "bounded relevant direct fields/inherited fields and direct arrays/collections/maps, JNI static fields and exact native host event prefix; no arbitrary global/recursive/JDK internals claim",
            "original_boundary_counts", List.of(2, 2, 3), "original_final_counts", counts(), "original_edit_completed_after_finally_restores", editCompleted,
            "fixture_close_returned", fixtureClosed, "fixture_close_catches_product_failures", true, "native_physical_cleanup_credit", false,
            "constructor_complete_instance_fields", List.of("scope:final FieldPreservation", "state:final NativeState"), "constructor_additional_default_fields", List.of(),
            "rows", rows)) + "\n");
        Files.writeString(Path.of(args[2]), json(map("snapshots", snapshots)) + "\n");
        Files.writeString(Path.of(args[3]), json(map("method", "View.invalidate", "phase", "entry", "receiver", reference(a), "counts", List.of(2, 2, 3), "original_production_frames", boundaryFrames)) + "\n");
        System.out.println("PASS 41 finite direct calls: rememberV2 32; PreservationMembership constructor 9; original counts 2/2/3 -> 0/0/0; zero native host events during selected calls.");
    }
}
