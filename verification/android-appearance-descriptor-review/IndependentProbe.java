package dev.mixer.android;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Independent host data probes; no Android runtime or presentation claim. */
public final class IndependentProbe {
    private static long assertions;
    private static void check(boolean value, String label) { assertions++; if (!value) throw new AssertionError(label); }
    private static void denies(Runnable action) {
        try { action.run(); throw new AssertionError("mutation permitted"); }
        catch (UnsupportedOperationException expected) { assertions++; }
    }
    @SuppressWarnings("unchecked") private static void immutable(Object value) {
        if (value instanceof Map<?, ?>) {
            Map<String, Object> map = (Map<String, Object>)value;
            denies(() -> map.put("probe", 1L));
            denies(() -> map.remove("probe"));
            denies(map::clear);
            denies(() -> map.putAll(Map.of("probe", 1L)));
            denies(() -> map.replaceAll((k, v) -> 1L));
            denies(() -> map.compute("probe", (k, v) -> 1L));
            denies(() -> map.keySet().remove("probe"));
            denies(() -> map.values().clear());
            if (!map.isEmpty()) {
                Map.Entry<String, Object> entry = map.entrySet().iterator().next();
                denies(() -> entry.setValue(1L));
                java.util.Iterator<String> iterator = map.keySet().iterator(); iterator.next();
                denies(iterator::remove);
            }
            for (Object child : map.values()) immutable(child);
        } else if (value instanceof List<?>) {
            List<Object> list = (List<Object>)value;
            denies(() -> list.add(1L));
            denies(() -> list.remove(1L));
            denies(list::clear);
            denies(() -> list.addAll(List.of(1L)));
            denies(() -> list.replaceAll(v -> 1L));
            if (!list.isEmpty()) {
                denies(() -> list.set(0, 1L));
                java.util.Iterator<Object> iterator = list.iterator(); iterator.next(); denies(iterator::remove);
                denies(() -> list.subList(0, 1).clear());
            }
            for (Object child : list) immutable(child);
        }
    }
    private static void encode(Object value, StringBuilder out) {
        if (value instanceof String) {
            out.append('"');
            for (char c : ((String)value).toCharArray()) { if (c == '"' || c == '\\') out.append('\\'); out.append(c); }
            out.append('"');
        } else if (value instanceof Long) out.append(value);
        else if (value instanceof Map<?, ?>) {
            out.append('{'); boolean first = true;
            Map<String, Object> ordered = new TreeMap<>();
            for (Map.Entry<?, ?> e : ((Map<?, ?>)value).entrySet()) ordered.put((String)e.getKey(), e.getValue());
            for (Map.Entry<String, Object> e : ordered.entrySet()) { if (!first) out.append(','); first = false; encode(e.getKey(), out); out.append(':'); encode(e.getValue(), out); }
            out.append('}');
        } else if (value instanceof List<?>) {
            out.append('['); boolean first = true;
            for (Object child : (List<?>)value) { if (!first) out.append(','); first = false; encode(child, out); }
            out.append(']');
        } else throw new AssertionError("unexpected retained type");
    }
    private static byte[] retained(AppearanceDescriptorV1 value) {
        Map<String, Object> root = new LinkedHashMap<>();
        root.put("format", "mixer.native-appearance.1"); root.put("id", value.id); root.put("resources", value.resources);
        if (value.platformSpecificReason == null) { root.put("mode", "shared"); root.put("theme", value.iOS); check(value.iOS == value.android, "shared alias"); }
        else { root.put("mode", "platformSpecific"); root.put("iOS", value.iOS); root.put("android", value.android); root.put("reason", value.platformSpecificReason); }
        StringBuilder out = new StringBuilder(); encode(root, out); out.append('\n'); return out.toString().getBytes(StandardCharsets.US_ASCII);
    }
    public static void main(String[] args) throws Exception {
        int accepted = 0, rejected = 0;
        for (String line : Files.readAllLines(Path.of(args[0]), StandardCharsets.US_ASCII)) {
            String[] fields = line.split("\t", -1); byte[] data = Base64.getDecoder().decode(fields[2]);
            AppearanceDescriptorV1 result = null;
            try { result = AppearanceDescriptorV1.decode(data); } catch (IllegalArgumentException expected) { /* rejected */ }
            check((result != null) == fields[1].equals("1"), fields[0]);
            if (result == null) { rejected++; continue; }
            accepted++; check(Arrays.equals(data, retained(result)), fields[0] + " retained values");
            immutable(result.iOS); immutable(result.android); immutable(result.resources);
            byte[] before = retained(result); Arrays.fill(data, (byte)'X');
            check(Arrays.equals(before, retained(result)), fields[0] + " defensive source ownership");
        }
        try { AppearanceDescriptorV1.decode(null); throw new AssertionError("null accepted"); } catch (IllegalArgumentException expected) { assertions++; }
        for (String[] sample : new String[][] {
            {"[".repeat(17) + "0" + "]".repeat(17) + "\n", "JSON construction bounds"},
            {"[" + "0,".repeat(64) + "0]\n", "array bound"},
            {"\"" + "A".repeat(513) + "\"\n", "string bounds"}
        }) {
            try { AppearanceDescriptorV1.decode(sample[0].getBytes(StandardCharsets.US_ASCII)); throw new AssertionError("guard bypass"); }
            catch (IllegalArgumentException expected) { check(expected.getMessage().equals(sample[1]), "construction guard"); }
        }
        check(!java.lang.reflect.Modifier.isPublic(AppearanceDescriptorV1.class.getModifiers()), "private class");
        for (java.lang.reflect.Field field : AppearanceDescriptorV1.class.getDeclaredFields()) check(java.lang.reflect.Modifier.isFinal(field.getModifiers()), "final retained field");
        System.out.println("PASS independent descriptor cases=" + (accepted + rejected) + " accepted=" + accepted + " rejected=" + rejected + " assertions=" + assertions);
    }
}
