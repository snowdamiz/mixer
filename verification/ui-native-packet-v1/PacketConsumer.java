package dev.mixer.android;

import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** Executes the existing production Java decoder; no Android widget/JNI authority. */
final class PacketConsumer {
    static int checks;
    static void require(boolean condition, String label) {
        if (!condition) throw new AssertionError(label);
        checks++;
    }
    static UiPacket read(Path folder, String name) throws Exception {
        return UiPacket.decode(Files.readAllBytes(folder.resolve(name + ".json")));
    }
    static void reject(Runnable body, String label) {
        try { body.run(); } catch (IllegalArgumentException expected) { checks++; return; }
        throw new AssertionError(label);
    }
    public static void main(String[] args) throws Exception {
        Path folder = Path.of(args[0]);
        UiPacket all = read(folder, "all-kinds");
        require(all.revision.equals("18446744073709551615"), "full unsigned revision");
        require(all.nodes.size() == 10, "all ten nodes");
        Set<String> kinds = new HashSet<>();
        for (UiPacket.Node node : all.nodes.values()) kinds.add(node.kind);
        require(kinds.equals(UiPacket.set("navigation", "list", "section", "vStack", "hStack", "text", "button", "zStack", "textField", "toggle")), "all ten kinds");
        require(all.nodes.get("vertical").number("spacing", -1) == 12.75, "fractional numeric property");
        require(all.nodes.get("text").flag("selectable", false), "boolean property");
        require(all.nodes.get("text").text("text", "").equals("Café 🏗️"), "Unicode text");
        UiPacket unicode = read(folder, "unicode");
        require(Arrays.equals(unicode.root.id.getBytes(StandardCharsets.UTF_8), new byte[]{101, (byte)204, (byte)129}), "decomposed identity bytes preserved");
        StringBuilder controls = new StringBuilder();
        for (int i = 0; i < 32; i++) controls.append((char)i);
        String expected = controls + "\\\"/é e\u0301 漢字 🏗️ \u2028\u2029";
        require(unicode.root.text("text", "").equals(expected), "all controls and Unicode survive");
        UiPacket first = read(folder, "first"), second = read(folder, "second");
        second.requireSuccessor(first);
        require(second.root.children.get(0).id.equals("b"), "reorder preserved");
        require(second.nodes.get("a").generation.equals(first.nodes.get("a").generation), "surviving generation preserved");
        UiPacket removed = read(folder, "removed"), reinserted = read(folder, "reinserted");
        removed.requireSuccessor(second);
        reinserted.requireSuccessor(removed);
        require(!reinserted.nodes.get("a").generation.equals(first.nodes.get("a").generation), "reinsert generation changes");
        reject(() -> reinserted.event("a", first.nodes.get("a").generation, "activate", null), "stale generation rejected");
        require(read(folder, "depth64").nodes.size() == 64, "maximum Swift tree depth parses");
        byte[] limit = Files.readAllBytes(folder.resolve("exact-limit.json"));
        require(limit.length == 1_048_576 && UiPacket.decode(limit).nodes.size() == 15, "exact byte limit parses");
        reject(() -> UiPacket.decode(Arrays.copyOf(limit, limit.length + 1)), "byte limit rejects");
        byte[] baseline = Files.readAllBytes(folder.resolve("baseline-unsupported.json"));
        reject(() -> UiPacket.decode(baseline), "existing unsupported Android baseline fails closed");
        Files.write(folder.resolve("activate.json"), all.event("button", all.nodes.get("button").generation, "activate", null));
        Files.write(folder.resolve("textChange.json"), all.event("input", all.nodes.get("input").generation, "textChange", "é\0漢字🏗️"));
        Files.write(folder.resolve("valueChange.json"), all.event("toggle", all.nodes.get("toggle").generation, "valueChange", true));
        System.out.println("PASS: " + checks + " Java packet checks and three return events");
    }
}
