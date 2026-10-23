package dev.mixer.android;

import java.io.BufferedReader;
import java.lang.reflect.RecordComponent;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Base64;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Full retained-value comparison against a separately compiled public Swift API.
 * The oracle exports the exact reconciler packet; this test never assigns IDs. */
public final class AppearanceResolutionTests {
    private AppearanceResolutionTests() {}
    private static int cases, accepted, rejected, packetBoundary, nodes, styles, assertions;
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("oracle TSV path");
        try (BufferedReader reader = Files.newBufferedReader(Path.of(args[0]), StandardCharsets.UTF_8)) {
            String line;
            while ((line = reader.readLine()) != null) checkCase(line.split("\t", -1));
        }
        negativeInputs();
        System.out.println("appearance resolution cases=" + cases + " accepted=" + accepted + " rejected=" + rejected
            + " knownPacketBoundary=" + packetBoundary + " nodes=" + nodes + " styles=" + styles + " assertions=" + assertions);
    }
    private static void checkCase(String[] f) throws Exception {
        if (f.length != 8) throw new AssertionError("TSV shape");
        String name = f[0]; cases++;
        boolean oracleAccepted = f[1].equals("accepted"), boundary = f[7].equals("packet-baseline-rejected");
        AppearanceResolutionV1.Plan plan;
        UiPacket packet;
        try {
            AppearanceDescriptorV1 descriptor = AppearanceDescriptorV1.decode(decode(f[2]));
            Map<String,Object> env = Json.object(Json.parse(decode(f[3])));
            AppearanceResolutionV1.Environment environment = new AppearanceResolutionV1.Environment(
                AppearanceResolutionV1.Scheme.valueOf(Json.string(env.get("scheme"))),
                AppearanceResolutionV1.Direction.valueOf(Json.string(env.get("direction"))),
                Integer.parseInt(Json.uint(env.get("textScale1024"))), Integer.parseInt(Json.uint(env.get("density1024"))));
            packet = UiPacket.decode(decode(f[5]));
            plan = AppearanceResolutionV1.prepare(packet, descriptor, environment, AppearanceResolutionV1.Platform.valueOf(f[4]));
        } catch (IllegalArgumentException exception) {
            if (oracleAccepted && !boundary) throw new AssertionError(name + " unexpectedly rejected: " + exception, exception);
            if (boundary) packetBoundary++; else rejected++;
            assertions++; return;
        }
        if (!oracleAccepted || boundary) throw new AssertionError(name + " unexpectedly accepted");
        accepted++;
        Object output = planOutput(plan);
        String actual = sha(canonical(output).getBytes(StandardCharsets.UTF_8));
        if (!f[6].equals(actual)) {
            Path failure = Path.of("resolution-actual.json"); Files.writeString(failure, canonical(output));
            throw new AssertionError(name + " complete retained plan/style SHA256: expected=" + f[6] + " actual=" + actual + " values=" + failure.toAbsolutePath());
        }
        assertions++;
        equal(packet.revision, plan.revision, name + " exact UInt64 revision");
        equal(null, plan.node("missing-node"), name + " missing node");
        equal(null, plan.style("missing-node", true, true), name + " missing style");
        expectImmutable(() -> plan.nodes.clear());
        expectImmutable(() -> plan.resources.add("forbidden"));
        expectImmutable(() -> plan.font.put("forbidden", "forbidden"));
        for (AppearanceResolutionV1.Node node : plan.nodes) {
            UiPacket.Node source = packet.nodes.get(node.identity().id());
            equal(source.generation, node.identity().generation(), name + " generation");
            equal(source.kind, node.kind(), name + " kind");
            equal(source.disabled, node.disabled(), name + " inherited disabled");
            expectImmutable(() -> node.childIDs().add("forbidden"));
            if (!source.disabled && source.actions.containsKey("activate")) {
                byte[] before = packet.event(source.id, source.generation, "activate", null);
                plan.style(source.id, true, true);
                equal(new String(before, StandardCharsets.UTF_8), new String(packet.event(source.id, source.generation, "activate", null), StandardCharsets.UTF_8), name + " event untouched");
            }
        }
    }
    private static Object planOutput(AppearanceResolutionV1.Plan p) throws Exception {
        Map<String,Object> out = new LinkedHashMap<>();
        out.put("revision", p.revision); out.put("configurationID", p.configurationID); out.put("recipe", p.recipe);
        out.put("canvas", p.canvas); out.put("environment", p.environment); out.put("platform", p.platform);
        out.put("platformSpecificReason", p.platformSpecificReason); out.put("font", p.font); out.put("resources", p.resources);
        List<Object> values = new ArrayList<>();
        for (AppearanceResolutionV1.Node n : p.nodes) {
            Map<String,Object> value = record(n); value.put("recipe", recipe(n.recipe()));
            List<Object> states = new ArrayList<>();
            for (int state = 0; state < 4; state++) states.add(p.style(n.identity().id(), (state & 1) != 0, (state & 2) != 0));
            value.put("styles", states); values.add(value); nodes++; styles += 4;
        }
        out.put("nodes", values); return out;
    }
    private static Object recipe(AppearanceResolutionV1.Recipe r) throws Exception {
        Map<String,Object> value = record(r);
        value.put("case", r.getClass().getSimpleName()); return value;
    }
    private static Map<String,Object> record(Object value) throws Exception {
        Map<String,Object> result = new LinkedHashMap<>();
        for (RecordComponent field : value.getClass().getRecordComponents()) result.put(field.getName(), field.getAccessor().invoke(value));
        return result;
    }
    // Numbers are deliberately decimal strings on both sides, avoiding host JSON
    // numeric representation differences and preserving every UInt64 bit.
    private static String canonical(Object value) throws Exception {
        if (value != null && value.getClass().isRecord()) return canonical(record(value));
        if (value instanceof Enum<?>) return canonical(((Enum<?>)value).name());
        if (value instanceof Number) return canonical(value.toString());
        if (value instanceof Map<?,?>) {
            Map<String,Object> sorted = new TreeMap<>();
            for (Map.Entry<?,?> e : ((Map<?,?>)value).entrySet()) sorted.put((String)e.getKey(), e.getValue());
            StringBuilder text = new StringBuilder("{"); boolean comma = false;
            for (Map.Entry<String,Object> e : sorted.entrySet()) {
                if (comma) text.append(','); comma = true;
                text.append(canonical(e.getKey())).append(':').append(canonical(e.getValue()));
            }
            return text.append('}').toString();
        }
        if (value instanceof List<?>) {
            StringBuilder text = new StringBuilder("["); boolean comma = false;
            for (Object v : (List<?>)value) { if (comma) text.append(','); comma = true; text.append(canonical(v)); }
            return text.append(']').toString();
        }
        StringBuilder text = new StringBuilder(); Json.write(text, value); return text.toString();
    }
    private static void negativeInputs() {
        for (int value : new int[] {Integer.MIN_VALUE, -1, 0, 511, 4097, 65535, Integer.MAX_VALUE}) {
            expectRejected(() -> new AppearanceResolutionV1.Environment(AppearanceResolutionV1.Scheme.light, AppearanceResolutionV1.Direction.leftToRight, value, 1024));
        }
        for (int value : new int[] {Integer.MIN_VALUE, -1, 0, 127, 16385, 65535, Integer.MAX_VALUE}) {
            expectRejected(() -> new AppearanceResolutionV1.Environment(AppearanceResolutionV1.Scheme.light, AppearanceResolutionV1.Direction.leftToRight, 1024, value));
        }
        expectRejected(() -> new AppearanceResolutionV1.Environment(null, AppearanceResolutionV1.Direction.leftToRight, 1024, 1024));
        expectRejected(() -> new AppearanceResolutionV1.Environment(AppearanceResolutionV1.Scheme.light, null, 1024, 1024));
        expectRejected(() -> AppearanceResolutionV1.prepare(null, null, null, null));
    }
    private static byte[] decode(String s) { return Base64.getDecoder().decode(s); }
    private static String sha(byte[] bytes) throws Exception { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
    private static void equal(Object expected, Object actual, String name) {
        assertions++; if (!java.util.Objects.equals(expected, actual)) throw new AssertionError(name + ": expected=" + expected + " actual=" + actual);
    }
    private static void expectImmutable(Runnable run) {
        assertions++; try { run.run(); } catch (UnsupportedOperationException expected) { return; } throw new AssertionError("mutable output");
    }
    private static void expectRejected(Runnable run) {
        assertions++; try { run.run(); } catch (IllegalArgumentException expected) { return; } throw new AssertionError("invalid input accepted");
    }
}
