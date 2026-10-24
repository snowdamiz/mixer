package dev.mixer.android;

import java.lang.reflect.Modifier;
import java.lang.reflect.RecordComponent;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Host data tests. An encoder exists here solely to inspect every retained typed
 * value; product admission never delegates schema authority to reflection. */
public final class AppearanceDescriptorV2Tests {
    private static int checks;
    private static void require(boolean condition, String name) { checks++; if (!condition) throw new AssertionError(name); }
    private static void immutable(Object value) throws Exception {
        require(value != null, "null typed value");
        if (value instanceof List<?> list) {
            try { list.clear(); throw new AssertionError("mutable typed list"); } catch (UnsupportedOperationException expected) { checks++; }
            for (Object child : list) immutable(child);
        } else if (value.getClass().isRecord()) {
            require(Modifier.isFinal(value.getClass().getModifiers()), "nonfinal record");
            for (RecordComponent field : value.getClass().getRecordComponents()) immutable(field.getAccessor().invoke(value));
        } else require(value instanceof String || value instanceof Integer || value instanceof Enum<?>, "untyped retained object");
    }
    private static Object tree(Object value) throws Exception {
        if (value instanceof AppearanceDescriptorV2.Color color)
            return String.format(java.util.Locale.ROOT,"#%02X%02X%02X%02X",color.red(),color.green(),color.blue(),color.alpha());
        if (value instanceof AppearanceDescriptorV2.Weight weight) return weight.value;
        if (value instanceof AppearanceDescriptorV2.SystemSans) return Map.of("kind","systemSans");
        if (value instanceof AppearanceDescriptorV2.Bundled bundled) return Map.of("kind","bundled","faces",tree(bundled.faces()),"fallback",tree(bundled.fallback()));
        if (value instanceof Enum<?> e) return e.name();
        if (value instanceof List<?> list) { List<Object> result = new ArrayList<>(); for (Object child : list) result.add(tree(child)); return result; }
        if (value.getClass().isRecord()) {
            Map<String,Object> result = new TreeMap<>();
            for (RecordComponent field : value.getClass().getRecordComponents()) result.put(field.getName(),tree(field.getAccessor().invoke(value)));
            return result;
        }
        require(value instanceof String || value instanceof Integer, "unexpected leaf"); return value;
    }
    private static String json(Object value) {
        if (value instanceof String s) return "\"" + s.replace("\\","\\\\").replace("\"","\\\"") + "\"";
        if (value instanceof Integer) return value.toString();
        if (value instanceof List<?> list) { List<String> items = new ArrayList<>(); for (Object item : list) items.add(json(item)); return "[" + String.join(",",items) + "]"; }
        if (value instanceof Map<?,?> map) {
            Map<String,Object> sorted = new TreeMap<>(); for (var entry : map.entrySet()) sorted.put((String)entry.getKey(),entry.getValue());
            List<String> fields = new ArrayList<>(); for (var entry : sorted.entrySet()) fields.add(json(entry.getKey()) + ":" + json(entry.getValue()));
            return "{" + String.join(",",fields) + "}";
        }
        throw new AssertionError("not JSON");
    }
    private static byte[] encoded(AppearanceDescriptorV2 value) throws Exception {
        Map<String,Object> root = new TreeMap<>(); root.put("format",AppearanceDescriptorV2.FORMAT); root.put("id",value.id);
        root.put("mode",value.mode.name()); root.put("resources",tree(value.resources));
        if (value.mode == AppearanceDescriptorV2.Mode.shared) root.put("theme",tree(value.iOS));
        else { root.put("iOS",tree(value.iOS)); root.put("android",tree(value.android)); root.put("reason",value.platformSpecificReason); }
        return (json(root) + "\n").getBytes(StandardCharsets.US_ASCII);
    }
    public static void main(String[] args) throws Exception {
        int accepted = 0, rejected = 0;
        for (String line : Files.readAllLines(Path.of(args[0]),StandardCharsets.US_ASCII)) {
            String[] fields = line.split("\t",-1); byte[] bytes = Base64.getDecoder().decode(fields[2]);
            AppearanceDescriptorV2 descriptor = null;
            try { descriptor = AppearanceDescriptorV2.decode(bytes); } catch (AppearanceDescriptorV2.Failure expected) {
                AppearanceDescriptorV2.Error construction = switch (fields[0]) {
                    case "depth21" -> AppearanceDescriptorV2.Error.depthLimit;
                    case "array65", "icon-count-65" -> AppearanceDescriptorV2.Error.arrayLimit;
                    case "values-over" -> AppearanceDescriptorV2.Error.valueLimit;
                    case "oversize", "empty" -> AppearanceDescriptorV2.Error.byteLimit;
                    case "duplicate-key" -> AppearanceDescriptorV2.Error.duplicateKey;
                    case "nonascii", "bom" -> AppearanceDescriptorV2.Error.invalidEncoding;
                    default -> null;
                };
                require(construction == null || expected.code == construction,"construction error:" + fields[0]);
            }
            boolean success = descriptor != null;
            require(success == fields[1].equals("1"),fields[0]);
            String decoded = "-";
            if (success) {
                accepted++; immutable(descriptor.iOS); immutable(descriptor.android); immutable(descriptor.resources);
                require(descriptor.mode != AppearanceDescriptorV2.Mode.shared || descriptor.iOS == descriptor.android,"shared identity");
                byte[] fromTyped = encoded(descriptor); require(Arrays.equals(fromTyped,bytes),"typed field loss:" + fields[0]);
                decoded = Base64.getEncoder().encodeToString(fromTyped);
                String id = descriptor.id; Arrays.fill(bytes,(byte)'X'); require(descriptor.id.equals(id),"source array retained");
                try { AppearanceDescriptorV1.decode(fromTyped); throw new AssertionError("V1 accepts V2"); } catch (IllegalArgumentException expected) { checks++; }
            } else rejected++;
            System.out.println(fields[0] + "\t" + (success ? "1" : "0") + "\t" + decoded);
        }
        byte[] v1 = Files.readAllBytes(Path.of(args[1]));
        require(v1.length == 1906,"V1 golden byte count"); AppearanceDescriptorV1.decode(v1);
        try { AppearanceDescriptorV2.decode(v1); throw new AssertionError("V2 accepts V1"); } catch (AppearanceDescriptorV2.Failure expected) { checks++; }
        try { AppearanceDescriptorV2.decode(null); throw new AssertionError("null accepted"); } catch (AppearanceDescriptorV2.Failure expected) { require(expected.code == AppearanceDescriptorV2.Error.byteLimit,"null classification"); }
        System.err.println("PASS descriptor cases=" + (accepted + rejected) + " accepted=" + accepted + " rejected=" + rejected + " assertions=" + checks);
    }
}
