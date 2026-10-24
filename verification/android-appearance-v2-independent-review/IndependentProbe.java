package dev.mixer.android;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.lang.reflect.Modifier;
import java.lang.reflect.RecordComponent;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Independent review probe. No author-test helper or product encoder is used. */
public final class IndependentProbe {
    private IndependentProbe() {}

    public static void main(String[] args) throws Exception {
        BufferedReader input = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.US_ASCII));
        String line;
        while ((line = input.readLine()) != null) {
            if (args[0].equals("descriptor")) descriptor(line);
            else if (args[0].equals("parser-errors")) {
                try { AppearanceDescriptorV2.decode(Base64.getDecoder().decode(line)); System.out.println("accept"); }
                catch (AppearanceDescriptorV2.Failure error) { System.out.println(error.code.name()); }
            }
            else if (args[0].equals("ownership")) ownership(line);
            else geometry(line);
        }
    }

    private static void descriptor(String line) throws Exception {
        byte[] bytes = Base64.getDecoder().decode(line);
        try {
            AppearanceDescriptorV2 descriptor = AppearanceDescriptorV2.decode(bytes);
            String rebuilt = encode(root(descriptor)) + "\n";
            System.out.println(Arrays.equals(rebuilt.getBytes(StandardCharsets.US_ASCII), bytes) ? "accept" : "typedMismatch");
        } catch (AppearanceDescriptorV2.Failure error) { System.out.println("reject"); }
    }

    private static Map<String,Object> root(AppearanceDescriptorV2 d) throws Exception {
        Map<String,Object> root = new TreeMap<>();
        root.put("format", AppearanceDescriptorV2.FORMAT); root.put("id",d.id);
        root.put("mode",d.mode.name()); root.put("resources",tree(d.resources));
        if (d.mode == AppearanceDescriptorV2.Mode.shared) {
            if (d.iOS != d.android || d.platformSpecificReason != null) throw new AssertionError("shared ownership");
            root.put("theme",tree(d.iOS));
        } else {
            root.put("iOS",tree(d.iOS)); root.put("android",tree(d.android)); root.put("reason",d.platformSpecificReason);
        }
        return root;
    }

    private static Object tree(Object value) throws Exception {
        if (value instanceof AppearanceDescriptorV2.Color c)
            return String.format(java.util.Locale.ROOT,"#%02X%02X%02X%02X",c.red(),c.green(),c.blue(),c.alpha());
        if (value instanceof AppearanceDescriptorV2.Weight w) return w.value;
        if (value instanceof Enum<?> e) return e.name();
        if (value instanceof String || value instanceof Integer) return value;
        if (value instanceof List<?> values) {
            List<Object> result = new ArrayList<>(); for (Object child : values) result.add(tree(child)); return result;
        }
        if (!value.getClass().isRecord()) throw new AssertionError("untraversed type " + value.getClass());
        Map<String,Object> result = new TreeMap<>();
        for (RecordComponent component : value.getClass().getRecordComponents())
            result.put(component.getName(),tree(component.getAccessor().invoke(value)));
        if (value instanceof AppearanceDescriptorV2.SystemSans) result.put("kind","systemSans");
        if (value instanceof AppearanceDescriptorV2.Bundled) result.put("kind","bundled");
        return result;
    }

    private static String encode(Object value) {
        if (value instanceof String s) return "\"" + s.replace("\\","\\\\").replace("\"","\\\"") + "\"";
        if (value instanceof Integer) return value.toString();
        if (value instanceof List<?> list) return "[" + String.join(",",list.stream().map(IndependentProbe::encode).toList()) + "]";
        if (value instanceof Map<?,?> map) {
            List<String> pairs = new ArrayList<>();
            for (Map.Entry<?,?> e : map.entrySet()) pairs.add(encode(e.getKey()) + ":" + encode(e.getValue()));
            return "{" + String.join(",",pairs) + "}";
        }
        throw new AssertionError("unencoded " + value);
    }

    @SuppressWarnings({"rawtypes", "unchecked"})
    private static void immutable(Object value) throws Exception {
        if (value instanceof String || value instanceof Integer || value instanceof Enum<?>) return;
        if (value instanceof List<?> list) {
            for (Object child : list) immutable(child);
            try { ((List)list).add(null); throw new AssertionError("mutable list"); }
            catch (UnsupportedOperationException expected) { /* observed rejection */ }
            return;
        }
        for (var field : value.getClass().getDeclaredFields()) {
            if (Modifier.isStatic(field.getModifiers())) continue;
            if (!Modifier.isFinal(field.getModifiers())) throw new AssertionError("mutable field " + field);
        }
        if (value.getClass().isRecord())
            for (var c : value.getClass().getRecordComponents()) immutable(c.getAccessor().invoke(value));
    }

    private static void ownership(String line) throws Exception {
        byte[] bytes=Base64.getDecoder().decode(line);
        AppearanceDescriptorV2 d=AppearanceDescriptorV2.decode(bytes);
        String before=encode(root(d)); Arrays.fill(bytes,(byte)0);
        if (!before.equals(encode(root(d)))) throw new AssertionError("retained input");
        immutable(d.iOS); immutable(d.android); immutable(d.resources);
        for (var field : d.getClass().getDeclaredFields())
            if (!Modifier.isStatic(field.getModifiers()) && !Modifier.isFinal(field.getModifiers())) throw new AssertionError("mutable descriptor");
        var mutableFaces=new ArrayList<AppearanceDescriptorV2.FontFace>();
        var copiedFont=new AppearanceDescriptorV2.Bundled(mutableFaces,AppearanceDescriptorV2.FontFallback.none);
        mutableFaces.add(new AppearanceDescriptorV2.FontFace("font","PS",AppearanceDescriptorV2.Weight.w400,AppearanceDescriptorV2.FontStyle.normal));
        if (!copiedFont.faces().isEmpty()) throw new AssertionError("font list alias");
        immutable(copiedFont);
        for (var path : List.of(AppearanceGeometryV2.track(),AppearanceGeometryV2.thumb(),AppearanceGeometryV2.group(101,103,65536))) {
            immutable(path.commands);
            for (var field : path.getClass().getDeclaredFields())
                if (!Modifier.isStatic(field.getModifiers()) && !Modifier.isFinal(field.getModifiers())) throw new AssertionError("mutable path");
        }
        var points=new ArrayList<AppearanceGeometryV2.Point>(); points.add(new AppearanceGeometryV2.Point(1,2));
        var command=new AppearanceGeometryV2.Command(AppearanceGeometryV2.Op.move,points); points.clear();
        if (command.points().size()!=1) throw new AssertionError("point list alias");
        immutable(command);
        try { AppearanceDescriptorV2.decode(null); throw new AssertionError("null bytes accepted"); }
        catch (AppearanceDescriptorV2.Failure expected) {
            if (expected.code != AppearanceDescriptorV2.Error.byteLimit) throw new AssertionError("null error");
        }
        try { AppearanceGeometryV2.thumbOrigin(false,null); throw new AssertionError("null direction accepted"); }
        catch (AppearanceGeometryV2.Failure expected) {
            if (expected.code != AppearanceGeometryV2.Error.extent) throw new AssertionError("direction error");
        }
        System.out.println("immutable");
    }

    private static String path(AppearanceGeometryV2.Path path) {
        StringBuilder out = new StringBuilder(path.shape.name()).append(';').append(path.width64).append(';').append(path.height64);
        for (var command : path.commands) {
            out.append(';').append(command.op().name());
            for (var point : command.points()) out.append(':').append(point.x64()).append(',').append(point.y64());
        }
        return out.toString();
    }

    private static void geometry(String line) {
        String[] f=line.split("\t");
        try {
            String result=switch (f[0]) {
                case "group" -> path(AppearanceGeometryV2.group(Long.parseLong(f[1]),Long.parseLong(f[2]),Long.parseLong(f[3])));
                case "track" -> path(AppearanceGeometryV2.track());
                case "thumb" -> path(AppearanceGeometryV2.thumb());
                case "origin" -> {
                    var p=AppearanceGeometryV2.thumbOrigin(f[1].equals("1"),AppearanceGeometryV2.Direction.valueOf(f[2]));
                    yield p.x64()+","+p.y64();
                }
                case "extent" -> Integer.toString(AppearanceGeometryV2.measuredExtent64(Double.longBitsToDouble(Long.parseUnsignedLong(f[1],16))));
                case "spacing" -> Integer.toString(AppearanceGeometryV2.spacing64(Double.longBitsToDouble(Long.parseUnsignedLong(f[1],16))));
                case "density" -> Integer.toString(AppearanceGeometryV2.normalizeDensity(Double.longBitsToDouble(Long.parseUnsignedLong(f[1],16))));
                case "edge" -> Integer.toString(AppearanceGeometryV2.pixelEdge(Long.parseLong(f[1]),Integer.parseInt(f[2])));
                case "coordinate" -> Long.toHexString(Double.doubleToRawLongBits(AppearanceGeometryV2.pixelCoordinate(Long.parseLong(f[1]),Integer.parseInt(f[2]))));
                default -> throw new AssertionError("unknown probe");
            };
            System.out.println("ok\t"+result);
        } catch (AppearanceGeometryV2.Failure error) { System.out.println("reject\t"+error.code.name()); }
    }
}
