package dev.mixer.android;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;
import java.util.Map;

public final class CopiedPairProbe {
    private static int checks = 0;
    private static void check(boolean value, String name) {
        if (!value) throw new AssertionError(name);
        checks++; System.out.println("PASS " + name);
    }
    private static void rejects(Runnable operation, String name) {
        try { operation.run(); } catch (IllegalArgumentException expected) {
            checks++; System.out.println("REJECT " + name + " " + expected.getMessage()); return;
        }
        throw new AssertionError("accepted " + name);
    }
    private static byte[] change(byte[] bytes, String from, String to) {
        String value = new String(bytes, StandardCharsets.UTF_8);
        if (!value.contains(from)) throw new AssertionError("missing mutation target " + from);
        return value.replace(from, to).getBytes(StandardCharsets.UTF_8);
    }
    public static void main(String[] args) throws Exception {
        Path directory = Path.of(args[0]);
        byte[] descriptor = Files.readAllBytes(directory.resolve("swift-descriptor.json"));
        AppearanceDescriptorV2 appearance = AppearanceDescriptorV2.decode(descriptor);
        check(appearance.mode == AppearanceDescriptorV2.Mode.shared && appearance.resources.isEmpty(), "actual Swift shared default");
        check(appearance.android.typography().font() instanceof AppearanceDescriptorV2.SystemSans, "actual system sans");
        rejects(() -> AppearanceDescriptorV2.decode(change(descriptor, "mixer.native-appearance.2", "mixer.native-appearance.9")), "appearance unsupported format");
        rejects(() -> AppearanceDescriptorV2.decode(change(descriptor, "measuredShared2", "measuredShared9")), "appearance unsupported recipe");
        rejects(() -> AppearanceDescriptorV2.decode(("{\"aardvark\":0," + new String(descriptor, StandardCharsets.UTF_8).substring(1)).getBytes(StandardCharsets.UTF_8)), "appearance unknown fields");
        rejects(() -> AppearanceDescriptorV2.decode("{\"format\":1,\"format\":1}\n".getBytes(StandardCharsets.UTF_8)), "appearance duplicate fields");
        rejects(() -> AppearanceDescriptorV2.decode("{}".getBytes(StandardCharsets.UTF_8)), "appearance malformed shape");
        byte[] first = Files.readAllBytes(directory.resolve("swift-packet-1.json"));
        byte[] next = Files.readAllBytes(directory.resolve("swift-packet-2.json"));
        UiPacket one = UiPacket.decode(first), two = UiPacket.decode(next);
        two.requireSuccessor(one); check(two.revision.equals("2"), "actual Swift packet successor");
        UiPacket actualApp = UiPacket.decode(Files.readAllBytes(directory.resolve("swift-app-session-packet.json")));
        check(actualApp.nodes.containsKey("draft") && actualApp.nodes.containsKey("add"), "actual exported app session packet");
        rejects(() -> one.requireSuccessor(two), "stale revision");
        rejects(() -> UiPacket.decode(change(first, "\"schemaVersion\":1}", "\"schemaVersion\":9}")), "packet unsupported schema");
        rejects(() -> UiPacket.decode(change(first, "\"schemaVersion\":1},\"identities\"", "\"schemaVersion\":9},\"identities\"")), "document unsupported schema");
        rejects(() -> UiPacket.decode(change(first, "{\"document\":", "{\"unknown\":null,\"document\":")), "packet unknown fields");
        rejects(() -> UiPacket.decode(change(first, "\"generation\":1", "\"generation\":0")), "zero generation");
        rejects(() -> UiPacket.decode(change(first, "\"generation\":2", "\"generation\":1")), "duplicate generation");
        rejects(() -> UiPacket.decode(change(first, "\"id\":\"root\"}", "\"id\":\"missing\"}")), "identity coverage");
        rejects(() -> UiPacket.decode(change(next, "\"generation\":1", "\"generation\":99")).requireSuccessor(one), "surviving identity changed");
        rejects(() -> UiPacket.decode("{\"schemaVersion\":1,\"schemaVersion\":1}".getBytes(StandardCharsets.UTF_8)), "packet duplicate fields");
        rejects(() -> UiPacket.decode(new byte[] {(byte)0xff}), "packet invalid encoding");
        UiPacket full = UiPacket.decode(Files.readAllBytes(directory.resolve("swift-packet-uint64.json")));
        check(full.revision.equals("18446744073709551615"), "full UInt64 revision");
        check(full.nodes.values().stream().anyMatch(n -> n.generation.equals("18446744073709551615")), "full UInt64 generation");
        UiPacket.Node draft = full.nodes.get("draft");
        byte[] event = full.event("draft", draft.generation, "textChange", "Java café 東京");
        Files.write(directory.resolve("java-event-uint64.json"), event);
        Map<String,Object> value = Json.object(Json.parse(event));
        check(Json.uint(value.get("revision")).equals(full.revision), "Java event retains UInt64 revision");
        rejects(() -> full.event("draft", "0", "textChange", "x"), "event stale identity");
        rejects(() -> full.event("draft", draft.generation, "activate", null), "event unbound");
        rejects(() -> full.event("draft", draft.generation, "textChange", Boolean.TRUE), "event wrong value");
        System.out.println("PASS production copied Swift to Java checks=" + checks);
    }
}
